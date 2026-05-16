"""
AC 生命周期管理器 · 5 节点钩子
T1=启动时 T2=变更时 T3=每5分钟 T4=日终 T5=月度
"""
import os
import json
import hashlib
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

AC_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = AC_DIR / "00-AC" / "evidence"
HANDOFF_DIR = AC_DIR / "00-AC" / "handoffs"

HARD_BLOCK_LAYERS = {"L0_storage", "L3_code"}
PROD_BLOCK_LAYERS = {"L0_storage", "L1_network", "L2_process", "L3_code", "L4_dependency", "L5_config"}


def detect_env() -> str:
    return os.environ.get("AC_ENV", "dev")


def get_env_config() -> Dict:
    env = detect_env()
    if env == "prod":
        return {"scan_depth": "full", "block_on_fail": True, "frequency": "continuous"}
    elif env == "ci":
        return {"scan_depth": "full", "block_on_fail": True, "frequency": "once"}
    else:
        return {"scan_depth": "full", "block_on_fail": False, "frequency": "on_startup"}


class ACLifecycle:
    def __init__(self):
        self.env = detect_env()
        self.config = get_env_config()

    def on_startup(self):
        from ac.full_scan import full_range_scan
        result = full_range_scan()
        env_config = get_env_config()
        failed_critical = False

        for layer, data in result["results"].items():
            if data and not data.get("passed") and data.get("passed") is not None:
                if layer in (PROD_BLOCK_LAYERS if env_config["block_on_fail"] else HARD_BLOCK_LAYERS):
                    failed_critical = True

        if failed_critical and env_config["block_on_fail"]:
            raise SystemError(f"架构扫描失败，{self.env} 环境拒绝启动。Failed layers in {PROD_BLOCK_LAYERS}")
        elif failed_critical:
            print("[WARN] 架构扫描未通过（HARD_BLOCK_LAYERS），但非生产环境继续运行")

        return result

    def on_git_push(self):
        from ac.archguard import ArchGuard
        result = ArchGuard().full_scan()
        from ac.cloud_guard import CloudGuard
        l0 = CloudGuard().full_scan()

        if result["overall"] != "PASS":
            raise SystemError(f"L3 代码层扫描失败，禁止推送: {result['ghost_count']} ghosts")
        if l0["overall"] != "PASS":
            raise SystemError(f"L0 存储层扫描失败，禁止推送")
        return True

    def on_timer_5min(self):
        from ac.cloud_guard import CloudGuard
        l0 = CloudGuard().full_scan()
        issues = []
        if l0["overall"] != "PASS":
            issues.append("L0_storage")
        return {"issues": issues, "fatal": False}

    def on_daily(self):
        try:
            from ac.archguard import ArchGuard
            ag = ArchGuard().full_scan()
        except Exception:
            ag = {"overall": "UNKNOWN"}
        try:
            from ac.cloud_guard import CloudGuard
            cg = CloudGuard().full_scan()
        except Exception:
            cg = {"overall": "UNKNOWN"}

        report = {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "archguard": ag.get("overall"),
            "cloudguard": cg.get("overall"),
        }
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        fp = EVIDENCE_DIR / f"daily_{report['date']}.json"
        fp.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return report

    def on_monthly(self):
        from ac.full_scan import full_range_scan
        result = full_range_scan()

        if not result.get("overall") == "PASS":
            print(f"[WARN] 月度全量扫描未通过: {result['ghost_count']} ghosts")

        month = datetime.now(timezone.utc).strftime("%Y%m")
        health_path = EVIDENCE_DIR / f"environment_health_{month}.md"
        if not health_path.exists():
            lines = [
                f"# 环境健康月度报告 · {month}",
                "",
                f"扫描时间: {result['timestamp']}",
                f"整体: {result['overall']}",
                f"异常层: {result['ghost_count']}",
                "",
                "| 层级 | 状态 | 详情 |",
                "|------|------|------|",
            ]
            for layer, data in result["results"].items():
                status = "SKIP" if not data else ("PASS" if data.get("passed") else "FAIL" if data.get("passed") is None else "WARN")
                detail = data.get("note", data.get("error", "")) if data else ""
                lines.append(f"| {layer} | {status} | {detail[:100]} |")
            health_path.write_text("\n".join(lines), encoding="utf-8")

        return result
