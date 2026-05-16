"""
统一知识检索服务 · KnowledgeService
数据源: ac_truth (SQLite) + ChromaDB (向量) + Metaso (外部搜索)
原则: 内部真值优先, 外部结果需验证标记
防护: SQL 语义守卫 — 检测云端隐式查询改写 (PRAGMA query_only + EXPLAIN QUERY PLAN)
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_log = logging.getLogger("ac.knowledge")

AC_DIR = Path(__file__).resolve().parent
DB_PATH = AC_DIR / "ac_platform.db"
CHROMA_DIR = AC_DIR / "chroma_store"

HIJACK_KEYWORDS = ["vector", "embed", "embedding", "ann", "approx", "hnsw", "ivf"]

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    import requests as _requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class KnowledgeService:
    def __init__(self, db_path: str = "", chroma_dir: str = ""):
        self._db = db_path or str(DB_PATH)
        self._chroma_dir = chroma_dir or str(CHROMA_DIR)
        self._chroma: Optional["chromadb.Collection"] = None
        self._chroma_client = None
        if CHROMA_AVAILABLE:
            self._init_chroma()

    def _conn(self, read_only: bool = False):
        conn = sqlite3.connect(self._db, timeout=10)
        conn.row_factory = sqlite3.Row
        if read_only:
            conn.execute("PRAGMA query_only = ON")
        return conn

    def _verify_sql_plan(self, query: str, sql: str) -> dict:
        """SQL 语义守卫: 执行 EXPLAIN QUERY PLAN 检测云端隐式改写"""
        with self._conn(read_only=True) as conn:
            plan_rows = conn.execute(f"EXPLAIN QUERY PLAN {sql}").fetchall()
        plan_str = " ".join(str(r) for r in plan_rows).lower()
        hijacked = [kw for kw in HIJACK_KEYWORDS if kw in plan_str]
        return {
            "clean": len(hijacked) == 0,
            "plan": plan_str[:500],
            "hijacked_keywords": hijacked,
        }

    def _log_hijack_attempt(self, query: str, plan: str, keywords: list[str]):
        _log.error("SQL_HIJACK_DETECTED query=%r keywords=%s plan=%s", query[:80], keywords, plan[:200])
        try:
            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO ac_guard_log (guard, action, detail, created_at) VALUES (?,?,?,?)",
                    (
                        "sql_plan_guard",
                        "hijack_detected",
                        json.dumps({"query": query[:80], "keywords": keywords, "plan": plan[:300]}, ensure_ascii=False),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
        except Exception:
            pass

    def _fallback_scan(self, query: str, top_k: int) -> list[dict]:
        """纯本地降级扫描: 绕过一切可能被改写的路径"""
        with self._conn(read_only=True) as conn:
            cur = conn.execute(
                "SELECT truth_id, title, category, source, content, verified, tags, created_at "
                "FROM ac_truth WHERE title LIKE ? OR content LIKE ? ORDER BY verified DESC LIMIT ?",
                (f"%{query}%", f"%{query}%", top_k),
            )
            return [dict(r) for r in cur.fetchall()]

    def _init_chroma(self):
        try:
            Path(self._chroma_dir).mkdir(parents=True, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(
                path=self._chroma_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._chroma = self._chroma_client.get_or_create_collection("ac_knowledge")
        except Exception:
            self._chroma = None

    def search(self, query: str, sources: Optional[list[str]] = None, top_k: int = 10) -> dict:
        sources = sources or ["truth", "chroma"]
        results = {
            "query": query,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": {},
        }

        if "truth" in sources:
            results["sources"]["truth"] = self._search_truth(query, top_k)
        if "chroma" in sources and self._chroma:
            results["sources"]["chroma"] = self._search_chroma(query, top_k)
        if "metaso" in sources:
            results["sources"]["metaso"] = self._search_metaso(query)

        results["total_hits"] = sum(
            len(v) for v in results["sources"].values() if isinstance(v, list)
        )
        return results

    def _search_truth(self, query: str, top_k: int = 10) -> list[dict]:
        search_sql = (
            "SELECT truth_id, title, category, source, content, verified, tags, created_at "
            "FROM ac_truth WHERE title LIKE '%{q}%' OR content LIKE '%{q}%' OR tags LIKE '%{q}%' "
            "ORDER BY verified DESC, created_at DESC LIMIT {k}"
        ).format(q=query.replace("'", "''"), k=int(top_k))

        plan = self._verify_sql_plan(query, search_sql)
        if not plan["clean"]:
            self._log_hijack_attempt(query, plan["plan"], plan["hijacked_keywords"])
            return self._fallback_scan(query, top_k)

        with self._conn(read_only=True) as conn:
            cur = conn.execute(
                "SELECT truth_id, title, category, source, content, verified, tags, created_at "
                "FROM ac_truth WHERE title LIKE ? OR content LIKE ? OR tags LIKE ? "
                "ORDER BY verified DESC, created_at DESC LIMIT ?",
                (f"%{query}%", f"%{query}%", f"%{query}%", top_k),
            )
            return [dict(r) for r in cur.fetchall()]

    def _search_chroma(self, query: str, top_k: int = 10) -> list[dict]:
        if not self._chroma:
            return []
        try:
            results = self._chroma.query(query_texts=[query], n_results=top_k)
            items = []
            ids = results.get("ids", [[]])[0]
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            for i in range(len(ids)):
                meta = (metas[i] or {}) if i < len(metas) else {}
                items.append({
                    "id": ids[i] if i < len(ids) else "",
                    "content": docs[i] if i < len(docs) else "",
                    "distance": distances[i] if i < len(distances) else None,
                    "source": meta.get("source", "chroma"),
                    "title": meta.get("title", ""),
                })
            return items
        except Exception:
            return []

    def _search_metaso(self, query: str) -> list[dict]:
        if not REQUESTS_AVAILABLE:
            return []
        api_key = os.environ.get("METASO_API_KEY", "")
        if not api_key:
            return []
        try:
            resp = _requests.post(
                "https://api.metaso.cn/v1/search",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"query": query, "top_k": 5},
                timeout=30,
            )
            data = resp.json()
            return [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("snippet", ""),
                    "url": r.get("url", ""),
                    "date": r.get("date", ""),
                }
                for r in data.get("results", [])
            ]
        except Exception:
            return []

    def index_truth(self, truth_id: str, title: str, content: str, category: str = "", source: str = ""):
        if not self._chroma:
            return False
        try:
            self._chroma.add(
                ids=[truth_id],
                documents=[f"{title}\n{content}"],
                metadatas=[{"title": title, "category": category, "source": source}],
            )
            return True
        except Exception:
            return False

    def index_batch(self, items: list[dict]) -> int:
        if not self._chroma or not items:
            return 0
        ids = [i.get("id", "") for i in items]
        docs = [f"{i.get('title','')}\n{i.get('content','')}" for i in items]
        metas = [{k: v for k, v in i.items() if k not in ("id", "content")} for i in items]
        try:
            self._chroma.add(ids=ids, documents=docs, metadatas=metas)
            return len(ids)
        except Exception:
            return 0

    def sync_from_truth(self, limit: int = 500) -> int:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT truth_id, title, category, source, content FROM ac_truth ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        if not rows:
            return 0
        items = [
            {"id": r["truth_id"], "title": r["title"], "content": r["content"],
             "category": r["category"], "source": r["source"]}
            for r in rows
        ]
        return self.index_batch(items)

    def clear_chroma(self):
        if not self._chroma_client:
            return
        try:
            self._chroma_client.delete_collection("ac_knowledge")
            self._chroma = self._chroma_client.get_or_create_collection("ac_knowledge")
        except Exception:
            pass


_knowledge: Optional[KnowledgeService] = None


def get_knowledge() -> KnowledgeService:
    global _knowledge
    if _knowledge is None:
        _knowledge = KnowledgeService()
    return _knowledge
