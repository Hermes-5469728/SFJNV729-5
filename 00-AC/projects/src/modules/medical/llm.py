"""AC Medical Module LLM Adapter - 3层LLM降级策略
迁移自: core/dads_llm.py
本地优先 · 降级策略 · 零幻觉"""
import os, json, time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

class LLMProvider(Enum):
    OLLAMA = "ollama"
    DASHSCOPE = "dashscope"
    DEEPSEEK = "deepseek"

@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    latency_ms: int
    cached: bool = False
    error: Optional[str] = None

class LLMSwitcher:
    OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    DASHSCOPE_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
    DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

    PROVIDER_ORDER = ["ollama", "dashscope", "deepseek"]
    MODEL_MAP = {
        "ollama": os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"),
        "dashscope": os.environ.get("DASHSCOPE_MODEL", "qwen-turbo"),
        "deepseek": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
    }

    def __init__(self):
        self.cache: Dict[str, LLMResponse] = {}
        self.stats = {"total": 0, "cache_hits": 0, "errors": 0}

    def generate(self, prompt: str, system: Optional[str] = None, max_retries: int = 2) -> LLMResponse:
        cache_key = f"{system or ''}:{prompt[:500]}"
        if cache_key in self.cache:
            self.stats["cache_hits"] += 1
            cached = self.cache[cache_key]
            cached.cached = True
            return cached

        self.stats["total"] += 1
        last_error = None

        for provider in self.PROVIDER_ORDER:
            for attempt in range(max_retries):
                try:
                    t0 = time.time()
                    if provider == "ollama":
                        result = self._call_ollama(prompt, system)
                    elif provider == "dashscope":
                        result = self._call_dashscope(prompt, system)
                    elif provider == "deepseek":
                        result = self._call_deepseek(prompt, system)
                    latency = int((time.time() - t0) * 1000)
                    response = LLMResponse(
                        content=result,
                        provider=provider,
                        model=self.MODEL_MAP[provider],
                        latency_ms=latency,
                    )
                    self.cache[cache_key] = response
                    return response
                except Exception as e:
                    last_error = str(e)
                    continue

        self.stats["errors"] += 1
        return LLMResponse(
            content="[LLM UNAVAILABLE] All providers failed. Using local rules only.",
            provider="none",
            model="none",
            latency_ms=0,
            error=last_error,
        )

    def _call_ollama(self, prompt: str, system: Optional[str]) -> str:
        import requests
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = requests.post(
            f"{self.OLLAMA_HOST}/api/chat",
            json={"model": self.MODEL_MAP["ollama"], "messages": messages, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def _call_dashscope(self, prompt: str, system: Optional[str]) -> str:
        import requests
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            headers={"Authorization": f"Bearer {self.DASHSCOPE_KEY}", "Content-Type": "application/json"},
            json={"model": self.MODEL_MAP["dashscope"], "input": {"messages": messages}},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["output"]["text"]

    def _call_deepseek(self, prompt: str, system: Optional[str]) -> str:
        import requests
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.DEEPSEEK_KEY}", "Content-Type": "application/json"},
            json={"model": self.MODEL_MAP["deepseek"], "messages": messages},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def stats_summary(self) -> Dict[str, Any]:
        return {
            **self.stats,
            "cache_size": len(self.cache),
            "cache_hit_rate": f"{self.stats['cache_hits'] / max(self.stats['total'], 1):.1%}",
        }
