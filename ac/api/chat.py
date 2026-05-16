"""多AI对话路由 · 可插拔适配器层"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    model: str = "deepseek-chat"


class ChatResponse(BaseModel):
    reply: str
    model: str
    latency_ms: float = 0
    tokens_in: int = 0
    tokens_out: int = 0


def _call_adapter(adapter, prompt: str) -> ChatResponse:
    resp = adapter.call(prompt)
    if resp.error:
        raise HTTPException(status_code=502, detail=resp.error)
    return ChatResponse(
        reply=resp.content,
        model=adapter.name,
        latency_ms=resp.latency_ms or 0,
        tokens_in=resp.tokens_in or 0,
        tokens_out=resp.tokens_out or 0,
    )


@router.post("/deepseek", response_model=ChatResponse)
def chat_deepseek(req: ChatRequest):
    from ac.adapters.deepseek_free import DeepSeekFreeAdapter
    return _call_adapter(DeepSeekFreeAdapter(), req.message)


@router.post("/qwen", response_model=ChatResponse)
def chat_qwen(req: ChatRequest):
    from ac.adapters.qwen_free import QwenFreeAdapter
    return _call_adapter(QwenFreeAdapter(), req.message)


@router.post("/doubao", response_model=ChatResponse)
def chat_doubao(req: ChatRequest):
    from ac.adapters.doubao import DoubaoAdapter
    return _call_adapter(DoubaoAdapter(), req.message)


@router.post("/kimi", response_model=ChatResponse)
def chat_kimi(req: ChatRequest):
    from ac.adapters.kimi import KimiAdapter
    return _call_adapter(KimiAdapter(), req.message)


@router.post("/yuanbao", response_model=ChatResponse)
def chat_yuanbao(req: ChatRequest):
    from ac.adapters.yuanbao_crawler import YuanbaoAdapter
    adapter = YuanbaoAdapter()
    reply = adapter.chat(req.message)
    return ChatResponse(reply=reply, model="yuanbao-lite")
