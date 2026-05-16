"""AC 输出治理层 · L2 治理 + L3 修正"""

from typing import Any

from ac.governance.checker import BaseChecker, CheckerRegistry, CheckResult
from ac.governance.syntax import JSONSyntaxChecker, L5HeaderChecker
from ac.governance.semantic import DomainSemanticChecker
from ac.governance.security import SecurityChecker, EncodingChecker, EncodingProbe
from ac.governance.corrector import Corrector

__all__ = [
    "GovernancePipeline",
    "pipeline",
    "CheckerRegistry",
    "CheckResult",
    "Corrector",
]

CHECKER_REGISTRY = CheckerRegistry()
CHECKER_REGISTRY.register(EncodingChecker())         # 1: 编码校验 — 在 JSON 解析之前
CHECKER_REGISTRY.register(JSONSyntaxChecker())        # 2: 语法校验
CHECKER_REGISTRY.register(L5HeaderChecker())          # 3: L5 标注头校验
CHECKER_REGISTRY.register(DomainSemanticChecker())    # 4: 语义校验
CHECKER_REGISTRY.register(SecurityChecker())          # 5: 安全校验


def _get_checkers(command: str | None) -> list[BaseChecker]:
    all_ = CHECKER_REGISTRY.all()
    if command == "dispatch":
        return [c for c in all_ if c.name != "l5_header"]
    return all_


class GovernancePipeline:
    def __init__(self, registry: CheckerRegistry | None = None, max_retries: int = 3) -> None:
        self.registry = registry or CHECKER_REGISTRY
        self.corrector = Corrector(max_attempts=max_retries)

    def run(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        EncodingProbe.clear_log()
        # L0→L2 防腐层：强制清洗为合法 UTF-8
        text = EncodingProbe.sanitize(text)
        sanitized = bool(EncodingProbe.get_log())
        results: list[dict[str, Any]] = []
        current = text
        command = (context or {}).get("command")
        checkers = _get_checkers(command)

        for checker in checkers:
            result = checker.check(current, context)
            entry: dict[str, Any] = {"checker": checker.name, "passed": result.passed, "level": result.level, "message": result.message}

            if not result.passed:
                fixed, corrected_result, attempts = self.corrector.run(current, result, context)
                current = fixed
                entry["corrected"] = True
                entry["retries"] = attempts
                entry["result_after"] = corrected_result.message
            else:
                entry["corrected"] = False
                entry["retries"] = 0

            results.append(entry)

        all_passed = all(r["passed"] or r.get("corrected", False) for r in results)
        return {
            "passed": all_passed,
            "text": current,
            "checks": results,
            "encoding_sanitized": sanitized,
        }


_pipeline_instance = GovernancePipeline()


def pipeline(text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return _pipeline_instance.run(text, context)
