---
title: "AC Platform 完整架构设计（高颗粒度）"
date: 2026-05-11
tags: [architecture, system-design, high-detail]
category: 架构设计
---

# 🏗️ AC Platform 完整架构设计（高颗粒度）

## 一、系统架构全景图

```mermaid
graph TB
    subgraph 用户层["用户层"]
        A1[Web前端]
        A2[移动端]
        A3[API客户端]
        A4[命令行工具]
    end

    subgraph api_gateway["API Gateway"]
        B1[负载均衡]
        B2[请求路由]
        B3[SSL终止]
        B4[请求日志]
    end

    subgraph dual_ai["双AI工程流"]
        C1[Opencode执行器]
        C2[Trae架构师]
        C3[意图识别引擎]
        C4[任务调度器]
    end

    subgraph hermes["Hermes知识库"]
        D1[知识图谱]
        D2[文档管理]
        D3[意图契约存储]
        D4[版本控制]
    end

    subgraph core_platform["核心平台"]
        E1[路由调度器]
        E2[认证中心]
        E3[配置管理]
        E4[防御管道]
        E5[事件总线]
        E6[缓存层]
    end

    subgraph modules["业务模块"]
        F1[医疗决策模块]
        F2[AC决策模块]
        F3[个人助手模块]
        F4[数据处理模块]
    end

    subgraph data_layer["数据层"]
        G1[(主数据库 SQLite)]
        G2[(备用数据库)]
        G3[向量数据库]
        G4[Redis缓存]
        G5[文件存储]
    end

    subgraph external["外部服务"]
        H1[LLM服务-DashScope]
        H2[LLM服务-DeepSeek]
        H3[Ollama本地]
        H4[医疗知识库API]
    end

    subgraph ops["运维监控"]
        I1[Prometheus监控]
        I2[Grafana看板]
        I3[ELK日志系统]
        I4[自动备份]
        I5[告警系统]
    end
```

---

## 二、核心平台详细设计

### 2.1 路由调度器

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| route_id | str | 路由唯一标识 | `med_drug_search` |
| path | str | API路径 | `/api/v1/medical/drugs` |
| methods | list | HTTP方法 | `["GET", "POST"]` |
| module | str | 所属模块 | `medical` |
| handler | str | 处理函数路径 | `src.modules.medical.api:search_drugs` |
| auth_required | bool | 是否需要认证 | `true` |
| rate_limit | int | 速率限制(次/分钟) | `60` |
| timeout | int | 超时时间(秒) | `30` |

### 2.2 认证中心

| 角色 | 权限范围 | 描述 |
|------|----------|------|
| super_admin | 全部权限 | 系统管理员 |
| admin | 管理权限 | 项目管理员 |
| developer | 开发权限 | 开发人员 |
| user | 用户权限 | 普通用户 |
| guest | 只读权限 | 访客 |

### 2.3 防御管道

| 规则类型 | 配置项 | 默认值 | 说明 |
|----------|--------|--------|------|
| 速率限制 | requests_per_minute | 60 | 每分钟请求数 |
| 输入限制 | max_payload_size | 1MB | 请求体最大大小 |
| 内容过滤 | block_keywords | [] | 屏蔽关键词列表 |
| SQL防护 | enabled | true | 是否启用SQL注入防护 |
| XSS防护 | enabled | true | 是否启用XSS防护 |

---

## 三、核心配置结构

```python
class Settings(BaseModel):
    # 运行模式
    AC_CORE_MODE: bool = True
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # 安全配置
    API_KEY: Optional[str] = None
    SECRET_KEY: str = "default-secret-key"

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./ac_platform.db"

    # LLM配置
    OLLAMA_HOST: str = "http://localhost:11434"
    DASHSCOPE_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None

    # 防御配置
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 60
```

---

## 四、意图契约数据结构

```python
class IntentContract(BaseModel):
    task_id: str           # TASK-YYYYMMDD-XXX
    title: str             # 任务标题
    description: str       # 详细描述
    complexity: str         # low/medium/high
    priority: str          # high/medium/low
    author: str
    assignee: Optional[str] = None
    status: str            # pending/in_progress/review/completed
    requirements: List[str]
    acceptance_criteria: List[AcceptanceCriteria]
    deliverables: List[Deliverable]
```

---

## 五、数据库表结构

| 表名 | 说明 |
|------|------|
| users | 用户表 |
| api_keys | API Key表 |
| roles | 角色表 |
| med_drugs | 药物数据库 |
| med_drug_interactions | 药物交互表 |
| med_patients | 患者表 |
| med_records | 病历表 |
| tasks | 任务表 |
| intent_contracts | 意图契约表 |

---

*来源: {USER_HOME}\TRAE\Hermes\架构设计\AC Platform完整架构设计_高颗粒度.md*
*文档版本: v1.0 | 创建时间: 2026-05-11*
