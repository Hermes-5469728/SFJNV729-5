***

title: "AC Platform 完整架构图"
date: 2026-05-11
tags: \[architecture, system-design]
category: 架构设计
--------------

# 🏗️ AC Platform 完整架构图

## 一、系统总览

```mermaid
flowchart TB
    subgraph 用户层
        A[用户界面] --> B[API Gateway]
    end
    
    subgraph 双AI工程流
        C[Opencode执行器]
        D[Trae架构师]
        E[Hermes知识库]
    end
    
    subgraph 核心平台
        F[路由调度器]
        G[认证中心]
        H[配置管理]
        I[防御管道]
    end
    
    subgraph 模块层
        J[医疗模块]
        K[AC决策模块]
        L[个人助手模块]
    end
    
    subgraph 数据层
        M[(主数据库)]
        N[(备用数据库)]
        O[向量存储]
        P[文件存储]
    end
    
    subgraph 外部服务
        Q[LLM服务]
        R[Ollama本地]
        S[云API]
    end
    
    subgraph 运维层
        T[备份系统]
        U[监控告警]
        V[日志系统]
    end
    
    B --> C
    B --> D
    C --> E
    D --> E
    C --> F
    D --> F
    F --> G
    F --> H
    F --> I
    I --> J
    I --> K
    I --> L
    J --> M
    K --> M
    L --> M
    M -.-> N
    J --> O
    C --> Q
    D --> Q
    C --> R
    D --> R
    T --> M
    T --> E
    U --> F
    V --> F
```

## 二、核心平台架构

### 2.1 路由调度器

```mermaid
flowchart TD
    A[请求进入] --> B{路径匹配}
    B -->|API路由| C[确定性路由]
    B -->|工具调用| D[启发式路由]
    
    C --> E[路径参数解析]
    E --> F[权限检查]
    F --> G[模块分发]
    G --> H[医疗模块]
    G --> I[AC模块]
    G --> J[个人模块]
    
    D --> K[工具注册表查询]
    K --> L{工具存在?}
    L -->|是| M[参数验证]
    L -->|否| N[返回错误]
    M --> O[执行工具]
    O --> P[结果封装]
    
    H --> Q[返回响应]
    I --> Q
    J --> Q
    P --> Q
    N --> Q
```

### 2.2 认证中心

| 认证方式    | 适用场景  | 实现方式           |
| ------- | ----- | -------------- |
| API Key | 服务间调用 | Header Token   |
| OAuth2  | 用户登录  | 授权码流程          |
| 会话认证    | Web界面 | Cookie/Session |

### 2.3 防御管道

```mermaid
flowchart LR
    A[输入请求] --> B[输入验证]
    B --> C[恶意内容检测]
    C --> D[权限校验]
    D --> E[速率限制]
    E --> F[内容审计]
    F --> G[输出过滤]
    G --> H[正常处理]
    
    B -->|验证失败| I[拒绝请求]
    C -->|检测到恶意| I
    D -->|无权限| I
    E -->|超限| J[限流响应]
    F -->|内容违规| I
```

## 三、医疗模块架构

### 3.1 模块内部结构

```mermaid
flowchart TB
    subgraph 医疗模块
        A[API层]
        B[业务逻辑层]
        C[数据访问层]
        D[评分引擎]
        E[防御适配器]
        F[LLM集成]
        G[向量检索]
    end
    
    A --> B
    B --> C
    B --> D
    B --> E
    B --> F
    B --> G
    C --> H[(医疗数据库)]
    G --> I[向量存储]
    F --> J[外部LLM]
```

### 3.2 临床评分引擎

| 评分模型         | 用途     | 参数数量 |
| ------------ | ------ | ---- |
| CHA₂DS₂-VASc | 房颤卒中风险 | 7    |
| HAS-BLED     | 出血风险   | 6    |
| Wells DVT    | DVT概率  | 7    |
| Wells PE     | PE概率   | 8    |
| CURB-65      | 肺炎严重程度 | 5    |

## 四、双AI协作流程

### 4.1 意图契约机制

```mermaid
flowchart TD
    A[用户想法] --> B[Opencode意图识别]
    B --> C{复杂度评估}
    C -->|低| D[直接执行]
    C -->|中/高| E[生成意图契约]
    E --> F[存入Inbox]
    F --> G[触发Trae分析]
    G --> H[契约验证]
    H -->|通过| I[执行实现]
    H -->|不通过| J[回询澄清]
    J --> B
    D --> K[结果反馈]
    I --> K
    K --> L[更新知识库]
```

### 4.2 契约数据结构

| 字段                   | 类型   | 必填 | 说明              |
| -------------------- | ---- | -- | --------------- |
| task\_id             | str  | ✅  | 唯一标识            |
| title                | str  | ✅  | 任务标题            |
| complexity           | enum | ✅  | low/medium/high |
| deadline             | date | ❌  | 截止日期            |
| requirements         | str  | ✅  | 需求描述            |
| acceptance\_criteria | list | ✅  | 验收标准            |
| risks                | list | ❌  | 风险评估            |

## 五、数据层架构

### 5.1 数据库隔离策略

```mermaid
flowchart TB
    subgraph 主数据库
        A[(med_*)]
        B[(ac_*)]
        C[(user_*)]
        D[(core_*)]
    end
    
    A --> E[医疗模块]
    B --> F[AC模块]
    C --> G[用户管理]
    D --> H[核心服务]
```

### 5.2 备份与冗余

```mermaid
flowchart TD
    A[主数据库] --> B[定时备份]
    A --> C[实时同步]
    B --> D[本地备份]
    B --> E[云端备份]
    C --> F[备用数据库]
    D --> G[保留7天]
    E --> H[无限保留]
```

## 六、工具链架构

### 6.1 自动化流程

```mermaid
flowchart TD
    A[代码提交] --> B[Pre-commit Hook]
    B --> C[Ruff格式化]
    C --> D[Mypy类型检查]
    D --> E[文档生成]
    E --> F[契约验证]
    F --> G[提交成功]
    
    C -->|失败| H[修正代码]
    D -->|失败| H
    E -->|失败| I[更新文档]
    F -->|失败| J[修正契约]
    H --> B
    I --> B
    J --> B
```

### 6.2 工具配置矩阵

| 工具         | 配置文件                    | 用途       | 触发时机       |
| ---------- | ----------------------- | -------- | ---------- |
| Ruff       | ruff.toml               | 格式化+Lint | pre-commit |
| Mypy       | mypy.ini                | 类型检查     | pre-commit |
| Pytest     | pyproject.toml          | 单元测试     | make test  |
| Pre-commit | .pre-commit-config.yaml | 钩子管理     | git commit |

## 七、目录结构

```
TRAE/
├── src/                          # 源代码
│   ├── core/                     # 核心平台
│   │   ├── config.py             # 配置管理
│   │   ├── database.py           # 数据库连接
│   │   ├── auth.py               # 认证中心
│   │   ├── router.py             # 路由调度
│   │   └── gaia_defense.py       # 防御管道
│   ├── modules/                  # 业务模块
│   │   ├── medical/              # 医疗模块
│   │   ├── ac/                   # AC决策模块
│   │   └── personal/             # 个人助手模块
│   ├── shared/                   # 共享组件
│   │   ├── dependencies.py       # 依赖注入
│   │   └── exceptions.py         # 异常体系
│   └── utils/                    # 工具函数
│       ├── date_utils.py         # 日期工具
│       ├── intent_contract.py    # 意图契约
│       ├── doc_generator.py      # 文档生成
│       └── backup_manager.py     # 备份管理
├── Hermes/                       # 知识库
│   ├── Templates/                # 模板
│   ├── Inbox/                    # 待处理
│   └── Docs/                     # 生成文档
├── tests/                        # 测试用例
├── backups/                      # 备份文件
├── pyproject.toml                # 项目配置
├── Makefile                      # 命令脚本
└── .pre-commit-config.yaml       # 钩子配置
```

## 八、关键设计决策

> \[!IMPORTANT] 核心原则
>
> 1. **模块化**: 1+N架构，核心平台+业务模块分离
> 2. **防御性**: 多层防御管道，零信任架构
> 3. **可追溯**: 意图契约机制，完整需求链路
> 4. **自动化**: CI/CD全流程，文档即代码

> \[!WARNING] 风险提示
>
> - 单点故障: 主数据库需要冗余备份
> - 依赖外部服务: LLM服务需要降级策略
> - 数据一致性: 多模块共享数据需要事务管理

## 九、扩展规划

| 阶段      | 目标     | 时间      |
| ------- | ------ | ------- |
| Phase 1 | 核心平台稳定 | Q2 2026 |
| Phase 2 | 模块扩展   | Q3 2026 |
| Phase 3 | 高可用架构  | Q4 2026 |
| Phase 4 | 多云部署   | Q1 2027 |

