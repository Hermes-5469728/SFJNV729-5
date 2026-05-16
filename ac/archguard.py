"""
架构卫士 · 自动化架构审计服务
替代人工进行猎鬼、端点验证、导入完整性检查
每次扫描生成不可销毁的审计报告
"""

import os
import json
import hashlib
import subprocess
import sys
import importlib
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

AC_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = AC_DIR / "00-AC" / "evidence"
DB_PATH = AC_DIR / "ac_platform.db"

# Fix import path: add parent directory to sys.path so 'ac' package is importable
# When running from {USER_HOME}\ac\archguard.py:
#   - AC_DIR = {USER_HOME}\ac
#   - we need {USER_HOME} in sys.path to import 'ac' as a package
_parent_dir = str(AC_DIR.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)


class ArchGuard:
    """自动化架构审计引擎"""

    def __init__(self):
        self.report: dict = {}

    def full_scan(self) -> Dict:
        """全量架构扫描，返回完整报告"""
        self.report = {
            "scan_id": hashlib.sha256(str(datetime.now(timezone.utc)).encode()).hexdigest()[:16],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": {}
        }

        self.report["results"]["fraud_test"] = self._run_fraud_tests()
        self.report["results"]["endpoint_verify"] = self._verify_endpoints()
        self.report["results"]["pipeline_check"] = self._check_pipeline()
        self.report["results"]["core_reachable"] = self._check_core()
        self.report["results"]["bus_guard"] = self._check_bus_guard()
        self.report["results"]["hunt_status"] = self._check_hunt_status()
        self.report["results"]["sql_integrity"] = self._check_sql_integrity()
        self.report["results"]["directory_compliance"] = self._check_directory_compliance()

        all_pass = all(v.get("passed", False) for v in self.report["results"].values())
        self.report["overall"] = "PASS" if all_pass else "FAIL"
        self.report["ghost_count"] = sum(
            1 for v in self.report["results"].values() if not v.get("passed")
        )

        self._archive_report()
        return self.report

    def _run_fraud_tests(self) -> Dict:
        """运行测试套件（run_tests.py）"""
        try:
            result = subprocess.run(
                [sys.executable, str(AC_DIR / "run_tests.py")],
                capture_output=True, text=True, timeout=120,
                cwd=str(AC_DIR), encoding="utf-8", errors="replace",
            )
            output = result.stdout + result.stderr
            failed = output.count("[FAIL]")
            passed = output.count("[PASS]")
            return {
                "passed": failed == 0 and passed > 0,
                "passed_count": passed,
                "failed_count": failed,
                "output": output[-300:],
            }
        except FileNotFoundError:
            return {"passed": False, "error": "run_tests.py 不存在"}
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _verify_endpoints(self) -> Dict:
        """对比 CLI dispatch 和核心 dispatch 输出一致性"""
        try:
            query = "帮助"
            cli = subprocess.run(
                [sys.executable, str(AC_DIR / "cli.py"), "dispatch", query, "--no-gov"],
                capture_output=True, text=True, timeout=30,
                cwd=str(AC_DIR), encoding="utf-8", errors="replace",
            )
            out = cli.stdout
            brace_start = out.find("{")
            brace_end = out.rfind("}") + 1
            cli_data = json.loads(out[brace_start:brace_end]) if brace_start >= 0 else {"status": "parse_error"}

            from ac.core import dispatch as real_dispatch
            server_data = real_dispatch(query)

            consistent = cli_data.get("status") == server_data.get("status")
            return {
                "passed": consistent,
                "cli_status": cli_data.get("status"),
                "server_status": server_data.get("status"),
                "query": query,
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _check_pipeline(self) -> Dict:
        """治理管道存活检查"""
        try:
            from ac.governance import pipeline
            result = pipeline("test", {"command": "model_response"})
            return {
                "passed": True,
                "alive": True,
                "checks": len(result.get("checks", [])),
            }
        except ImportError:
            try:
                import ac.governance as gov
                return {
                    "passed": hasattr(gov, "checker") or hasattr(gov, "Pipeline"),
                    "alive": True,
                    "checks": "module_exists",
                }
            except Exception as e:
                return {"passed": False, "error": str(e)}
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _check_core(self) -> Dict:
        """AC 核心可达性"""
        try:
            from ac.core import dispatch, annotate, status
            r = dispatch("test", session_id="archguard")
            return {
                "passed": r.get("status") is not None,
                "modules": ["core.dispatch", "core.annotate", "core.status"],
                "dispatch_result": r.get("status"),
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _check_bus_guard(self) -> Dict:
        """守卫日志完整性"""
        try:
            conn = sqlite3.connect(str(DB_PATH), timeout=10)
            conn.row_factory = sqlite3.Row
            guard_count = conn.execute("SELECT COUNT(*) FROM ac_guard_log").fetchone()[0]
            guards = conn.execute("SELECT DISTINCT guard FROM ac_guard_log").fetchall()
            conn.close()
            guard_names = [r["guard"] for r in guards]
            passed = guard_count > 0
            return {
                "passed": passed,
                "intact": passed,
                "guard_count": guard_count,
                "active_guards": guard_names or ["暂无守卫记录"],
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _check_hunt_status(self) -> Dict:
        """最近猎鬼状态（含 handoff receipts）"""
        ghosts = []
        if EVIDENCE_DIR.is_dir():
            for f in sorted(EVIDENCE_DIR.rglob("*")):
                if not f.is_file():
                    continue
                if f.suffix not in (".txt", ".md", ".json"):
                    continue
                if f.parent.name.startswith("autoscan_"):
                    continue
                ghosts.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
                })
        passed = len(ghosts) > 0
        return {
            "passed": passed,
            "date": ghosts[-1]["modified"][:10] if ghosts else "无",
            "ghost_count": len(ghosts),
            "latest": ghosts[-1] if ghosts else None,
        }

    def _check_sql_integrity(self) -> Dict:
        """SQL 执行计划一致性检查: 检测云服务商隐式查询改写"""
        try:
            from ac.knowledge_service import KnowledgeService, HIJACK_KEYWORDS
            ks = KnowledgeService(str(DB_PATH))
            test_queries = ["布洛芬", "焦虑", "失眠"]
            hijacked_queries = []

            for q in test_queries:
                plan = ks._verify_sql_plan(
                    q,
                    f"SELECT * FROM ac_truth WHERE content LIKE '%{q.replace(chr(39), chr(39)+chr(39))}%' LIMIT 3"
                )
                if not plan["clean"]:
                    hijacked_queries.append({
                        "query": q,
                        "keywords": plan["hijacked_keywords"],
                        "plan": plan["plan"][:200],
                    })

            passed = len(hijacked_queries) == 0
            return {
                "passed": passed,
                "queries_tested": len(test_queries),
                "hijacked_count": len(hijacked_queries),
                "hijacked_queries": hijacked_queries,
                "guard_keywords": HIJACK_KEYWORDS,
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _check_directory_compliance(self) -> Dict:
        """目录结构合规检查 · 按 PROJECT_STRUCTURE.md 宪法执行"""
        violations = []
        AC_WHITELIST = {"PROJECT_STRUCTURE.md", "README.md", ".gitignore"}

        def _iter_files(d: Path):
            """遍历目录下所有文件，跳过 __pycache__ 和隐藏目录"""
            for f in d.rglob("*"):
                if f.is_file() and "__pycache__" not in f.parts:
                    yield f

        # ac/ 顶层只能有 .py 文件（白名单除外）
        for f in AC_DIR.iterdir():
            if f.is_file() and f.suffix != ".py" and f.name not in AC_WHITELIST:
                violations.append(f"ac/ 顶层禁止 {f.suffix} 文件: {f.name}")

        # site/ 下不能有 .py 文件
        site_dir = AC_DIR / "site"
        if site_dir.exists():
            for f in _iter_files(site_dir):
                if f.suffix == ".py":
                    violations.append(f"site/ 禁止 .py 文件: {f.relative_to(AC_DIR)}")

        # tests/ 下只能放 test_*.py（允许 __init__.py + 数据文件 .db/.json/.txt 用于测试）
        tests_dir = AC_DIR / "tests"
        if tests_dir.exists():
            for f in tests_dir.glob("*.py"):
                if not f.name.startswith("test_") and f.name != "__init__.py" and not f.name.startswith("_"):
                    violations.append(f"tests/ 非测试 .py: {f.name}")

        # docs/ 下只能放 .md
        docs_dir = AC_DIR / "00-AC" / "docs"
        if docs_dir.exists():
            for f in _iter_files(docs_dir):
                if f.suffix != ".md":
                    violations.append(f"docs/ 只能放 .md: {f.relative_to(AC_DIR)}")

        # handoffs/ 下只能放 .md
        handoffs_dir = AC_DIR / "00-AC" / "handoffs"
        if handoffs_dir.exists():
            for f in _iter_files(handoffs_dir):
                if f.suffix != ".md":
                    violations.append(f"handoffs/ 只能放 .md: {f.relative_to(AC_DIR)}")

        # evidence/ 下不能有 .py 文件（允许 .json/.txt/.md）
        evidence_dir = AC_DIR / "00-AC" / "evidence"
        if evidence_dir.exists():
            for f in _iter_files(evidence_dir):
                if f.suffix == ".py":
                    violations.append(f"evidence/ 禁止 .py 文件: {f.relative_to(AC_DIR)}")

        # governance/ 下只能放 .py
        gov_dir = AC_DIR / "governance"
        if gov_dir.exists():
            for f in _iter_files(gov_dir):
                if f.suffix != ".py":
                    violations.append(f"governance/ 只能放 .py: {f.relative_to(AC_DIR)}")

        # adapters/ 下只能放 .py
        adapters_dir = AC_DIR / "adapters"
        if adapters_dir.exists():
            for f in _iter_files(adapters_dir):
                if f.suffix != ".py":
                    violations.append(f"adapters/ 只能放 .py: {f.relative_to(AC_DIR)}")

        # 免疫措施：检测硬编码的旧路径（防止路径引用复发）
        FORBIDDEN_PATH = r"{USER_HOME}\ac"
        for f in _iter_files(AC_DIR):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                if FORBIDDEN_PATH in content:
                    violations.append(f"硬编码旧路径: {f.relative_to(AC_DIR)}")
            except Exception:
                pass

        return {
            "passed": len(violations) == 0,
            "violations": violations,
        }

    def _archive_report(self):
        """将扫描报告归档"""
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        scan_dir = EVIDENCE_DIR / f"autoscan_{self.report['scan_id']}"
        scan_dir.mkdir(exist_ok=True)

        (scan_dir / "report.json").write_text(
            json.dumps(self.report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        lines = [f"自动扫描 {self.report['timestamp']}",
                 f"整体: {self.report['overall']}",
                 f"活跃异常: {self.report['ghost_count']}"]
        for name, result in self.report["results"].items():
            status = "OK" if result.get("passed") else "FAIL"
            lines.append(f"  [{status}] {name}")
        (scan_dir / "summary.txt").write_text("\n".join(lines), encoding="utf-8")


_guard: ArchGuard | None = None


def get_guard() -> ArchGuard:
    global _guard
    if _guard is None:
        _guard = ArchGuard()
    return _guard
