"""workflow/stream_a_dispatch.py
流 A · 单轮调度流
快速路径：CLT → L0 → Dispatch → Expert Match → Governance → CLT
适用于简单查询，同步阻塞，单次往返完成。
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ac.core import dispatch as _dispatch
from ac.governance import pipeline as gov_pipeline
from ac.guard import sanitize_text


def stream_a_process(query: str, session_id: str, no_gov: bool = False) -> dict:
    """单轮调度流入口"""
    clean = sanitize_text(query)

    result = _dispatch(clean)

    if not no_gov and result.get("status") == "matched":
        import json
        output = json.dumps(result, ensure_ascii=False)
        ctx = {"command": "dispatch", "query": clean, "session_id": session_id}
        gov_result = gov_pipeline(output, ctx)
        result["governance"] = gov_result

    result["stream"] = "A"
    result["session_id"] = session_id
    return result
