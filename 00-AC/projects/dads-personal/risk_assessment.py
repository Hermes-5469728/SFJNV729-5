from pathlib import Path
import importlib.util
import sys

_spec = importlib.util.spec_from_file_location(
    "ac_core",
    str(Path(__file__).resolve().parent.parent / "ac-core" / "__init__.py"),
)
_ac_core = importlib.util.module_from_spec(_spec)
sys.modules["ac_core"] = _ac_core
_spec.loader.exec_module(_ac_core)

from .protection_rules import query_protection_rules  # noqa: E402


class DoctorRiskAgent(_ac_core.BaseAgent):
    SEVERITY_MAP = {
        "critical": {"emoji": "\U0001f534", "label": "\u5371\u91cd"},
        "severe":   {"emoji": "\U0001f7e0", "label": "\u91cd\u5ea6"},
        "moderate": {"emoji": "\U0001f7e1", "label": "\u4e2d\u5ea6"},
        "mild":     {"emoji": "\U0001f7e2", "label": "\u8f7b\u5ea6"},
    }

    def think(self, user_input: str) -> list:
        self.memory.add({"role": "user", "content": user_input})
        query_protection_rules(user_input)
        steps = self.planner.decompose(user_input)
        self.memory.add({"role": "assistant", "content": {"steps": steps}})
        return steps

    def assess(self, description: str) -> dict:
        self.think(description)
        return self._analyze(description)

    def _analyze(self, description: str) -> dict:
        matches = query_protection_rules(description)

        if matches:
            top = matches[0]
            confidence = top["confidence_base"]
            if len(matches) > 1:
                confidence = max(0.25, confidence * 0.85)
            return {
                "scenario": top["scenario"],
                "rule_id": top["id"],
                "severity": top["severity"],
                "confidence": confidence,
                "advice": top["advice"],
            }

        return {
            "scenario": "\u5f85\u8bc4\u4f30\u573a\u666f\uff08\u63cf\u8ff0: " + description[:20] + "\uff09",
            "rule_id": "PR-000",
            "severity": "mild",
            "confidence": 0.30,
            "advice": (
                "\u5efa\u8bae\u8be6\u7ec6\u63cf\u8ff0\u60c5\u5883\uff0c\u5305\u542b\u5173\u952e\u98ce\u9669\u70b9"
                "\uff08\u5982\u8d39\u7528\u3001\u6cbb\u7597\u98ce\u9669\u3001\u6c9f\u901a\u7b49\uff09\uff0c\u4ee5\u4fbf\u7cbe\u51c6\u5339\u914d\u9632\u62a4\u89c4\u5219\u3002"
            ),
        }
