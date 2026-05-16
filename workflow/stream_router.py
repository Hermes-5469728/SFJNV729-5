"""workflow/stream_router.py
双流路由器 · 自动选择 Stream A 或 Stream B
根据输入复杂度、关键词、历史命中率路由到合适的数据流。
"""

import re, uuid
from datetime import datetime, timezone

from .stream_a_dispatch import stream_a_process
from .stream_b_orchestrator import stream_b_process


# 触发流 B 的关键词（包含任一关键词 → 走编排流）
COMPLEX_TRIGGERS = [
    "然后", "并且", "先", "再", "接着",
    "同时", "分别", "依次", "逐步",
    "写一个", "开发", "实现", "设计一个",
    "分析", "比较", "规划", "生成代码",
]


def _is_complex(query: str) -> bool:
    """判断是否走流 B"""
    if len(query) > 100:
        return True
    for kw in COMPLEX_TRIGGERS:
        if kw in query:
            return True
    return False


def route(
    query: str,
    session_id: str | None = None,
    force_stream: str | None = None,
    no_gov: bool = False,
) -> dict:
    """路由入口：自动选择流 A 或流 B"""
    sid = session_id or str(uuid.uuid4())

    if force_stream == "A":
        return stream_a_process(query, sid, no_gov)
    if force_stream == "B":
        return stream_b_process(query, sid, no_gov=no_gov)

    if _is_complex(query):
        return stream_b_process(query, sid, no_gov=no_gov)
    else:
        return stream_a_process(query, sid, no_gov)
