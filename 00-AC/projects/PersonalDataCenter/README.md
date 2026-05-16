# Personal Data Center - 个人数据处理中心

高度模块化的四层架构系统，专为 OpenCode TUI 环境优化。

## 项目位置

```
{USER_VAULT}\PersonalDataCenter\
```

## 四层架构

### 1. SDK层 (基础框架颗粒)

| 颗粒模块 | 文件 | 功能 |
|---------|------|------|
| PluginManager | `sdk/plugin_manager.py` | 插件加载/卸载/执行 |
| DualTrackRouter | `sdk/dual_track_router.py` | Personal/Medical双轨路由 |
| AuthManager | `sdk/auth_manager.py` | Casbin权限控制 |
| VectorDB | `sdk/vector_db.py` | LanceDB向量存储 |

### 2. DADS层 (RAG核心颗粒)

| 颗粒模块 | 文件 | 功能 |
|---------|------|------|
| OctupleReview | `dads/octuple_review.py` | 八重审查机制 |
| ParentChildContract | `dads/parent_child_contract.py` | 契约校验系统 |
| RAGPipeline | `dads/rag_pipeline.py` | RAG检索流水线 |

### 3. 前端层 (交互颗粒)

| 颗粒组件 | 功能 |
|---------|------|
| CrClCalculator | Cockcroft-Gault公式计算 |
| ParasiteNotes | 寄生笔记系统 |
| AnchorSystem | 锚点导航系统 |

### 4. 数据层 (存储颗粒)

| 颗粒模块 | 文件 | 功能 |
|---------|------|------|
| DataLoader | `data/data_loader.py` | 数据加载 + is_loaded阻塞 |
| EncodingFixer | `data/encoding_fixer.py` | DB-01/DB-02编码修复 |

## OpenCode TUI 命令规范

| 命令 | 描述 |
|------|------|
| `/sdk list-plugins` | 列出所有插件 |
| `/sdk load-plugin <name>` | 加载指定插件 |
| `/sdk unload-plugin <name>` | 卸载指定插件 |
| `/sdk route-info` | 查看路由配置 |
| `/sdk auth-check <sub> <obj> <act>` | 权限检查 |
| `/dads run-pipeline <query>` | 运行RAG流水线 |
| `/dads review-result <result>` | 单步审查 |
| `/dads contract-create <type>` | 创建契约 |
| `/dads contract-verify <id>` | 验证契约 |
| `/ui show <component>` | 显示组件 |
| `/ui hide <component>` | 隐藏组件 |
| `/data load <path>` | 加载数据文件 |
| `/data status` | 查询加载状态 |
| `/data wait` | 阻塞等待is_loaded |

## 快速启动

```bash
cd {USER_VAULT}\PersonalDataCenter

pip install -r requirements.txt

python -m uvicorn sdk.app:app --host 127.0.0.1 --port 8000

streamlit run frontend/app.py
```

## API端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/sdk/status` | GET | SDK状态 |
| `/auth/enforce` | POST | 权限检查 |
| `/vector/search` | POST | 向量检索 |
| `/plugins/list` | GET | 插件列表 |
| `/plugins/execute` | POST | 执行插件 |
| `/routes/list` | GET | 路由列表 |
| `/track/{track}/route/{path}` | POST | 双轨路由 |

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
├── opencode_tui.py       # OpenCode TUI接口
├── requirements.txt
└── README.md
```