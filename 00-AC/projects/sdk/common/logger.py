import json
import logging
import time
from datetime import datetime


class SdkLogger:
    def __init__(self, name: str = "hermes-ac-sdk"):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.INFO)
        if not self._logger.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(h)

    def log_call(self, channel: str, method: str, latency_ms: int,
                 tokens: int = 0, retry: int = 0, error: str = ""):
        entry = {
            "ts": datetime.now().isoformat(),
            "channel": channel,
            "method": method,
            "latency_ms": latency_ms,
            "tokens": tokens,
            "retry": retry,
            "error": error,
        }
        self._logger.info(json.dumps(entry, ensure_ascii=False))
