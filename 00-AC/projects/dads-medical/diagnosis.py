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

from .knowledge_base import query_medical_knowledge  # noqa: E402


class MedicalDiagnosis(_ac_core.BaseAgent):
    SEVERITY_MAP = {
        "critical": {"emoji": "\U0001f534", "label": "\u5371\u91cd"},
        "severe":   {"emoji": "\U0001f7e0", "label": "\u91cd\u5ea6"},
        "moderate": {"emoji": "\U0001f7e1", "label": "\u4e2d\u5ea6"},
        "mild":     {"emoji": "\U0001f7e2", "label": "\u8f7b\u5ea6"},
    }

    def think(self, user_input: str) -> list:
        self.memory.add({"role": "user", "content": user_input})
        query_medical_knowledge(user_input)
        steps = self.planner.decompose(user_input)
        self.memory.add({"role": "assistant", "content": {"steps": steps}})
        return steps

    def diagnose(self, symptoms: str) -> dict:
        self.think(symptoms)
        return self._analyze(symptoms)

    def _analyze(self, symptoms: str) -> dict:
        matches = query_medical_knowledge(symptoms)

        if matches:
            top = matches[0]
            confidence = top["confidence_base"]
            if len(matches) > 1:
                confidence = max(0.25, confidence * 0.85)
            return {
                "disease": top["disease"],
                "severity": top["severity"],
                "confidence": confidence,
                "advice": top["advice"],
            }

        return {
            "disease": f"\u5f85\u9274\u522b\u8bca\u65ad\uff08\u4e3b\u8bc9: {symptoms[:20]}\uff09",
            "severity": "mild",
            "confidence": 0.30,
            "advice": "\u5efa\u8bae\u95e8\u8bca\u5b8c\u5584\u76f8\u5173\u68c0\u67e5\uff0c\u5fc5\u8981\u65f6\u591a\u5b66\u79d1\u4f1a\u8bca",
        }
