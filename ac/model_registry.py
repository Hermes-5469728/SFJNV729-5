"""模型路由表 · 按任务类型分派模型 · 主备自动切换

原则:
  1. 模型选择通过配置，不硬编码在业务代码中
  2. 每个任务类型必须配置 fallback 模型
  3. API 凭证存储在 .env 文件，禁止硬编码
  4. 换模型 → 改 MODEL_REGISTRY 字典即可，业务代码零改动
"""

from ac.adapters.registry import get_registry
from ac.adapters.base import ModelAdapter

MODEL_REGISTRY = {
    "reasoning": {
        "primary": "deepseek-free",
        "fallback": "qwen-free",
    },
    "lightweight": {
        "primary": "doubao",
        "fallback": "deepseek-free",
    },
    "long_context": {
        "primary": "kimi",
        "fallback": "qwen-free",
    },
    "code": {
        "primary": "deepseek-free",
        "fallback": "kimi",
    },
}

_DEFAULT_TASK = "reasoning"


def get_model(task_type: str = "reasoning", prefer_free: bool = True) -> ModelAdapter | None:
    """根据任务类型获取模型适配器，自动检测可用性并降级

    Args:
        task_type: 任务类型 (reasoning, lightweight, long_context, code)
        prefer_free: 是否优先免费层（预留，当前仅影响日志）

    Returns:
        ModelAdapter 或 None（所有模型不可用）
    """
    group = MODEL_REGISTRY.get(task_type, MODEL_REGISTRY[_DEFAULT_TASK])
    registry = get_registry()

    primary_name = group["primary"]
    primary = registry.get(primary_name)
    if primary and primary.is_available() and primary.health_check():
        return primary

    fallback_name = group["fallback"]
    fallback = registry.get(fallback_name)
    if fallback and fallback.is_available() and fallback.health_check():
        return fallback

    available = registry.available()
    if available:
        return available[0]

    return None


def list_tasks() -> list[dict]:
    """列出所有任务类型及其当前可用模型"""
    registry = get_registry()
    result = []
    for task, group in MODEL_REGISTRY.items():
        primary = registry.get(group["primary"])
        fallback = registry.get(group["fallback"])
        result.append({
            "task": task,
            "primary": {
                "name": group["primary"],
                "available": primary.is_available() if primary else False,
            },
            "fallback": {
                "name": group["fallback"],
                "available": fallback.is_available() if fallback else False,
            },
            "active": (
                group["primary"] if (primary and primary.is_available())
                else group["fallback"] if (fallback and fallback.is_available())
                else None
            ),
        })
    return result


def get_current_model_info(task_type: str = "reasoning") -> dict:
    """返回当前任务使用的模型信息（用于仪表盘显示）"""
    model = get_model(task_type)
    if not model:
        return {"task": task_type, "active_model": None, "status": "no_available_model"}

    group = MODEL_REGISTRY.get(task_type, MODEL_REGISTRY[_DEFAULT_TASK])
    primary_active = model.name == group["primary"]

    return {
        "task": task_type,
        "active_model": model.name,
        "model_id": model.model_id,
        "is_primary": primary_active,
        "is_fallback": not primary_active,
        "is_free_tier": model.is_free_tier,
        "status": "ok",
    }
