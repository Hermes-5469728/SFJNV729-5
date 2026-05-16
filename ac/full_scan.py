"""
全范围架构扫描 · 统一入口
7 层扫描: L0 存储 → L1 网络 → L2 进程 → L3 代码 → L4 依赖 → L5 配置 → L6 运行时
调用: from ac.full_scan import full_range_scan; results = full_range_scan()
"""
import json
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

AC_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = AC_DIR / "00-AC" / "evidence"

LAYERS = ["L0_storage", "L1_network", "L2_process", "L3_code", "L4_dependency", "L5_config", "L6_runtime"]


def full_range_scan() -> Dict:
    report = {
        "scan_id": hashlib.sha256(str(datetime.now(timezone.utc)).encode()).hexdigest()[:16],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": {},
    }

    report["results"]["L0_storage"] = _scan_l0()
    report["results"]["L1_network"] = _scan_l1()
    report["results"]["L2_process"] = _scan_l2()
    report["results"]["L3_code"] = _scan_l3()
    report["results"]["L4_dependency"] = _scan_l4()
    report["results"]["L5_config"] = _scan_l5()
    report["results"]["L6_runtime"] = _scan_l6()

    impl_results = {k: v for k, v in report["results"].items() if v and v.get("passed") is not None}
    all_pass = all(v.get("passed", False) for v in impl_results.values())
    report["overall"] = "PASS" if all_pass and impl_results else ("FAIL" if impl_results else "PENDING")
    report["ghost_count"] = sum(1 for v in impl_results.values() if not v.get("passed"))
    _archive(report)
    return report


def _scan_l0() -> Dict:
    try:
        from ac.cloud_guard import CloudGuard
        cg = CloudGuard().full_scan()
        return {
            "passed": cg.get("overall") == "PASS",
            "details": {k: v for k, v in cg.get("results", {}).items()},
            "scan_id": cg.get("scan_id"),
        }
    except ImportError:
        return {"passed": False, "error": "cloud_guard.py not found"}
    except Exception as e:
        return {"passed": False, "error": str(e)}


def _scan_l1() -> Dict:
    try:
        from ac.network_guard import NetworkGuard
        return NetworkGuard().full_scan()
    except ImportError:
        return {"passed": None, "status": "skeleton", "note": "network_guard.py not yet implemented"}
    except Exception as e:
        return {"passed": False, "error": str(e)}


def _scan_l2() -> Dict:
    try:
        from ac.process_guard import ProcessGuard
        return ProcessGuard().full_scan()
    except ImportError:
        return {"passed": None, "status": "skeleton", "note": "process_guard.py not yet implemented"}
    except Exception as e:
        return {"passed": False, "error": str(e)}


def _scan_l3() -> Dict:
    try:
        from ac.archguard import ArchGuard
        ag = ArchGuard().full_scan()
        return {
            "passed": ag.get("overall") == "PASS",
            "details": {k: v for k, v in ag.get("results", {}).items()},
            "scan_id": ag.get("scan_id"),
        }
    except Exception as e:
        return {"passed": False, "error": str(e)}


def _scan_l4() -> Dict:
    try:
        from ac.dependency_guard import DependencyGuard
        return DependencyGuard().full_scan()
    except ImportError:
        return {"passed": None, "status": "skeleton", "note": "dependency_guard.py not yet implemented"}
    except Exception as e:
        return {"passed": False, "error": str(e)}


def _scan_l5() -> Dict:
    try:
        from ac.config_guard import ConfigGuard
        return ConfigGuard().full_scan()
    except ImportError:
        return {"passed": None, "status": "skeleton", "note": "config_guard.py not yet implemented"}
    except Exception as e:
        return {"passed": False, "error": str(e)}


def _scan_l6() -> Dict:
    try:
        from ac.runtime_guard import RuntimeGuard
        return RuntimeGuard().full_scan()
    except ImportError:
        return {"passed": None, "status": "skeleton", "note": "runtime_guard.py not yet implemented"}
    except Exception as e:
        return {"passed": False, "error": str(e)}


def _archive(report: Dict):
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    fp = EVIDENCE_DIR / f"full_scan_{report['scan_id']}.json"
    fp.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    result = full_range_scan()
    print(f"Overall: {result['overall']} ({result['ghost_count']} ghosts)")
    for layer, data in result["results"].items():
        status = data.get("status") if data and data.get("passed") is None else ("PASS" if data and data.get("passed") else "FAIL" if data else "SKIP")
        print(f"  [{status}] {layer}")
