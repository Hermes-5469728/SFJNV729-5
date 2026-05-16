from typing import Any

import json
import copy
from ac.governance.checker import CheckResult


MAX_RETRIES = 3


def auto_fix_json(text: str) -> str:
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    fixed = text.strip()
    if fixed.endswith(","):
        fixed = fixed[:-1]
    try:
        json.loads(fixed)
        return fixed
    except json.JSONDecodeError:
        pass

    if fixed.count("{") > fixed.count("}"):
        fixed += "}"
    elif fixed.count("[") > fixed.count("]"):
        fixed += "]"
    try:
        json.loads(fixed)
        return fixed
    except json.JSONDecodeError:
        pass

    return text


def auto_fix_l5_header(text: str) -> str:
    markers = ["L5 强制标注", "来源链:", "声明:"]
    missing = [m for m in markers if m not in text]
    if not missing:
        return text
    return text


def correct(output: str, result: CheckResult, context: dict[str, Any] | None = None) -> tuple[str, bool]:
    if result.passed:
        return output, True

    original = output
    fixed = output

    if "JSON" in result.message or "json" in result.message:
        fixed = auto_fix_json(fixed)

    if "L5" in result.message:
        fixed = auto_fix_l5_header(fixed)

    return fixed, fixed != original


class Corrector:
    def __init__(self, max_attempts: int = MAX_RETRIES) -> None:
        self.max_attempts = max_attempts

    def run(self, output: str, check_result: CheckResult, context: dict[str, Any] | None = None) -> tuple[str, CheckResult, int]:
        current = output
        for attempt in range(self.max_attempts):
            fixed, changed = correct(current, check_result, context)
            if not changed:
                return current, check_result, attempt
            try:
                data = json.loads(fixed)
                current = json.dumps(data, ensure_ascii=False, indent=2)
                return current, CheckResult(passed=True, level="info", message=f"修正成功 (attempt {attempt + 1})"), attempt + 1
            except json.JSONDecodeError:
                current = fixed
                check_result = CheckResult(passed=False, level="error", message=f"修正后仍不合格 (attempt {attempt + 1})")

        return current, check_result, self.max_attempts
