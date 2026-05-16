"""DeepSeek 免费 API 适配器 · 环境变量鉴权 · 不走 AC 路由不可裸调"""

import os
import time
import urllib.request
import urllib.error
import json
from dataclasses import dataclass

from .base import ModelAdapter, ModelResponse

ENV_KEY = "DEEPSEEK_FREE_API_KEY"
FALLBACK_KEY = "DEEPSEEK_API_KEY"
API_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_TIMEOUT = 60


class DeepSeekFreeAdapter(ModelAdapter):
    @property
    def name(self) -> str:
        return "deepseek-free"

    @property
    def model_id(self) -> str:
        return "deepseek-chat"

    def _get_key(self) -> str | None:
        key = os.environ.get(ENV_KEY)
        if not key:
            key = os.environ.get(FALLBACK_KEY)
        if not key:
            key = os.environ.get("AC_DEEPSEEK_KEY")
        return key

    def is_available(self) -> bool:
        return self._get_key() is not None

    def health_check(self) -> bool:
        return self._timed_health_check()

    def call(self, prompt: str, system: str | None = None,
             temperature: float = 0.7, max_tokens: int = 4096,
             timeout: int = DEFAULT_TIMEOUT) -> ModelResponse:
        api_key = self._get_key()
        if not api_key:
            return ModelResponse(
                model_name=self.name, content="",
                error=f"{ENV_KEY} 未设置",
            )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            API_URL, data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        start = time.time()
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            raw = json.loads(resp.read())
            elapsed = (time.time() - start) * 1000

            choice = raw.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            usage = raw.get("usage", {})

            return ModelResponse(
                model_name=self.name,
                content=content or "",
                raw=raw,
                latency_ms=round(elapsed, 1),
                tokens_in=usage.get("prompt_tokens", 0),
                tokens_out=usage.get("completion_tokens", 0),
            )

        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:500]
            return ModelResponse(
                model_name=self.name, content="",
                error=f"HTTP {e.code}: {detail}",
                latency_ms=round((time.time() - start) * 1000, 1),
            )
        except Exception as e:
            return ModelResponse(
                model_name=self.name, content="",
                error=str(e),
                latency_ms=round((time.time() - start) * 1000, 1),
            )

    @property
    def is_free_tier(self) -> bool:
        return True
