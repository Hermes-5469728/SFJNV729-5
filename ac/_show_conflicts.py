"""Extract 44 conflict entries for manual classification"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sqlite3
from ac.anchor_engine import get_engine

c = sqlite3.connect(str(Path("{USER_HOME}/ac/ac_platform.db")))
rows = c.execute("SELECT rowid, title, content, verified, tags FROM ac_truth ORDER BY rowid").fetchall()
c.close()

engine = get_engine()
conflicts = []
for rowid, title, content, verified, tags in rows:
    r = engine.detect_conflict(title, content)
    if r["has_conflict"]:
        conflicts.append((rowid, title, content[:200], verified, tags))

print(f"共 {len(conflicts)} 条冲突。请分类：")
print(f"  A = 真冲突 | B = 多义词误报 | C = 否定误触 | D = 锚点存疑")
print(f"=" * 70)
for rowid, title, content, verified, tags in conflicts:
    print(f"\n--- #{rowid} {'[verified=1]' if verified else ''} ---")
    print(f"标题: {title[:60]}")
    print(f"摘要: {content[:120]}")
    print(f"标签: {tags[:60] if tags else ''}")
    print(f"分类: ___")  # user fills this
