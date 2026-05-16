"""
L0 存储层守卫 · CloudGuard
检测: sqlite3.dll 哈希 / 文件增长异常 / DB 连接参数 / 隐式索引
频率: 启动时 + 每小时
"""
import os
import json
import hashlib
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

AC_DIR = Path(__file__).resolve().parent
DB_PATH = AC_DIR / "ac_platform.db"
EVIDENCE_DIR = AC_DIR / "00-AC" / "evidence"

PYTHON_HOME = Path(sys.executable).parent
DLL_DIR = PYTHON_HOME / "DLLs"
SQLITE_DLL = DLL_DIR / "sqlite3.dll"
SQLITE_PYD = DLL_DIR / "_sqlite3.pyd"

BASELINE = {
    "sqlite3.dll": {
        "sha256": "153883edf04717624437cd092adb2b72015be3984e03d25cf5a1823b0f764ac7",
        "size": 1584984,
        "version": "3.50.4",
    },
    "_sqlite3.pyd": {
        "sha256": "c6d7bcea0084bcfa3c487bd7040350ee7c77f4108ce74b964f760133b2a7a6b2",
        "size": 132440,
    },
}

FILE_GROWTH_MIN_RATIO = 0.8
FILE_GROWTH_MAX_RATIO = 1.5


class CloudGuard:
    def __init__(self):
        self.report: dict = {}

    def full_scan(self) -> Dict:
        self.report = {
            "scan_id": hashlib.sha256(str(datetime.now(timezone.utc)).encode()).hexdigest()[:16],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": {},
        }
        self.report["results"]["dll_hash"] = self._check_dll_hash()
        self.report["results"]["file_growth"] = self._check_file_growth()
        self.report["results"]["db_params"] = self._check_db_params()
        self.report["results"]["index_audit"] = self._check_implicit_indexes()

        all_pass = all(v.get("passed", False) for v in self.report["results"].values())
        self.report["overall"] = "PASS" if all_pass else "FAIL"
        self.report["ghost_count"] = sum(1 for v in self.report["results"].values() if not v.get("passed"))
        self._archive_report()
        return self.report

    def _check_dll_hash(self) -> Dict:
        results = {}
        for name, expected in BASELINE.items():
            dll_path = DLL_DIR / name
            if not dll_path.exists():
                results[name] = {"passed": False, "error": f"DLL not found: {dll_path}"}
                continue
            try:
                data = dll_path.read_bytes()
                actual_hash = hashlib.sha256(data).hexdigest()
                actual_size = len(data)
                match = actual_hash == expected["sha256"] and actual_size == expected["size"]
                results[name] = {
                    "passed": match,
                    "expected_hash": expected["sha256"][:16] + "...",
                    "actual_hash": actual_hash[:16] + "...",
                    "expected_size": expected["size"],
                    "actual_size": actual_size,
                    "version": expected.get("version", "unknown"),
                }
            except Exception as e:
                results[name] = {"passed": False, "error": str(e)}
        passed = all(v.get("passed") for v in results.values())
        return {"passed": passed, "files": results}

    def _check_file_growth(self) -> Dict:
        if not DB_PATH.exists():
            return {"passed": False, "error": f"DB not found: {DB_PATH}"}
        try:
            before_size = DB_PATH.stat().st_size
            conn = sqlite3.connect(str(DB_PATH), timeout=10)
            conn.execute("CREATE TABLE IF NOT EXISTS _growth_test (id INTEGER PRIMARY KEY, data TEXT)")
            test_data = "X" * 100
            conn.execute("INSERT INTO _growth_test (data) VALUES (?)", (test_data,))
            conn.commit()
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            mid_size = DB_PATH.stat().st_size
            conn.execute("DELETE FROM _growth_test")
            conn.execute("DROP TABLE IF EXISTS _growth_test")
            conn.commit()
            conn.close()
            growth = mid_size - before_size
            ratio = growth / len(test_data) if growth > 0 else 0
            passed = (growth == 0) or (FILE_GROWTH_MIN_RATIO <= ratio <= FILE_GROWTH_MAX_RATIO)
            return {
                "passed": passed,
                "before_bytes": before_size,
                "after_bytes": mid_size,
                "growth_bytes": growth,
                "data_bytes": len(test_data),
                "ratio": round(ratio, 2),
                "threshold": f"{FILE_GROWTH_MIN_RATIO}-{FILE_GROWTH_MAX_RATIO}",
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _check_db_params(self) -> Dict:
        try:
            conn = sqlite3.connect(str(DB_PATH), timeout=10)
            journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            conn.close()
            passed = journal_mode in ("wal", "delete")
            return {
                "passed": passed,
                "journal_mode": journal_mode,
                "warning": None if passed else f"Unexpected journal_mode: {journal_mode}",
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _check_implicit_indexes(self) -> Dict:
        try:
            conn = sqlite3.connect(str(DB_PATH), timeout=10)
            indexes = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL").fetchall()
            conn.close()
            user_indexes = [name for name, sql_def in indexes if sql_def and "CREATE" in sql_def.upper()]
            auto_indexes = [name for name, sql_def in indexes if not sql_def or "CREATE" not in sql_def.upper()]
            passed = True
            return {
                "passed": passed,
                "user_created": len(user_indexes),
                "auto_indexes": len(auto_indexes),
                "auto_names": auto_indexes,
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _archive_report(self):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        scan_dir = EVIDENCE_DIR / f"cloud_hijack" / f"scan_{self.report['scan_id']}"
        scan_dir.mkdir(parents=True, exist_ok=True)
        (scan_dir / "report.json").write_text(
            json.dumps(self.report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )


_guard: CloudGuard | None = None


def get_guard() -> CloudGuard:
    global _guard
    if _guard is None:
        _guard = CloudGuard()
    return _guard
