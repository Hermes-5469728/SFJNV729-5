"""AC-Trae 锚点桥接层。两边读写同一来源。"""
import json
from pathlib import Path

# 唯一锚点库位置（相对于项目根目录）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
ANCHOR_DB_PATH = _PROJECT_ROOT / "00-DataCenter" / "anchor_db.json"


def load_anchors():
    """供 Trae 的 validator.py 调用"""
    if ANCHOR_DB_PATH.exists():
        return json.loads(ANCHOR_DB_PATH.read_text(encoding="utf-8"))
    return []


def sync_from_ac():
    """AC 侧每次入库后调用，保持锚点库最新"""
    import sqlite3
    c = sqlite3.connect(str(Path(__file__).resolve().parent / "ac_platform.db"))
    rows = c.execute(
        "SELECT title, content, tags, source FROM ac_truth WHERE verified=1 ORDER BY rowid"
    ).fetchall()
    c.close()
    anchors = [
        {"topic": t[:80], "verified_truth": ct[:500], "source": s or "ac_truth",
         "confidence": 1.0, "tags": (tg or "").split(",")}
        for t, ct, tg, s in rows
    ]
    ANCHOR_DB_PATH.write_text(json.dumps(anchors, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(anchors)
