import sys, io, sqlite3, uuid, json, os
from datetime import datetime, timezone
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 获取项目根目录（tools/ 的父目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

db_path = str(PROJECT_ROOT / "ac" / "ac_platform.db")
db = sqlite3.connect(db_path)
cur = db.cursor()

title = '架构复盘 · 2026-05-13 ac_server.py 假端点实锤'
content = (
    '2026-05-13 架构复盘发现 P1-3（SubAgent 隔离）的实锤证据。\n'
    'ac_server.py _execute_dispatch 路由完全不调用 AC core.dispatch()。\n\n'
    '三个假端点：\n'
    '1. _execute_knowledge_query()  \u2192 f-string 拼凑，不查数据库\n'
    '2. _execute_reasoning()  \u2192 f-string 拼凑，无真实推理\n'
    '3. _execute_code_generation()  \u2192 SubAgent，不走 AC 调度\n\n'
    '行 385 注释声称\u201c已切除\u201d但代码未改。\n'
    '影响：:8001 上跑的 AC Server 是假 AC，所有 dispatch 请求被拦截或伪造。\n'
    '修复方向：_execute_dispatch 应调用 core.dispatch() 走真实 E/D/S/Q 流水线。'
)

tags = json.dumps(['P1-3', 'SubAgent隔离', '假端点', 'ac_server', '架构复盘'], ensure_ascii=False)

from ac.validator import validate_truth
vr = validate_truth(title, content)

fid = str(uuid.uuid4())
now = datetime.now(timezone.utc).isoformat()
cur.execute(
    'INSERT INTO ac_truth (truth_id, title, category, source, content, truth_count, verified, tags, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
    (fid, title, 'architecture', 'AC dispatch', content, 1,
     1 if vr.passed and vr.level == 'L5' else 0,
     f'{tags} [v{vr.level}:{vr.score:.1f}]', now)
)
db.commit()
db.close()

print('title: ' + title)
print('level: ' + vr.level + ' | score: ' + str(vr.score) + ' | passed: ' + str(vr.passed))
print('truth_id: ' + fid)
