import zipfile, xml.etree.ElementTree as ET, sys, io, os, sqlite3, json, uuid
from datetime import datetime, timezone
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 获取项目根目录（tools/ 的父目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
db_path = str(PROJECT_ROOT / "ac" / "ac_platform.db")
db = sqlite3.connect(db_path)
cur = db.cursor()

# 建表
cur.execute('''
    CREATE TABLE IF NOT EXISTS internship_forms (
        form_id TEXT PRIMARY KEY,
        form_type TEXT NOT NULL,
        title TEXT NOT NULL,
        category TEXT DEFAULT 'internship',
        content TEXT NOT NULL,
        fields_json TEXT,
        source_file TEXT,
        created_at TEXT NOT NULL
    )
''')
cur.execute('''
    CREATE TABLE IF NOT EXISTS internship_templates (
        template_id TEXT PRIMARY KEY,
        form_type TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        field_count INTEGER DEFAULT 0,
        fields_json TEXT,
        source_file TEXT,
        created_at TEXT NOT NULL
    )
''')

# 已读数据
forms = [
    {
        "type": "三方协议知情同意书",
        "title": "丙方岗位实习法定监护人（或家长）知情同意书",
        "file": "附件2学生岗位实习三方协议书（家长知情同意书 2024）.docx",
        "content": """学生岗位实习三方协议家长知情同意书。
含9条知情条款：实习性质、单位资质、教学要求、报告制度、保险购买、通讯要求、住宿管理、
医疗机构排休制度、临床实习无报酬声明。一式三份（学校/单位/家长）。""",
        "fields": ["学生姓名", "学院", "专业", "班级", "实习时间", "实习单位", "家长签名", "关系", "电话", "日期"]
    },
    {
        "type": "住宿申请表",
        "title": "学生岗位实习住宿（租住/居家）申请表",
        "file": "附件3医学院实习住宿租住申请表（2024）.docx",
        "content": """实习住宿申请表。
学生填写个人信息、实习信息、家长信息、租住房信息。
含申请原因及承诺条款，需学生签名、家长意见、辅导员意见、医学院意见。""",
        "fields": ["姓名", "性别", "电话", "学号", "专业", "班级", "实习时间", "实习岗位",
                   "实习单位名称", "实习单位地址", "家长姓名", "家长电话", "家庭地址",
                   "租住房地址", "房东姓名及电话", "学生签名", "家长签名", "日期"]
    },
    {
        "type": "租住知情同意书",
        "title": "学生岗位实习申请租住家长知情同意书",
        "file": "附件4实习租住学生家长知情同意书（医学院）.docx",
        "content": """实习租住家长知情同意书。
家长确认同意学生自行租住，承诺督促学生遵守规章制度、
定期检查宿舍安全设施、保持联系。附家长身份证复印件。""",
        "fields": ["学生姓名", "与学生关系及姓名", "单位名称", "家长签名", "联系电话", "日期"]
    },
    {
        "type": "自主实习申请表",
        "title": "学生自主岗位实习申请表",
        "file": "附件5医学院自主实习申请表（2024）.docx",
        "content": """自主实习申请表。
学生因不同意学校安排申请自主实习。含基本信息、实习单位信息（名称/信用代码/等级/地址）、
家长信息。需申请原因及承诺、家长意见、辅导员意见、教研室意见、医学院审核意见。""",
        "fields": ["姓名", "身份证号", "电话", "学号", "专业", "班级", "实习时间",
                   "实习岗位", "实习单位名称", "社会统一信用代码", "单位等级",
                   "地址", "联系人及电话", "家长姓名", "与本人关系", "联系电话",
                   "学生签名", "家长签名", "日期"]
    },
    {
        "type": "自主实习家长知情书",
        "title": "学生自主岗位实习家长知情书",
        "file": "附件6医学院自主实习申请表家长知情附件（2024）.docx",
        "content": """自主实习家长知情书。
家长确认同意学生自主实习，承诺督促学生遵守规章制度、保障安全。
附家长身份证复印件。""",
        "fields": ["学生姓名", "与学生关系及姓名", "单位名称", "家长签名", "联系电话", "日期"]
    }
]

now = datetime.now(timezone.utc).isoformat()
for f in forms:
    fid = str(uuid.uuid4())
    cur.execute(
        "INSERT OR IGNORE INTO internship_forms (form_id, form_type, title, category, content, fields_json, source_file, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (fid, f["type"], f["title"], "internship", f["content"], json.dumps(f["fields"], ensure_ascii=False), f["file"], now)
    )
    tid = str(uuid.uuid4())
    cur.execute(
        "INSERT OR IGNORE INTO internship_templates (template_id, form_type, title, description, field_count, fields_json, source_file, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (tid, f["type"], f["title"], f["content"][:100], len(f["fields"]), json.dumps(f["fields"], ensure_ascii=False), f["file"], now)
    )
    print(f'  [{f["type"]}] {f["title"]} ({len(f["fields"])} fields)')

db.commit()
print(f'\n共入库 {len(forms)} 份表单模板')
db.close()
