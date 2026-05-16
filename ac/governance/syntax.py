import json
from ac.governance.checker import BaseChecker, CheckResult


REQUIRED_DISPATCH_FIELDS = {"status", "query", "session_id", "matched"}
REQUIRED_MATCHED_FIELDS = {"name", "category", "priority", "lease", "role"}
L5_HEADER_MARKERS = ["L5 强制标注", "来源链:", "声明:"]


class JSONSyntaxChecker(BaseChecker):
    @property
    def name(self) -> str:
        return "json_syntax"

    def check(self, text: str, context: dict | None = None) -> CheckResult:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return CheckResult(passed=False, level="error", message=f"JSON 解析失败: {e}", details={"error": str(e), "position": e.pos})

        missing = REQUIRED_DISPATCH_FIELDS - set(data.keys())
        if missing:
            return CheckResult(passed=False, level="error", message=f"缺少必需字段: {missing}", details={"missing_fields": list(missing)})

        if data.get("matched"):
            for i, m in enumerate(data["matched"]):
                mf = set(m.keys()) if isinstance(m, dict) else set()
                missing_m = REQUIRED_MATCHED_FIELDS - mf
                if missing_m:
                    return CheckResult(passed=False, level="error", message=f"matched[{i}] 缺少字段: {missing_m}", details={"index": i, "missing_fields": list(missing_m)})

        return CheckResult(passed=True, level="info", message="JSON 语法校验通过")


class L5HeaderChecker(BaseChecker):
    @property
    def name(self) -> str:
        return "l5_header"

    def check(self, text: str, context: dict | None = None) -> CheckResult:
        for marker in L5_HEADER_MARKERS:
            if marker not in text:
                return CheckResult(passed=False, level="error", message=f"L5 头部缺少标记: {marker}", details={"missing_marker": marker})
        return CheckResult(passed=True, level="info", message="L5 头部完整")
