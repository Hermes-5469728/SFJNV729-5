# AC 决策中心 (AC Platform) 产品架构

## 定位

整个 1+N 生态的"大脑"——统一的任务调度、记忆管理、决策路由中心。

---

## 一、1+N 轨道 — 平台底座

### 代码位置
```
AgentHub/ac-core/
├── __init__.py      # 统一导出
├── agent.py         # BaseAgent — think() / act() / connect_hermes()
├── planner.py       # TaskPlanner — decompose() 任务拆解
└── memory.py        # ShortTermMemory — 容量10 对话记忆
```

### 类层次
```
BaseAgent                     ← 平台基类
├── MedicalDiagnosis          ← dads-medical (继承, 重写 think)
│   └── + _analyze()         ← 知识库匹配诊断
└── DoctorRiskAgent          ← dads-personal (继承, 重写 think)
    └── + assess()           ← 防护规则匹配评估
```

### 核心服务矩阵

| 服务 | 类 | 方法 | 消费者 |
|---|---|---|---|
| 决策引擎 | `BaseAgent` | `think()` / `act()` | 所有插件 |
| 任务拆解 | `TaskPlanner` | `decompose(task)` → 3步骤 | 所有插件 |
| 短期记忆 | `ShortTermMemory` | `add()` / `recent()` / `clear()` | 所有插件 |
| Hermes 连接 | `BaseAgent` | `connect_hermes(client)` | 数据中心 |

### 插件接入方式
```python
from ac_core import BaseAgent      # 继承基类

class MyPlugin(BaseAgent):         # 重写 think()
    def think(self, input):        # 自动获得 planner + memory + hermes
        ...
```

---

## 二、独立产品轨道 — AC 决策中心 (独立版)

### 架构
```
┌─────────────────────────────────────────┐
│            AC 决策中心                   │
├─────────────┬─────────────┬─────────────┤
│ 信息处理    │ 决策算法    │ 个人发展    │
│ 引擎        │ 模块        │ 辅助        │
├─────────────┴─────────────┴─────────────┤
│          创意工坊 (独立功能)             │
├─────────────────────────────────────────┤
│             通用数据中心                 │
└─────────────────────────────────────────┘
```

### 独立部署时扩展的目录
```
ac-core/
├── engine/           # 信息处理引擎 (独立版增强)
├── algorithms/       # 决策算法集 (独立版增强)
├── workshop/         # 创意工坊模块
├── api/              # REST API 层
└── web/              # Web 前端资源
```

---

## 三、当前状态

| 模块 | 文件 | 行数 | 状态 |
|---|---|---|---|
| BaseAgent | `agent.py` | 33 | 已交付 |
| TaskPlanner | `planner.py` | 7 | 已交付 |
| ShortTermMemory | `memory.py` | 18 | 已交付 |
| AC 决策中心独立版 | — | — | 待开发 |

---

*来源: {USER_HOME}\TRAE\Hermes\00-hermes\01-AC\AC-PLATFORM-ARCHITECTURE.md*
*文档版本: v1.0 | 创建时间: 2026-05-11*
