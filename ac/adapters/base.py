"""模型适配器基类 · 所有 LLM 接入点必须实现此接口"""

import time
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any


@dataclass
class ModelResponse:
    model_name: str
    content: str
    raw: dict | None = None
    latency_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    error: str | None = None
    governance: dict | None = None


class ModelAdapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        ...

    @abstractmethod
    def call(self, prompt: str, **kwargs) -> ModelResponse:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """快速检查服务是否可用（真实调用 API，不只是查 key 是否存在）"""
        ...

    @property
    def is_free_tier(self) -> bool:
        """是否免费层——影响配额感知路由"""
        return False

    def _timed_health_check(self, timeout: float = 10.0, test_prompt: str = "ping") -> bool:
        """通用 health_check 实现：发送短 prompt 测试连通性"""
        try:
            start = time.time()
            result = self.call(test_prompt, max_tokens=5, timeout=int(timeout))
            elapsed = (time.time() - start) * 1000
            return result.error is None and elapsed < timeout * 1000
        except Exception:
            return False
