import json
from ac.governance.checker import BaseChecker, CheckResult
from ac.seed import PRIORITY_MAP, EXPERTS

VALID_PRIORITIES = set(PRIORITY_MAP.keys())
KNOWN_EXPERT_NAMES = {e["name"] for e in EXPERTS}


class DomainSemanticChecker(BaseChecker):
    @property
    def name(self) -> str:
        return "domain_semantic"

    def check(self, text: str, context: dict | None = None) -> CheckResult:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return CheckResult(passed=True, level="warning", message="非 JSON 输出,跳过语义校验")

        issues = []
        for i, m in enumerate(data.get("matched", [])):
            name = m.get("name", "")
            priority = m.get("priority", "")
            lease = m.get("lease", 0)

            if name and name not in KNOWN_EXPERT_NAMES:
                issues.append(f"matched[{i}]: 未知专家名 '{name}'")

            if priority and priority not in VALID_PRIORITIES:
                issues.append(f"matched[{i}]: 无效优先级 '{priority}'")

            if isinstance(lease, int) and lease <= 0:
                issues.append(f"matched[{i}]: 租约轮数必须 >0 (got {lease})")

        if issues:
            return CheckResult(passed=False, level="warning", message="语义校验发现异常", details={"issues": issues})

        return CheckResult(passed=True, level="info", message="语义校验通过")
