---
name: "personal-data-center"
description: "个人数据处理中心四层架构SDK (SDK/DADS/Frontend/Data)。当用户需要搭建AI数据处理系统、RAG流水线、插件管理或TUI交互界面时使用此技能。"
---

# Personal Data Center - 个人数据处理中心

高度模块化的四层架构系统，专为 OpenCode TUI 环境优化。

## 项目位置

```
{USER_VAULT}\
├── skills/personal-data-center/     # 技能定义
├── PersonalDataCenter/              # 完整代码库（从桌面复制）
└── src/                            # 核心源码
```

## 四层架构

### 1. SDK层 (基础框架颗粒)

**路径**: `sdk/`

| 颗粒模块 | 文件 | 功能 |
|---------|------|------|
| PluginManager | `sdk/plugin_manager.py` | 插件加载/卸载/执行 |
| DualTrackRouter | `sdk/dual_track_router.py` | Personal/Medical双轨路由 |
| AuthManager | `sdk/auth_manager.py` | Casbin权限控制 |
| VectorDB | `sdk/vector_db.py` | LanceDB向量存储 |

**OpenCode TUI 交互钩子**:
```
/sdk list-plugins          # 列出所有插件
/sdk load-plugin <name>    # 加载指定插件
/sdk unload-plugin <name>  # 卸载指定插件
/sdk route-info            # 查看路由配置
/sdk auth-check <sub> <obj> <act>  # 权限检查
```

### 2. DADS层 (RAG核心颗粒)

**路径**: `dads/`

| 颗粒模块 | 文件 | 功能 |
|---------|------|------|
| OctupleReview | `dads/octuple_review.py` | 八重审查机制 |
| ParentChildContract | `dads/parent_child_contract.py` | 契约校验系统 |
| RAGPipeline | `dads/rag_pipeline.py` | RAG检索流水线 |

**八重审查项**:
1. 敏感内容审查
2. 医疗准确性审查
3. 法律法规合规审查
4. 伦理准则审查
5. 数据隐私保护审查
6. 逻辑一致性审查
7. 输出格式规范审查
8. 用户意图匹配审查

**OpenCode TUI 交互钩子**:
```
/dads run-pipeline <query>       # 运行RAG流水线
/dads review-result <result>     # 单步审查
/dads contract-create <type>     # 创建契约
/dads contract-verify <id>       # 验证契约
/dads review-step <step>         # 单步调试审查
```

### 3. 前端层 (交互颗粒)

**路径**: `frontend/`

| 颗粒组件 | 功能 |
|---------|------|
| CrClCalculator | Cockcroft-Gault公式计算 |
| ParasiteNotes | 寄生笔记系统 |
| AnchorSystem | 锚点导航系统 |

**OpenCode TUI 交互钩子**:
```
/ui show crcl              # 显示CrCl计算器
/ui show notes             # 显示寄生笔记
/ui show anchors           # 显示锚点系统
/ui hide <component>       # 隐藏指定组件
/ui reload <component>     # 重载组件数据
```

### 4. 数据层 (存储颗粒)

**路径**: `data/`

| 颗粒模块 | 文件 | 功能 |
|---------|------|------|
| DataLoader | `data/data_loader.py` | 数据加载 + is_loaded阻塞 |
| EncodingFixer | `data/encoding_fixer.py` | DB-01/DB-02编码修复 |

**OpenCode TUI 交互钩子**:
```
/data load <path>          # 加载数据文件
/data status               # 查询加载状态
/data wait                 # 阻塞等待is_loaded
/data fix-encoding <file>   # 修复编码问题
```

## 快速启动

```bash
# 安装依赖
pip install -r requirements.txt

# 启动后端API
python -m uvicorn sdk.app:app --host 127.0.0.1 --port 8000

# 启动前端
streamlit run frontend/app.py
```

## API端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/auth/enforce` | POST | 权限检查 |
| `/vector/search` | POST | 向量检索 |
| `/plugins/list` | GET | 插件列表 |
| `/plugins/execute` | POST | 执行插件 |
| `/track/{track}/route/{path}` | POST | 双轨路由 |

## 核心接口示例

```python
# SDK层 - 插件管理
from sdk.plugin_manager import PluginManager
pm = PluginManager()
pm.load_plugin("dads.rag_pipeline")
pm.execute_plugin("rag_pipeline", {"query": "..."})

# DADS层 - 八重审查
from dads.octuple_review import OctupleReview
review = OctupleReview()
results = review.review_sync(query, context, response)
summary = review.get_summary(results)

# DADS层 - 契约校验
from dads.parent_child_contract import ParentChildContract, ContractType
contract_mgr = ParentChildContract()
contract = contract_mgr.create_contract("parent1", "child1", ContractType.RETRIEVAL)
result = contract_mgr.verify_contract(contract.contract_id)

# 数据层 - 阻塞加载
from data.data_loader import DataLoader
loader = DataLoader()
loader.load_from_json("data.json")
loader.is_loaded(timeout=30)  # 阻塞等待
```

## 目录结构

```
PersonalDataCenter/
├── sdk/                    # SDK层
│   ├── app.py             # FastAPI入口
│   ├── auth_manager.py    # Casbin权限
│   ├── vector_db.py       # LanceDB封装
│   ├── plugin_manager.py  # 插件管理器
│   └── dual_track_router.py # 双轨路由
├── dads/                   # DADS层
│   ├── rag_pipeline.py    # RAG流水线
│   ├── octuple_review.py  # 八重审查
│   └── parent_child_contract.py # 契约校验
├── frontend/               # 前端层
│   └── app.py            # Streamlit界面
├── data/                  # 数据层
│   ├── data_loader.py    # 数据加载器
│   └── encoding_fixer.py # 编码修复
├── configs/               # 配置文件
├── docs/                  # 文档
├── requirements.txt
└── start.py
```

## OpenCode TUI 命令规范

所有命令遵循统一格式：`/<layer> <action> [params]`

- `/sdk` - SDK层操作
- `/dads` - DADS层操作
- `/ui` - 前端层操作
- `/data` - 数据层操作

使用 `help` 或 `?` 获取详细帮助。