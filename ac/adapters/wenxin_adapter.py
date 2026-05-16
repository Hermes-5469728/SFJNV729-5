"""文心一言适配器 · 千帆 API 通道 · 不可信外部信源
鉴权: WENXIN_API_KEY + WENXIN_SECRET_KEY (OAuth2 client_credentials)
规则: 生成代码需经 ArchGuard 扫描后方可合入
"""

import os
import time
import urllib.request
import urllib.error
import json

from .base import ModelAdapter, ModelResponse

ENV_API_KEY = "WENXIN_API_KEY"
ENV_SECRET_KEY = "WENXIN_SECRET_KEY"
OAUTH_URL = "https://aip.baidubce.com/oauth/2.0/token"
CHAT_URL = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions"
DEFAULT_MODEL = "ernie-4.0-8k"
DEFAULT_TIMEOUT = 60


class WenxinAdapter(ModelAdapter):
    def __init__(self):
        self._token: str | None = None
        self._token_expire: float = 0.0

    @property
    def name(self) -> str:
        return "wenxin"

    @property
    def model_id(self) -> str:
        return DEFAULT_MODEL

    def _get_credentials(self) -> tuple[str | None, str | None]:
        api_key = os.environ.get(ENV_API_KEY)
        secret_key = os.environ.get(ENV_SECRET_KEY)
        if not api_key:
            api_key = os.environ.get("AC_WENXIN_KEY")
        if not secret_key:
            secret_key = os.environ.get("AC_WENXIN_SECRET")
        return api_key, secret_key

    def is_available(self) -> bool:
        api_key, secret_key = self._get_credentials()
        return api_key is not None and secret_key is not None

    def _fetch_token(self) -> str | None:
        api_key, secret_key = self._get_credentials()
        if not api_key or not secret_key:
            return None

        now = time.time()
        if self._token and now < self._token_expire:
            return self._token

        params = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": secret_key,
        })
        url = f"{OAUTH_URL}?{params}"

        try:
            resp = urllib.request.urlopen(url, timeout=15)
            data = json.loads(resp.read())
            self._token = data.get("access_token")
            expires = data.get("expires_in", 86400)
            self._token_expire = now + expires - 60
            return self._token
        except Exception:
            return None

    def health_check(self) -> bool:
        token = self._fetch_token()
        if not token:
            return False
        return self._timed_health_check()

    def call(self, prompt: str, system: str | None = None,
             temperature: float = 0.7, max_tokens: int = 2048,
             timeout: int = DEFAULT_TIMEOUT) -> ModelResponse:
        api_key, secret_key = self._get_credentials()
        if not api_key or not secret_key:
            return ModelResponse(
                model_name=self.name, content="",
                error=f"{ENV_API_KEY} 或 {ENV_SECRET_KEY} 未设置",
            )

        token = self._fetch_token()
        if not token:
            return ModelResponse(
                model_name=self.name, content="",
                error="无法获取文心 access_token（检查 API Key / Secret Key 是否正确）",
            )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "disable_search": True,
        }

        body = json.dumps(payload).encode("utf-8")
        url = f"{CHAT_URL}?access_token={token}"
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json"},
        )

        start = time.time()
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            raw = json.loads(resp.read())
            elapsed = (time.time() - start) * 1000

            content = raw.get("result", "")
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
        return False
