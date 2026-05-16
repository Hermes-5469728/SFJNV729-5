"""Personal Assistant — AC dispatch 适配器（经过治理管道）"""
from __future__ import annotations
from typing import Optional


class DispatchAdapter:
    def __init__(self, server_url: str = "http://127.0.0.1:8000"):
        self._url = server_url.rstrip("/")

    def dispatch(self, query: str, session_id: Optional[str] = None, user_id: Optional[str] = None) -> dict:
        """
        经过 AC Server /dispatch 端点
        每个请求经过完整治理（健康检查证实 backend 为 ac.core.dispatch）
        """
        import requests
        payload = {"request": query}
        if session_id:
            payload["session_id"] = session_id
        if user_id:
            payload["user_id"] = user_id
        try:
            r = requests.post(f"{self._url}/dispatch", json=payload, timeout=30)
            data = r.json()
            if data.get("status") == "success":
                d = data["data"]
                return {
                    "status": d.get("status", "completed"),
                    "matched": (d.get("result") or {}).get("matched", []),
                    "governance_passed": d.get("governance_passed", False),
                    "execution_time_ms": d.get("execution_time_ms", 0),
                    "raw": data,
                }
            return {"status": "error", "error": data.get("error", "unknown"), "raw": data}
        except Exception as ex:
            return {"status": "error", "error": str(ex)}
