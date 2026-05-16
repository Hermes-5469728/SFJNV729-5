"""L5 强制标注 · 所有 API 输出强制附加幻觉警告 · src/core/defense_label.py"""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import json

LABEL_ZH = "[本回答绝对含有幻觉成分 · 禁止盲从 · 外部验证前不可采信]"
LABEL_EN = "[This answer absolutely contains hallucination content · Blind trust forbidden · Cannot be trusted before external verification]"


def apply_mandatory_label(text: str) -> str:
    if LABEL_ZH in text or LABEL_EN in text:
        return text
    return f"{text}\n\n{LABEL_ZH}\n{LABEL_EN}"


class MandatoryLabelMiddleware(BaseHTTPMiddleware):
    """FastAPI 中间件: 所有 JSON 响应的 'detail' 或顶层消息字段自动注入 L5 标签"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        try:
            data = json.loads(body)
            data = self._inject_label(data)
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

        return JSONResponse(
            content=json.loads(body),
            status_code=response.status_code,
            headers=dict(response.headers),
        )

    def _inject_label(self, data):
        if isinstance(data, dict):
            if "detail" in data and isinstance(data["detail"], str):
                data["detail"] = apply_mandatory_label(data["detail"])
            if "message" in data and isinstance(data["message"], str):
                data["message"] = apply_mandatory_label(data["message"])
            if "error" in data and isinstance(data["error"], str):
                data["error"] = apply_mandatory_label(data["error"])
            data["_defense"] = "L5"
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    self._inject_label(item)
        return data
