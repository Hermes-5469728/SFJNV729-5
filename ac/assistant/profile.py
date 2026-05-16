"""Personal Assistant — 用户画像管理"""
from __future__ import annotations
import json, sqlite3, threading
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from .schemas import AssistantProfile, Identity, Preferences, Tone


DB_LOCK = threading.Lock()


class ProfileStore:
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
                CREATE TABLE IF NOT EXISTS assistant_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_json TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.commit()

    def get(self, user_id: str) -> Optional[AssistantProfile]:
        with DB_LOCK, self._conn() as conn:
            cur = conn.execute(
                "SELECT profile_json FROM assistant_profiles WHERE user_id = ?",
                (user_id,),
            )
            row = cur.fetchone()
        if row:
            return AssistantProfile.from_dict(json.loads(row[0]))
        return None

    def save(self, user_id: str, profile: AssistantProfile) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with DB_LOCK, self._conn() as conn:
            existing = conn.execute(
                "SELECT version FROM assistant_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            ver = (existing[0] + 1) if existing else 1
            conn.execute(
                "INSERT OR REPLACE INTO assistant_profiles (user_id, profile_json, version, created_at, updated_at) VALUES (?, ?, ?, COALESCE((SELECT created_at FROM assistant_profiles WHERE user_id=?), ?), ?)",
                (user_id, json.dumps(profile.to_dict(), ensure_ascii=False), ver, user_id, now, now),
            )
            conn.commit()
        return True

    def delete(self, user_id: str) -> bool:
        with DB_LOCK, self._conn() as conn:
            conn.execute("DELETE FROM assistant_profiles WHERE user_id = ?", (user_id,))
            conn.commit()
        return True

    def list_all(self) -> list[dict]:
        with DB_LOCK, self._conn() as conn:
            cur = conn.execute(
                "SELECT user_id, version, updated_at FROM assistant_profiles ORDER BY updated_at DESC",
            )
            return [dict(r) for r in cur.fetchall()]


_default_profile = AssistantProfile()

def get_default_profile() -> AssistantProfile:
    return _default_profile

def make_profile(
    user_id: str = "",
    name: str = "",
    tone: Tone = Tone.CASUAL,
    expert_domains: list[str] | None = None,
) -> AssistantProfile:
    p = AssistantProfile()
    p.identity = Identity(user_id=user_id, name=name)
    p.preferences.tone = tone
    if expert_domains:
        from .schemas import DomainConfig, ExpertiseLevel
        for d in expert_domains:
            p.knowledge.domains.append(DomainConfig(domain=d, expertise=ExpertiseLevel.ADVANCED))
    return p
