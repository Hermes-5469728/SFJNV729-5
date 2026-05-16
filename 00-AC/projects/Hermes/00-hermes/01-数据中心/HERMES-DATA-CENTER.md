# 通用数据中心 (Hermes Data Center) 产品架构

## 定位

整个 DADS 生态的统一数据底座。**1+N 轨道**中作为 `shared/hermes/` 连接器被各插件调用；**独立产品轨道**中作为独立部署的数据服务。

---

## 一、1+N 轨道 — 嵌入式连接器

### 代码位置
```
AgentHub/
├── shared/hermes/          ← 数据中心连接器
│   ├── __init__.py
│   ├── client.py           # HermesClient (read/write 接口)
│   └── schema.py           # UserProfile / MedicalRecord 数据类
├── ac-core/                ← 平台底座 (通过 connect_hermes() 接入)
├── dads-medical/           ← 医疗插件 (调用 HermesClient)
└── dads-personal/          ← 个人插件 (调用 HermesClient)
```

### 调用链
```
[dads-medical] ──→ query_medical_knowledge() ──→ HermesClient.read_data()
[dads-personal] ──→ query_protection_rules()  ──→ HermesClient.read_data()
[ac-core]        ──→ connect_hermes(client)    ──→ HermesClient.query()
```

### 核心类

| 组件 | 文件 | 职责 |
|---|---|---|
| `HermesClient` | `client.py` | 读写接口 (当前 print 模拟，预留真实 API) |
| `UserProfile` | `schema.py` | 用户画像 (年龄/病史) |
| `MedicalRecord` | `schema.py` | 病历记录 (诊断/处方/时间戳) |

---

## 二、独立产品轨道 — 独立数据服务

### 架构
```
┌─────────────────────────────────────────┐
│          Hermes Data Center             │
├─────────────┬─────────────┬─────────────┤
│ 数据仓库    │ 同步服务    │ 数据 API    │
│ (DC1)       │ (DC2)       │ (DC3)       │
├─────────────┴─────────────┴─────────────┤
│       独立产品按需接入 DC3               │
│   AC ←→ DADS医疗 ←→ DADS个人            │
└─────────────────────────────────────────┘
```

### 独立部署时扩展的目录
```
data/
├── models/          # 数据模型定义
├── schemas/         # JSON Schema 校验
├── migrations/      # 数据库迁移脚本
└── seed/            # 初始种子数据
```

---

## 三、当前数据资产

| 知识库 | 位置 | 条目数 | 状态 |
|---|---|---|---|
| 医学疾病 KB | `dads-medical/knowledge_base.py` | 10 种 | 已交付 |
| 三明医改防护规则 KB | `dads-personal/protection_rules.py` | 8 条 | 已交付 |
| 用户画像 Schema | `shared/hermes/schema.py` | 2 个 dataclass | 已交付 |

---

*文档版本: v1.0 | 创建时间: 2026-05-11*
