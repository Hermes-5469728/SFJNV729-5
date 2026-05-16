"""模型路由器 · 选择适配器 → 调用 → 治理管道审计

核心原则:
  1. 所有模型调用必经此路由，禁止裸调适配器
  2. 调用结果经过治理管道（L0 编码 + L5 标注 + 安全 + 幻觉审计）
  3. 路由日志写入 ac_governance_log
"""

import sys
from pathlib import Path
_ac_dir = Path(__file__).resolve().parent
if str(_ac_dir.parent) not in sys.path:
    sys.path.insert(0, str(_ac_dir.parent))

from ac.governance import pipeline as gov_pipeline
from ac.governance.hallucination_auditor import HallucinationAuditor
from .base import ModelResponse
from .registry import get_registry, ModelRegistry


class ModelRouter:
    def __init__(self, registry: ModelRegistry | None = None):
        self.registry = registry or get_registry()
        self.auditor = HallucinationAuditor()

    def select(self, preferred: str | None = None) -> str | None:
        available = self.registry.available()
        if not available:
            return None
        if preferred and self.registry.get(preferred) and self.registry.get(preferred).is_available():
            return preferred
        return available[0].name

    def call(self, prompt: str, model: str | None = None,
             system: str | None = None, **kwargs) -> ModelResponse:
        model_name = model or self.select()
        if not model_name:
            return ModelResponse(
                model_name="none", content="",
                error="无可用模型（请设置环境变量 DEEPSEEK_FREE_API_KEY）",
            )

        adapter = self.registry.get(model_name)
        if not adapter:
            return ModelResponse(
                model_name=model_name, content="",
                error=f"模型 '{model_name}' 未注册",
            )

        result = adapter.call(prompt, system=system, **kwargs)

        if result.error:
            return result

        gov_result = gov_pipeline(result.content, {
            "command": "model_response",
            "model": model_name,
        })

        audit = self.auditor.audit(result.content)

        result.governance = {
            "passed": gov_result["passed"],
            "checks": gov_result["checks"],
            "encoding_sanitized": gov_result["encoding_sanitized"],
            "hallucination_audit": audit,
        }

        if not gov_result["passed"]:
            result.content = gov_result["text"]
            result.error = "治理检查未完全通过，内容已修正"

        return result

    def list_models(self) -> list[dict]:
        return self.registry.list()


_router: ModelRouter | None = None


def get_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


def reset_router():
    global _router
    _router = None
