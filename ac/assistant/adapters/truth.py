"""Personal Assistant — 真值入库适配器（经过 validate_truth）"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional

def store_truth(
    title: str,
    content: str,
    category: str = "personal_assistant",
    source: str = "assistant",
    tags: str = "",
) -> dict:
    """
    经过 ac.validator.validate_truth → ac.db.save_truth
    写入前强制 L5 验证
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from ac.validator import validate_truth
    from ac.db import get_conn, save_truth
    from ac.core import load_config

    vr = validate_truth(title, content)
    config = load_config()
    conn = get_conn(config)
    result = save_truth(
        conn,
        title=title,
        category=category,
        source=source,
        content=content,
        tags=tags,
    )
    conn.commit()
    conn.close()
    return {
        "truth_id": result.get("rowid", ""),
        "verified": result.get("verified", 0),
        "validation_level": result.get("validation", ""),
        "score": result.get("score", 0),
    }
