"""Personal Assistant — 规则引擎"""
from __future__ import annotations
import re, json, sqlite3, threading
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from .schemas import BehaviorRule, TriggerDef, TriggerMatch, Priority

DB_LOCK = threading.Lock()


class RuleEngine:
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
                CREATE TABLE IF NOT EXISTS assistant_rules (
                    rule_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT,
                    rule_json TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    priority TEXT DEFAULT 'P5',
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_user ON assistant_rules(user_id)")
            conn.commit()

    def add(self, user_id: str, rule: BehaviorRule) -> str:
        if not rule.rule_id:
            import uuid
            rule.rule_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        import dataclasses
        rule_dict = dataclasses.asdict(rule)
        with DB_LOCK, self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO assistant_rules (rule_id, user_id, name, rule_json, enabled, priority, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM assistant_rules WHERE rule_id=?), ?), ?)",
                (rule.rule_id, user_id, rule.name, json.dumps(rule_dict, ensure_ascii=False), 1 if rule.enabled else 0, rule.priority.value if hasattr(rule.priority, 'value') else rule.priority, rule.rule_id, now, now),
            )
            conn.commit()
        return rule.rule_id

    def delete(self, rule_id: str) -> bool:
        with DB_LOCK, self._conn() as conn:
            conn.execute("DELETE FROM assistant_rules WHERE rule_id = ?", (rule_id,))
            conn.commit()
        return True

    def get_for_user(self, user_id: str) -> list[BehaviorRule]:
        from .schemas import _fromdict
        with DB_LOCK, self._conn() as conn:
            cur = conn.execute("SELECT rule_json FROM assistant_rules WHERE user_id = ? AND enabled = 1 ORDER BY priority", (user_id,))
            return [_fromdict(BehaviorRule, json.loads(r[0])) for r in cur.fetchall()]

    def match(self, query: str, rules: list[BehaviorRule]) -> list[BehaviorRule]:
        matched = []
        for rule in rules:
            if not rule.enabled:
                continue
            for t in rule.triggers:
                if self._match_one(query, t):
                    matched.append(rule)
                    break
        matched.sort(key=lambda r: r.priority.value)
        return matched

    def _match_one(self, query: str, t) -> bool:
        if isinstance(t, dict):
            t = TriggerDef(**t)
        q = query if t.case_sensitive else query.lower()
        p = t.pattern if t.case_sensitive else t.pattern.lower()
        if t.match_type == TriggerMatch.EXACT:
            return q == p
        elif t.match_type == TriggerMatch.PREFIX:
            return q.startswith(p)
        elif t.match_type == TriggerMatch.SUFFIX:
            return q.endswith(p)
        elif t.match_type == TriggerMatch.CONTAINS:
            return p in q
        elif t.match_type == TriggerMatch.REGEX:
            try:
                return bool(re.search(p, q))
            except re.error:
                return False
        return False
