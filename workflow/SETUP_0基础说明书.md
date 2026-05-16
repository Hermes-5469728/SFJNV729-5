# AC Platform + 双数据流工作流 · 零基础搭建说明书

> 适用人群：从没装过 Python 的小白  
> 目标：在新电脑上完整跑起 AC 调度平台 + 多 CLT 双流工作流

---

## 一、环境准备（约 20 分钟）

### 1.1 安装 Python

1. 打开 https://www.python.org/downloads/
2. 点击黄色 **Download Python 3.11.x**（不要下 3.13，部分库不兼容）
3. 运行安装程序，**务必勾选底部的 `Add Python to PATH`**
4. 一路点 Next 装完
5. 验证：按 `Win+R` → 输入 `cmd` → 回车，在黑窗口输入：
   ```
   python --version
   ```
   看到 `Python 3.11.x` 就对了

### 1.2 安装 Git

1. 打开 https://git-scm.com/downloads
2. 下载 Windows 版，一路默认安装
3. 验证：在 cmd 输入：
   ```
   git --version
   ```
   看到 `git version 2.x` 就对了

### 1.3 下载代码

你有两个选择：

**选项 A：从 GitHub 克隆（推荐）**
```cmd
cd C:\
git clone https://github.com/ac-platform/SFJNV729-5.git AC-Platform
```

**选项 B：从 U 盘/移动硬盘复制**
直接把 `HERMES-DATE` 文件夹复制到新电脑的 `C:\Users\你的用户名\` 下

---

## 二、装依赖包（约 5 分钟）

打开 cmd，逐条执行：

```cmd
pip install pydantic chromadb chardet
```

**如果报错 `Microsoft C++ Build Tools`：**
1. 打开 https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. 下载 `Build Tools` 安装包
3. 运行，勾选 **"C++ build tools"**，安装
4. 重启 cmd，重新执行上面的 pip 命令

**可选（如需用到 LLM 修正功能）：**
```cmd
pip install pandas transformers torch fastapi uvicorn websockets
```

---

## 三、数据库（约 3 分钟）

**`ac_platform.db` 是关键文件**，里面存了 90 条已验证真值、24 个专家、历史调度和治理记录。新电脑上两个办法：

### 方案 A：直接复制现有数据库（推荐）

从旧电脑把 `ac_platform.db` 复制到新电脑的项目根目录：

```
旧电脑: {PROJECT_ROOT}\ac_platform.db
        ↓  复制到 U 盘  ↓
新电脑: C:\Users\你的用户名\HERMES-DATE\HERMES-DATE\ac_platform.db
```

**优点**：所有数据都在（90 条真值、历史记录、专家表），不需要重新迁移。
**注意**：复制后先检查版本号：

```cmd
python -c "import sqlite3; c=sqlite3.connect('ac_platform.db'); print(c.execute('PRAGMA user_version').fetchone()[0])"
```

如果输出 `2` 说明版本匹配，直接用。

### 方案 B：从零重建（旧电脑不在身边时）

#### Step 1 定位到项目目录

```cmd
cd C:\Users\你的用户名\HERMES-DATE\HERMES-DATE
```

#### Step 2 创建数据库并迁移

```cmd
python -m db_migration migrate
```

看到输出：
```
=== Migration Manager ===
Current schema version: 0, target: 2
→ Applying v1: initial_schema... ✅
→ Applying v2: encoding_columns... ✅
Schema is up to date (v2)
```

#### Step 3 导入专家数据

```cmd
python cli.py seed
```

看到：
```
已导入 24 个专家（L=10, T=6, M=2, A=5）
```

#### Step 4 重建真值知识库（关键补充）

`python cli.py seed` **只会导入专家表**，不会恢复 90 条真值记录。

**如果你有旧数据库文件**，用以下命令把真值导出为 JSON：

```cmd
python -c "
import sqlite3, json
c = sqlite3.connect(r'旧电脑路径\ac_platform.db')
rows = c.execute('SELECT title, category, source, content, tags FROM ac_truth').fetchall()
c.close()
with open('truth_export.json','w') as f:
    json.dump(rows, f, ensure_ascii=False)
print(f'导出了 {len(rows)} 条真值')
"
```

然后把 `truth_export.json` 复制到新电脑，导入：

```cmd
python -c "
import sqlite3, json, uuid
from datetime import datetime, timezone
c = sqlite3.connect('ac_platform.db')
with open('truth_export.json') as f:
    rows = json.load(f)
for r in rows:
    c.execute('INSERT INTO ac_truth (truth_id, title, category, source, content, verified, tags, created_at) VALUES (?,?,?,?,?,1,?,?)',
              (str(uuid.uuid4()), r[0], r[1], r[2], r[3], r[4], datetime.now(timezone.utc).isoformat()))
c.commit()
c.close()
print(f'导入了 {len(rows)} 条真值')
"
```

**没有旧数据库**：真值表为空不影响核心功能，只用缺失锚点比对能力。

---

## 四、验证安装（约 1 分钟）

```cmd
python cli.py status
```

正常输出示例：
```json
{
  "system": "AC = (E, D, S, Q)",
  "version": "v2.3",
  "experts": { "A": 5, "L": 10, "M": 2, "T": 6, "total": 23 },
  ...
}
```

试一个调度：
```cmd
python cli.py dispatch "你好"
```

---

## 五、锚点引擎配置（约 3 分钟）

两个文件需要修改路径（因为你的用户名和原电脑不一样）：

### 修改 anchor_engine.py

用记事本打开 `anchor_engine.py`，找到第 7 行：

```python
ANCHOR_PATH = Path("{PROJECT_ROOT}/00-DataCenter/anchor_db.json")
```

把 `36854` 改成**你的电脑用户名**。例如如果你的用户名是 `zhangsan`：

```python
ANCHOR_PATH = Path("C:/Users/zhangsan/HERMES-DATE/HERMES-DATE/00-DataCenter/anchor_db.json")
```

### 修改 eav_extractor.py

同样操作，找到第 7 行附近的路径，改成你的用户名。

**不修改也能用**——只是锚点比对功能会跳过，不影响核心调度和编排功能。

---

## 六、工作流模块说明

项目里已经预装了双流工作流模块，位置在：

```
workflow/
├── __init__.py              # 模块入口
├── stream_router.py         # 路由器（自动选流 A/B）
├── stream_a_dispatch.py     # 流 A · 单轮调度
├── stream_b_orchestrator.py # 流 B · 多轮编排
└── multi_clt_handler.py     # 多 CLT 并发处理器
```

### 快速测试

在项目目录下执行：

```cmd
python -c "from workflow import route; print(route('你好'))"
python -c "from workflow import route; print(route('写一个登录模块'))"
```

第一个会走**流 A**（单轮调度），第二个会走**流 B**（多轮编排）。

### 强制指定流

```cmd
python -c "from workflow import route; print(route('你好', force_stream='B'))"
```

---

## 七、多 CLT 模式（进阶）

如果你需要多个终端同时接入：

```python
import asyncio
from workflow import MultiCLTHandler

handler = MultiCLTHandler(max_workers=2)

async def demo():
    await handler.start()
    # 模拟两个 CLT 同时提交
    s1 = await handler.submit("CLT-1", "分析这段代码")
    s2 = await handler.submit("CLT-2", "数据库表结构设计")
    await asyncio.sleep(5)
    print(handler.get_result(s1))
    print(handler.get_result(s2))
    print(handler.status_summary())
    await handler.stop()

asyncio.run(demo())
```

---

## 八、常见问题

### Q: `pip` 不是内部或外部命令
A: 重新安装 Python，勾选 `Add Python to PATH`

### Q: `ModuleNotFoundError: No module named 'ac'`
A: 确保你在项目目录下执行命令（`cd C:\...\HERMES-DATE\HERMES-DATE`）

### Q: 数据库版本不匹配
A: 删除旧的 `ac_platform.db`，重新执行 `python -m db_migration migrate`

### Q: ChromaDB 安装失败
A: 安装 Microsoft C++ Build Tools（看第二节的报错处理）

### Q: 中文乱码
A: 在 cmd 里执行 `chcp 65001` 切换到 UTF-8

---

## 附：DADS 遗产 · 设计参考

这套 AC Platform 的前身是 **CoPilot DADS**（医疗药物核查系统）。
相关参考文档已整合到：

```
00-AC/docs/references/     ← 8 篇 DADS 架构文档
00-AC/DataCenter/truth_datasets/  ← 医学真值数据集
00-AC/docs/EVOLUTION_DADS_to_AC.md  ← 演进对照表
```

DADS 的母体-子体制度是 AC 1+N 架构的起源，建议新手上手前先看：
1. `00-AC/docs/references/DADS_母体子体制度.md` — 理解为什么这么设计
2. `00-AC/docs/references/DADS_已知不足.md` — 避免 AC 重复踩坑

---

## 九、文件清单

新电脑上最终需要的文件：

```
HERMES-DATE/HERMES-DATE/
├── cli.py                 # 主入口
├── core.py                # 调度核心
├── orchestrator.py        # 编排引擎
├── guard.py               # L0 编码层
├── db.py                  # 数据库操作
├── db_migration.py        # 数据库迁移
├── seed.py                # 专家种子数据
├── anchor_engine.py       # 锚点引擎（需改路径）
├── eav_extractor.py       # EAV 抽取器（需改路径）
├── collaborative_governor.py  # 协同治理
├── case_center.py         # 案例中心
├── validator.py           # 真值验证
├── governance/            # 治理管道目录
├── schemas/               # 数据模型目录
├── qa/                    # QA 测试目录
├── workflow/              # 双流工作流模块 ← 新增
├── 00-AC/                 # 子项目目录
├── ac_platform.db         # 数据库（初始为空）
└── anchor_db.json         # 锚点数据（可选）
```

**总共约 30 个文件，核心依赖 3 个 pip 包，总搭建时间约 30 分钟。**
