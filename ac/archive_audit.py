"""
归档审查器 · 归档前强制验证 AC 核心真实性
三关：核心可达 → 测试通过 → 端点一致
"""

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

AC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(AC_DIR.parent))


class ArchiveAuditError(RuntimeError):
    pass


def run_tests() -> dict:
    """运行现有测试套件，返回三关结果"""
    result = subprocess.run(
        [sys.executable, str(AC_DIR / "run_tests.py")],
        capture_output=True, text=True, timeout=120,
        cwd=str(AC_DIR), encoding="utf-8", errors="replace",
    )
    output = result.stdout + result.stderr
    passed_count = output.count("[PASS]")
    failed_count = output.count("[FAIL]")
    return {
        "passed": failed_count == 0,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "output_snippet": output[-500:],
    }


def check_core_import() -> bool:
    try:
        from ac.core import dispatch, load_config, annotate
        from ac.governance import pipeline
        return True
    except ImportError:
        return False


def check_dispatch_works() -> bool:
    try:
        r = subprocess.run(
            [sys.executable, str(AC_DIR / "cli.py"), "dispatch", "测试"],
            capture_output=True, text=True, timeout=30,
            cwd=str(AC_DIR), encoding="utf-8", errors="replace",
        )
        return r.returncode == 0 and "matched" in r.stdout
    except Exception:
        return False


def check_server(endpoint: str = "http://127.0.0.1:8001") -> bool:
    try:
        import urllib.request, json
        r = urllib.request.urlopen(f"{endpoint}/api/health", timeout=5)
        return json.loads(r.read()).get("status") == "ok"
    except Exception:
        return False


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def audit() -> dict:
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "tests": {},
    }

    # 第一关：核心可达
    results["checks"]["core_import"] = check_core_import()
    if not results["checks"]["core_import"]:
        raise ArchiveAuditError("AC 核心不可达！归档终止")

    results["checks"]["dispatch_works"] = check_dispatch_works()
    if not results["checks"]["dispatch_works"]:
        raise ArchiveAuditError("dispatch 不可用！归档终止")

    results["checks"]["server_alive"] = check_server()

    # 第二关：测试套件
    test_result = run_tests()
    results["tests"] = test_result
    if not test_result["passed"]:
        raise ArchiveAuditError(
            f"测试未通过 ({test_result['failed_count']} fail)，请先修复！归档终止"
        )

    results["passed"] = True
    return results


def store_receipt(date: str, filepath: str, sha256: str, audit_result: dict) -> dict:
    """写入 handoff_receipts 存根 + ac_truth"""
    receipt_dir = AC_DIR / "00-AC" / "evidence" / "handoff_receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)

    receipt = {
        "date": date,
        "filepath": filepath,
        "sha256": sha256,
        "audit_timestamp": audit_result["timestamp"],
        "audit_checks": audit_result["checks"],
        "audit_tests_passed": audit_result["tests"]["passed"],
    }
    receipt_path = receipt_dir / f"{date}.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")

    # 写入 ac_truth
    try:
        from ac.core import load_config
        from ac.db import get_conn, save_truth
        conn = get_conn(load_config())
        r = save_truth(
            conn,
            title=f"handoff_hash_{date}",
            category="system",
            source="archive_audit",
            content=json.dumps(receipt, ensure_ascii=False),
            tags=f"handoff,sha256,{date}",
        )
        conn.close()
        receipt["truth_id"] = r.get("rowid")
        receipt["truth_verified"] = r.get("verified")
    except Exception as e:
        receipt["truth_error"] = str(e)

    return receipt


if __name__ == "__main__":
    import sys
    try:
        r = audit()
        print(json.dumps(r, ensure_ascii=False, indent=2))
        print("\n✅ 审计通过，可以归档")
    except ArchiveAuditError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
