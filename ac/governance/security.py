import re
import sys
import unicodedata
from ac.governance.checker import BaseChecker, CheckResult


_ENCODING_LOG: list[dict] = []


class EncodingProbe:
    """L0→L2 防腐层：强制所有进入治理层的数据为合法 UTF-8"""

    @staticmethod
    def sanitize(text: str) -> str:
        if not text:
            return text
        original = text
        if "\ufffd" in text:
            try:
                recovered = text.encode("latin-1").decode("utf-8")
                if "\ufffd" not in recovered:
                    text = recovered
                else:
                    text = unicodedata.normalize("NFKC", text).replace("\ufffd", "?")
            except (UnicodeEncodeError, UnicodeDecodeError, ValueError):
                text = unicodedata.normalize("NFKC", text).replace("\ufffd", "?")
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            text = text.encode("utf-8", errors="replace").decode("utf-8")
        if text != original:
            _ENCODING_LOG.append({"original_len": len(original), "sanitized_len": len(text)})
        return text

    @staticmethod
    def get_log() -> list[dict]:
        return list(_ENCODING_LOG)

    @staticmethod
    def clear_log():
        _ENCODING_LOG.clear()


class EncodingChecker(BaseChecker):
    @property
    def name(self) -> str:
        return "encoding"

    def check(self, text: str, context: dict | None = None) -> CheckResult:
        if "\ufffd" in text:
            return CheckResult(passed=False, level="error", message="输入包含 U+FFFD 替换字符（编码损坏）")
        try:
            text.encode("utf-8")
        except UnicodeEncodeError as e:
            return CheckResult(passed=False, level="error", message=f"不是合法 UTF-8: {e}")
        sanitized = EncodingProbe.get_log()
        if sanitized:
            return CheckResult(passed=True, level="warning", message=f"编码已清洗 ({len(sanitized)} 次修复)")
        return CheckResult(passed=True, level="info", message="编码校验通过")

SENSITIVE_PATTERNS = [
    (re.compile(r"(?i)\b(token|secret|password|api_key|apikey|private_key)\s*[:=]\s*['\"]?\w{8,}['\"]?"), "疑似凭证泄露"),
    (re.compile(r"(?i)(rm\s+-rf|format\s+|del\s+/f|shutdown\s+/s)"), "危险命令"),
    (re.compile(r"(?i)(eval\s*\(|exec\s*\(|os\.system\s*\(|subprocess\.call\s*\()"), "代码注入"),
]

MAX_OUTPUT_LENGTH = 100_000


class SecurityChecker(BaseChecker):
    @property
    def name(self) -> str:
        return "security"

    def check(self, text: str, context: dict | None = None) -> CheckResult:
        if len(text) > MAX_OUTPUT_LENGTH:
            return CheckResult(passed=False, level="error", message=f"输出超限 ({len(text)} > {MAX_OUTPUT_LENGTH})", details={"length": len(text)})

        findings = []
        for pattern, desc in SENSITIVE_PATTERNS:
            if pattern.search(text):
                findings.append(desc)

        if findings:
            return CheckResult(passed=False, level="error", message="安全检查未通过", details={"findings": findings})

        return CheckResult(passed=True, level="info", message="安全检查通过")
