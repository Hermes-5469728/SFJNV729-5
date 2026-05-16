"""Personal Assistant — 个人记忆"""
from __future__ import annotations
import json, sqlite3, threading
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone, timedelta

DB_LOCK = threading.Lock()


class PersonalMemory:
    def __init__(self, db_path: str | Path = ""):
        if not db_path:
            db_path = Path(__file__).resolve().parent.parent / "ac_platform.db"
        self._db = str(db_path)
        self._init_table()

    def _conn(self):
        return sqlite3.connect(self._db, timeout=10)

    def _init_table(self):
        with DB_LOCK, self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS assistant_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_id TEXT,
                    topic TEXT,
                    content TEXT,
                    memory_type TEXT DEFAULT 'session',
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_user ON assistant_memory(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_topic ON assistant_memory(topic)")
            conn.commit()

    def remember(self, user_id: str, topic: str, content: str, memory_type: str = "long_term", confidence: float = 1.0):
        now = datetime.now(timezone.utc).isoformat()
        with DB_LOCK, self._conn() as conn:
            conn.execute(
                "INSERT INTO assistant_memory (user_id, topic, content, memory_type, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, topic, content, memory_type, confidence, now),
            )
            conn.commit()

    def recall(self, user_id: str, topic: str, limit: int = 5) -> list[dict]:
        with DB_LOCK, self._conn() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT content, confidence, created_at FROM assistant_memory WHERE user_id = ? AND topic LIKE ? ORDER BY confidence DESC, created_at DESC LIMIT ?",
                (user_id, f"%{topic}%", limit),
            )
            return [{"content": r["content"], "confidence": r["confidence"], "created_at": r["created_at"]} for r in cur.fetchall()]

    def get_recent(self, user_id: str, limit: int = 20) -> list[dict]:
        with DB_LOCK, self._conn() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT topic, content, memory_type, created_at FROM assistant_memory WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            )
            return [{"topic": r["topic"], "content": r["content"], "memory_type": r["memory_type"], "created_at": r["created_at"]} for r in cur.fetchall()]

    def forget(self, user_id: str, topic: str = "", before_days: int = 0):
        with DB_LOCK, self._conn() as conn:
            if topic:
                conn.execute("DELETE FROM assistant_memory WHERE user_id = ? AND topic = ?", (user_id, topic))
            elif before_days > 0:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=before_days)).isoformat()
                conn.execute("DELETE FROM assistant_memory WHERE user_id = ? AND created_at < ?", (user_id, cutoff))
            conn.commit()
