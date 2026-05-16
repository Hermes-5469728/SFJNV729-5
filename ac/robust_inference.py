"""鲁棒推理层 · 重试 + 熔断 + 缓存 + 双引擎互证

三层防护确保推理链在账号欠费、限流、接口变动时仍然存活:
  L1: 指数退避重试（同模型最多 3 次）
  L2: 熔断器（连续失败 N 次自动切断，60s 后半开试探）
  L3: 自动降级到备用模型 + 可选双引擎互证
"""

import time
import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from ac.adapters.base import ModelResponse
from ac.adapters.registry import get_registry
from ac.model_registry import get_model, get_current_model_info


@dataclass
class RobustResult:
    output: str
    model_name: str
    attempts: int
    from_cache: bool = False
    dual_verified: bool | None = None
    dual_details: dict | None = None
    from_fallback: bool = False
    circuit_breaker_triggered: bool = False
    latency_ms: float = 0.0
    error: str | None = None


class CircuitBreaker:
    """熔断器：连续失败 N 次自动切断，冷却后半开试探"""

    def __init__(self, max_failures: int = 3, cooldown: float = 60.0):
        self.max_failures = max_failures
        self.cooldown = cooldown
        self._failures: dict[str, int] = {}
        self._open_until: dict[str, float] = {}

    def record_success(self, name: str):
        self._failures[name] = 0
        self._open_until.pop(name, None)

    def record_failure(self, name: str):
        self._failures[name] = self._failures.get(name, 0) + 1
        if self._failures[name] >= self.max_failures:
            self._open_until[name] = time.time() + self.cooldown

    def is_open(self, name: str) -> bool:
        until = self._open_until.get(name)
        if until is None:
            return False
        if time.time() < until:
            return True
        self._open_until.pop(name, None)
        self._failures[name] = 0
        return False

    def state(self, name: str) -> str:
        if self.is_open(name):
            return "open"
        if self._failures.get(name, 0) > 0:
            return "half-open"
        return "closed"


class RobustInference:
    """鲁棒推理层"""

    def __init__(self, max_retries: int = 3, cache_size: int = 64):
        self.breaker = CircuitBreaker()
        self.max_retries = max_retries
        self._cache: dict[str, RobustResult] = {}
        self._cache_keys: list[str] = []
        self._cache_max = cache_size

    def infer(self, prompt: str, task_type: str = "reasoning",
              system: str | None = None, use_dual: bool = False,
              **kwargs) -> RobustResult:
        cache_key = hashlib.sha256(
            f"{task_type}:{prompt}:{system or ''}:{use_dual}".encode()
        ).hexdigest()

        if cache_key in self._cache:
            cached = self._cache[cache_key]
            return RobustResult(
                output=cached.output,
                model_name=cached.model_name,
                attempts=cached.attempts,
                from_cache=True,
                dual_verified=cached.dual_verified,
                dual_details=cached.dual_details,
                latency_ms=0,
            )

        t0 = time.time()

        model = get_model(task_type)
        if model is None:
            return RobustResult(
                output="", model_name="none", attempts=0,
                error="无可用模型",
                latency_ms=(time.time() - t0) * 1000,
            )

        current_name = model.name
        if self.breaker.is_open(current_name):
            cb_triggered = True
            fallback_model = self._resolve_fallback(task_type, exclude=current_name)
            if fallback_model:
                model = fallback_model
                current_name = model.name
            else:
                return RobustResult(
                    output="", model_name=current_name, attempts=0,
                    error=f"熔断器打开且无可用备用模型",
                    circuit_breaker_triggered=True,
                    latency_ms=(time.time() - t0) * 1000,
                )
        else:
            cb_triggered = False

        result = self._call_with_retry(model, prompt, system, **kwargs)

        dual_verified = None
        dual_details = None
        if use_dual and not result.error:
            dual_verified, dual_details = self._dual_verify(
                prompt, system, task_type, model.name
            )

        robust = RobustResult(
            output=result.content if not result.error else "",
            model_name=result.model_name,
            attempts=getattr(result, "attempts", 1),
            from_cache=False,
            dual_verified=dual_verified,
            dual_details=dual_details,
            from_fallback=cb_triggered,
            circuit_breaker_triggered=cb_triggered,
            latency_ms=(time.time() - t0) * 1000,
            error=result.error,
        )

        if not result.error:
            self._add_cache(cache_key, robust)

        return robust

    def _call_with_retry(self, model, prompt: str, system: str | None,
                         **kwargs) -> ModelResponse:
        for attempt in range(1, self.max_retries + 1):
            try:
                result = model.call(prompt, system=system, **kwargs)
                if result.error:
                    raise RuntimeError(result.error)
                self.breaker.record_success(model.name)
                setattr(result, "attempts", attempt)
                return result
            except Exception:
                self.breaker.record_failure(model.name)
                if attempt < self.max_retries:
                    wait = 2 ** (attempt - 1)
                    time.sleep(wait)
                else:
                    fallback_model = self._resolve_fallback("reasoning", exclude=model.name)
                    if fallback_model and fallback_model.name != model.name:
                        return self._call_with_retry(
                            fallback_model, prompt, system,
                            max_tokens=kwargs.get("max_tokens", 4096),
                            timeout=kwargs.get("timeout", 60),
                        )
                    return ModelResponse(
                        model_name=model.name, content="",
                        error=f"推理失败(重试{self.max_retries}次): 所有模型不可用",
                    )

        return ModelResponse(
            model_name=model.name, content="",
            error="推理失败: 未知错误",
        )

    def _resolve_fallback(self, task_type: str, exclude: str) -> Any:
        from ac.model_registry import get_model as get_task_model
        group = MODEL_REGISTRY_DICT.get(task_type, MODEL_REGISTRY_DICT["reasoning"])
        registry = get_registry()

        for candidate_name in [group["fallback"]]:
            if candidate_name == exclude:
                continue
            candidate = registry.get(candidate_name)
            if candidate and candidate.is_available():
                return candidate

        for adapter in registry.available():
            if adapter.name != exclude:
                return adapter

        return None

    def _dual_verify(self, prompt: str, system: str | None,
                     task_type: str, primary_name: str) -> tuple[bool | None, dict]:
        """双引擎验证：用备用模型跑一遍，对比结果中的数字和关键事实"""
        fallback = self._resolve_fallback(task_type, exclude=primary_name)
        if not fallback:
            return None, {"error": "无备用模型可用于双引擎验证"}

        try:
            primary_result = get_registry().get(primary_name).call(
                prompt, system=system, temperature=0.0, max_tokens=2048
            )
            fallback_result = fallback.call(
                prompt, system=system, temperature=0.0, max_tokens=2048
            )

            if primary_result.error or fallback_result.error:
                return None, {"error": "双引擎验证中某模型调用失败"}

            p_nums = set(re.findall(r'\d+\.?\d*', primary_result.content))
            f_nums = set(re.findall(r'\d+\.?\d*', fallback_result.content))
            nums_consistent = p_nums == f_nums

            p_len = len(primary_result.content)
            f_len = len(fallback_result.content)
            len_ratio = min(p_len, f_len) / max(p_len, f_len) if max(p_len, f_len) > 0 else 1.0

            return nums_consistent and len_ratio > 0.3, {
                "primary_model": primary_name,
                "fallback_model": fallback.name,
                "primary_numbers": sorted(p_nums),
                "fallback_numbers": sorted(f_nums),
                "numbers_consistent": nums_consistent,
                "length_ratio": round(len_ratio, 2),
                "primary_length": p_len,
                "fallback_length": f_len,
            }
        except Exception as e:
            return None, {"error": str(e)}

    def _add_cache(self, key: str, result: RobustResult):
        self._cache[key] = result
        self._cache_keys.append(key)
        while len(self._cache_keys) > self._cache_max:
            oldest = self._cache_keys.pop(0)
            self._cache.pop(oldest, None)

    def cache_stats(self) -> dict:
        return {
            "cached_entries": len(self._cache),
            "max_cache": self._cache_max,
        }

    def breaker_states(self) -> dict:
        return {
            "max_failures": self.breaker.max_failures,
            "cooldown_seconds": self.breaker.cooldown,
            "states": {
                name: self.breaker.state(name)
                for name in self.breaker._failures
            },
        }


MODEL_REGISTRY_DICT = {
    "reasoning": {"fallback": "qwen-free"},
    "lightweight": {"fallback": "deepseek-free"},
    "long_context": {"fallback": "qwen-free"},
    "code": {"fallback": "kimi"},
}


_robust: RobustInference | None = None


def get_robust() -> RobustInference:
    global _robust
    if _robust is None:
        _robust = RobustInference()
    return _robust


def reset_robust():
    global _robust
    _robust = None
