import json
import urllib.request

from ..common.retry import RetryHandler
from ..common.errors import AuthError, ServerError, RateLimitError


class HttpClient:
    def __init__(self, timeout_sec: int = 30):
        self.timeout_sec = timeout_sec
        self.retry = RetryHandler()

    def post(self, base_url: str, key: str, body: dict) -> dict:
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        def _do():
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                if resp.status == 401:
                    raise AuthError(base_url)
                if resp.status == 429:
                    raise RateLimitError(base_url)
                if resp.status >= 500:
                    raise ServerError(base_url, resp.status)
                return json.loads(resp.read().decode("utf-8"))

        return self.retry.execute(_do)
