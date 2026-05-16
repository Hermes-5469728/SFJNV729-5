"""CaseCenter · 案例中心 — 真值同步/失败捕获/语义检索"""

import json
import time
import uuid as _uuid
from dataclasses import dataclass, field, asdict
from typing import Any
from pathlib import Path

from ac.memory_manager import MemoryManager, Experience, MemoryRetrieval

HERE = Path(__file__).resolve().parent


@dataclass
class CaptureResult:
    success: bool
    case_id: str
    message: str


class CaseCenter:
    def __init__(self, db_path: str | Path = "./ac_memory"):
        self.mem = MemoryManager(db_path=str(db_path))

    # ── 同步 ac_truth → ChromaDB ─────────────────────

    def sync_truths(self) -> int:
        import sqlite3
        from datetime import datetime, timezone

        db = HERE.parent / "ac_platform.db"
        if not db.exists():
            return 0
        conn = sqlite3.connect(str(db))
        rows = conn.execute(
            "SELECT title, category, content, tags, created_at FROM ac_truth WHERE verified=1"
        ).fetchall()
        conn.close()

        count = 0
        for title, category, content, tags, created_at in rows:
            eid = f"truth_{_uuid.uuid4().hex[:12]}"
            exp = Experience(
                experience_id=eid,
                task_type=category,
                goal=title,
                summary=content[:500],
                success=True,
                duration=0,
                timestamp=datetime.fromisoformat(created_at).timestamp() if created_at else time.time(),
                solution=content,
                failure_reason=None,
                metrics={"source": "ac_truth", "tags": tags or ""},
            )
            import asyncio
            ok = asyncio.run(self.mem.store_experience(exp))
            if ok:
                count += 1
        return count

    # ── 失败捕获 ──────────────────────────────────────

    def capture_failure(
        self,
        query: str,
        command: str,
        error: str,
        result: dict | None = None,
        session_id: str = "",
    ) -> CaptureResult:
        cid = f"case_{_uuid.uuid4().hex[:12]}"
        exp = Experience(
            experience_id=cid,
            task_type=command,
            goal=query[:200],
            summary=f"{command} failed: {error[:300]}",
            success=False,
            duration=0,
            timestamp=time.time(),
            solution=None,
            failure_reason=error[:500],
            metrics={
                "session_id": session_id,
                "result": json.dumps(result, ensure_ascii=False, default=str) if result else "",
            },
        )
        import asyncio
        ok = asyncio.run(self.mem.store_experience(exp))
        return CaptureResult(success=ok, case_id=cid, message=error[:200])

    # ── 检索 ──────────────────────────────────────────

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        import asyncio
        results = asyncio.run(self.mem.retrieve_similar(query, top_k))
        return [
            {
                "case_id": r.experience.experience_id,
                "task_type": r.experience.task_type,
                "goal": r.experience.goal,
                "summary": r.experience.summary[:200],
                "success": r.experience.success,
                "similarity": round(r.similarity, 3),
                "solution": r.experience.solution[:500] if r.experience.solution else None,
                "failure_reason": r.experience.failure_reason[:200] if r.experience.failure_reason else None,
            }
            for r in results
        ]

    # ── 统计 ──────────────────────────────────────────

    def stats(self) -> dict:
        return self.mem.get_stats()


_center: CaseCenter | None = None


def get_center() -> CaseCenter:
    global _center
    if _center is None:
        _center = CaseCenter()
    return _center
