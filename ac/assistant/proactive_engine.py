"""ProactiveEngine — 事件驱动扫描引擎

Core协议：无事不扰，有危必应。
不刷存在感，只在检测到异常时主动推送。
"""
from __future__ import annotations
import subprocess
import sys
import json
import logging
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

_log = logging.getLogger("ac.proactive")

AC_DIR = Path(__file__).resolve().parent.parent
DB_PATH = AC_DIR / "ac_platform.db"
DB_LOCK = threading.Lock()

SCAN_INTERVAL_SECONDS = 300


class ScanResult:
    __slots__ = ("event", "level", "message", "detail", "timestamp")

    def __init__(self, event: str, level: str, message: str, detail: str = ""):
        self.event = event
        self.level = level
        self.message = message
        self.detail = detail
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "event": self.event,
            "level": self.level,
            "message": self.message,
            "detail": self.detail,
            "timestamp": self.timestamp,
        }


EVENT_WEIGHTS = {
    "test_failure": 3,
    "archguard_scan_fail": 4,
    "deadline_overdue": 2,
    "inactivity_3days": 1,
    "emotional_crisis_keyword": 3,
    "late_night_active": 1,
    "silence_after_emotional_crisis": 2,
}


class ProactiveEngine:
    def __init__(self, db_path: str = ""):
        self._db = db_path or str(DB_PATH)
        self._last_events: dict[str, ScanResult] = {}
        self._init_table()

    def _init_table(self):
        with DB_LOCK, sqlite3.connect(self._db, timeout=10) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS assistant_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    level TEXT NOT NULL DEFAULT 'info',
                    message TEXT,
                    detail TEXT,
                    acknowledged INTEGER DEFAULT 0,
                    created_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_event ON assistant_events(event)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ack ON assistant_events(acknowledged)")
            conn.commit()

    def _save_event(self, result: ScanResult):
        with DB_LOCK, sqlite3.connect(self._db, timeout=10) as conn:
            conn.execute(
                "INSERT INTO assistant_events (event, level, message, detail, created_at) VALUES (?, ?, ?, ?, ?)",
                (result.event, result.level, result.message, result.detail, result.timestamp),
            )
            conn.commit()

    def _find_unacknowledged(self, event: str) -> list[dict]:
        with DB_LOCK, sqlite3.connect(self._db, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT event, level, message, created_at FROM assistant_events WHERE event = ? AND acknowledged = 0 ORDER BY created_at DESC LIMIT 5",
                (event,),
            )
            return [dict(r) for r in cur.fetchall()]

    def acknowledge_event(self, event: str):
        with DB_LOCK, sqlite3.connect(self._db, timeout=10) as conn:
            conn.execute("UPDATE assistant_events SET acknowledged = 1 WHERE event = ? AND acknowledged = 0", (event,))
            conn.commit()

    def acknowledge_all(self):
        with DB_LOCK, sqlite3.connect(self._db, timeout=10) as conn:
            conn.execute("UPDATE assistant_events SET acknowledged = 1 WHERE acknowledged = 0")
            conn.commit()

    def get_pending_events(self, min_weight: int = 0) -> list[dict]:
        with DB_LOCK, sqlite3.connect(self._db, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT event, level, message, detail, created_at FROM assistant_events WHERE acknowledged = 0 ORDER BY created_at DESC LIMIT 20",
            )
            rows = [dict(r) for r in cur.fetchall()]
            if min_weight > 0:
                rows = [r for r in rows if EVENT_WEIGHTS.get(r["event"], 0) >= min_weight]
            return rows

    def scan_test_failure(self) -> Optional[ScanResult]:
        try:
            result = subprocess.run(
                [sys.executable, str(AC_DIR / "run_tests.py")],
                capture_output=True, text=True, timeout=60,
                encoding="utf-8", errors="replace",
            )
            output = result.stdout + result.stderr
            if "0 failed" in output or "All tests passed" in output:
                self._last_events.pop("test_failure", None)
                return None
            for line in output.split("\n"):
                if "failed" in line and "0 failed" not in line:
                    r = ScanResult("test_failure", "warning", f"测试未通过: {line.strip()[:100]}", output[:500])
                    self._save_event(r)
                    self._last_events["test_failure"] = r
                    return r
        except subprocess.TimeoutExpired:
            r = ScanResult("test_failure", "warning", "测试执行超时（>60s）")
            self._save_event(r)
            self._last_events["test_failure"] = r
            return r
        except Exception as e:
            _log.warning(f"scan_test_failure error: {e}")
        return None

    def scan_archguard(self) -> Optional[ScanResult]:
        try:
            from archguard import get_guard
            guard = get_guard()
            report = guard.full_scan()
            if report and report.get("status") == "fail":
                r = ScanResult("archguard_scan_fail", "warning", f"架构扫描失败: {report.get('summary', '')[:200]}", json.dumps(report, ensure_ascii=False)[:500])
                self._save_event(r)
                self._last_events["archguard_scan_fail"] = r
                return r
            self._last_events.pop("archguard_scan_fail", None)
        except Exception as e:
            _log.warning(f"scan_archguard error (non-fatal): {e}")
        return None

    def scan_inactivity(self) -> Optional[ScanResult]:
        try:
            with DB_LOCK, sqlite3.connect(self._db, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute(
                    "SELECT created_at FROM assistant_memory WHERE user_id = 'default' ORDER BY created_at DESC LIMIT 1",
                )
                row = cur.fetchone()
                if row is None:
                    return None
                last_active = datetime.fromisoformat(row["created_at"])
                now = datetime.now(timezone.utc)
                delta = now - last_active
                if delta > timedelta(days=3):
                    days = delta.days
                    r = ScanResult("inactivity_3days", "info", f"已 {days} 天未活跃", f"最后活跃: {row['created_at']}")
                    existing = self._find_unacknowledged("inactivity_3days")
                    if not existing:
                        self._save_event(r)
                        self._last_events["inactivity_3days"] = r
                        return r
            self._last_events.pop("inactivity_3days", None)
        except Exception as e:
            _log.warning(f"scan_inactivity error: {e}")
        return None

    def scan_deadlines(self) -> Optional[ScanResult]:
        try:
            with DB_LOCK, sqlite3.connect(self._db, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute(
                    "SELECT topic, content, created_at FROM assistant_memory WHERE topic LIKE 'deadline_%' AND memory_type = 'long_term' ORDER BY created_at DESC LIMIT 10",
                )
                now = datetime.now(timezone.utc)
                for row in cur.fetchall():
                    try:
                        deadline_info = json.loads(row["content"])
                        due = datetime.fromisoformat(deadline_info.get("due", ""))
                        if due < now and not deadline_info.get("completed"):
                            name = deadline_info.get("name", row["topic"])
                            r = ScanResult("deadline_overdue", "warning", f"截止日期已过: {name}", f"到期: {due.isoformat()}")
                            existing = self._find_unacknowledged("deadline_overdue")
                            if not existing:
                                self._save_event(r)
                                self._last_events["deadline_overdue"] = r
                                return r
                        else:
                            self._last_events.pop("deadline_overdue", None)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        except Exception as e:
            _log.warning(f"scan_deadlines error: {e}")
        return None

    def scan_late_night(self) -> Optional[ScanResult]:
        try:
            now = datetime.now(timezone.utc)
            hour = (now + timedelta(hours=8)).hour
            if hour < 6 or hour >= 23:
                with DB_LOCK, sqlite3.connect(self._db, timeout=10) as conn:
                    conn.row_factory = sqlite3.Row
                    cur = conn.execute(
                        "SELECT created_at FROM assistant_memory WHERE user_id = 'default' ORDER BY created_at DESC LIMIT 1",
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    last_active = datetime.fromisoformat(row["created_at"])
                    if (now - last_active) < timedelta(minutes=30):
                        existing = self._find_unacknowledged("late_night_active")
                        if not existing:
                            r = ScanResult("late_night_active", "info", "深夜了，还不睡吗")
                            self._save_event(r)
                            self._last_events["late_night_active"] = r
                            return r
            self._last_events.pop("late_night_active", None)
        except Exception as e:
            _log.warning(f"scan_late_night error: {e}")
        return None

    def scan_silence_after_emotional(self) -> Optional[ScanResult]:
        try:
            with DB_LOCK, sqlite3.connect(self._db, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute(
                    "SELECT created_at FROM assistant_events WHERE event = 'emotional_crisis_keyword' AND acknowledged = 0 ORDER BY created_at DESC LIMIT 1",
                )
                crisis_event = cur.fetchone()
                if crisis_event:
                    cur2 = conn.execute(
                        "SELECT created_at FROM assistant_memory WHERE memory_type = 'long_term' AND topic = 'query' AND user_id = 'default' ORDER BY created_at DESC LIMIT 1",
                    )
                    last_query = cur2.fetchone()
                    if last_query:
                        crisis_time = datetime.fromisoformat(crisis_event["created_at"])
                        query_time = datetime.fromisoformat(last_query["created_at"])
                        if query_time < crisis_time:
                            now = datetime.now(timezone.utc)
                            delta = now - crisis_time
                            if delta > timedelta(hours=2) and delta < timedelta(hours=48):
                                existing = self._find_unacknowledged("silence_after_emotional_crisis")
                                if not existing:
                                    r = ScanResult("silence_after_emotional_crisis", "info", "上次聊完之后你一直没说话，还好吗")
                                    self._save_event(r)
                                    self._last_events["silence_after_emotional_crisis"] = r
                                    return r
            self._last_events.pop("silence_after_emotional_crisis", None)
        except Exception as e:
            _log.warning(f"scan_silence_after_emotional error: {e}")
        return None

    def full_scan(self) -> list[ScanResult]:
        results = []
        for scan_method in [
            self.scan_test_failure,
            self.scan_archguard,
            self.scan_inactivity,
            self.scan_deadlines,
            self.scan_late_night,
            self.scan_silence_after_emotional,
        ]:
            try:
                r = scan_method()
                if r:
                    results.append(r)
            except Exception as e:
                _log.warning(f"scan error in {scan_method.__name__}: {e}")
        return results

    def summary(self) -> str:
        pending = self.get_pending_events(min_weight=1)
        if not pending:
            return ""
        lines = ["**森林守望者提醒：**"]
        for ev in pending:
            icon = {"test_failure": "测试", "archguard_scan_fail": "架构", "deadline_overdue": "截止", "inactivity_3days": "静默", "emotional_crisis_keyword": "情绪", "late_night_active": "夜深", "silence_after_emotional_crisis": "安静"}.get(ev["event"], ev["event"])
            lines.append(f"- `{icon}` {ev['message'][:80]}")
        lines.append("")
        lines.append("需要我处理什么吗？")
        return "\n".join(lines)


_engine: Optional[ProactiveEngine] = None


def get_engine(db_path: str = "") -> ProactiveEngine:
    global _engine
    if _engine is None:
        _engine = ProactiveEngine(db_path)
    return _engine
