"""模型注册表 · 所有适配器在此注册，统一通过路由访问"""

from typing import Any
from .base import ModelAdapter


class ModelRegistry:
    def __init__(self):
        self._adapters: dict[str, ModelAdapter] = {}

    def register(self, adapter: ModelAdapter) -> None:
        if adapter.name in self._adapters:
            raise KeyError(f"模型 '{adapter.name}' 已注册")
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> ModelAdapter | None:
        return self._adapters.get(name)

    def list(self) -> list[dict[str, Any]]:
        return [
            {"name": a.name, "model_id": a.model_id, "available": a.is_available()}
            for a in self._adapters.values()
        ]

    def available(self) -> list[ModelAdapter]:
        return [a for a in self._adapters.values() if a.is_available()]


_REGISTRY: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ModelRegistry()
    return _REGISTRY


def reset_registry():
    global _REGISTRY
    _REGISTRY = None
