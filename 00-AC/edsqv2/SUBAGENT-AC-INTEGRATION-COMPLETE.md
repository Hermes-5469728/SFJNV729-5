# SubAgent + AC Platform 统一架构 - P0/P1 完成总结

> **基于你的架构评审，修复双头架构冲突，建立 AC 为主调度器、SubAgent 为专家执行器的统一架构**

---

## ✅ 全部完成状态

| 优先级 | 问题 | 解决方案 | 状态 |
|--------|------|----------|------|
| **P0** | SubAgent 和 AC 是双头架构 | UnifiedDispatcher 统一入口 + Option A 集成模式 | ✅ 完成 |
| **P1** | 验证规则不统一 | 职责划分：SubAgent L1-L3 做生成质量，AC G0-G4 做事实验证 | ✅ 完成 |
| **P1** | 持久化分散 | 统一数据库：task 和 governance_events 合并 | ✅ 完成 |

---

## 📂 文件结构

```
HERMES-DATE/
├── unified_dispatcher.py              # 新增：统一调度器（Option A 架构）
├── orchestrator.py                    # 现有：AC 13态状态机
├── governance/
│   └── __init__.py                   # 现有：G3 治理管道（6个 checker）
├── governance_tasks.py               # 现有：P1 任务队列
├── governance_events.py               # 现有：P2 事件存储
└── [SubAgent 相关文件...]
```

---

## 🏗️ 核心架构 - Option A（推荐方案）

```
                    ┌─────────────────────────────────────────────────────┐
                    │              统一入口（UnifiedDispatcher）           │
                    │                                                     │
                    │   所有请求 → dispatch(request) → 领域分类            │
                    └─────────────────────┬───────────────────────────────┘
                                          │
          ┌───────────────────────────────┼───────────────────────────────┐
          │                               │                               │
          ▼                               ▼                               ▼
┌─────────────────┐           ┌─────────────────────┐           ┌─────────────────┐
│ TaskDomain      │           │  TaskDomain         │           │ TaskDomain      │
│ KNOWLEDGE       │           │ REASONING          │           │ CODE_GENERATION │
│ REASONING       │           │ MIXED              │           │ ARCHITECTURE    │
│                 │           │                    │           │ DOCUMENTATION   │
└────────┬────────┘           └──────────┬──────────┘           └────────┬────────┘
         │                                 │                               │
         ▼                                 ▼                               ▼
┌─────────────────┐           ┌─────────────────────┐           ┌─────────────────────┐
│   AC Executor   │           │   AC Executor       │           │  SubAgent Executor  │
│   (自主执行)     │           │   (自主执行)        │           │  (专家执行器)       │
└────────┬────────┘           └──────────┬──────────┘           └────────┬────────┘
         │                                 │                               │
         │                                 │                               │
         │    ┌─────────────────────────────┼───────────────────────────────┤
         │    │                             │                               │
         │    ▼                             ▼                               ▼
         │    │                   ┌─────────────────────────────────────────┤
         │    │                   │         AC G3 治理管道（统一）           │
         │    │                   │   6个 checker：                          │
         │    │                   │   1.Encoding 2.JSON 3.L5 4.Semantic    │
         │    │                   │   5.Security 6.Hallucination           │
         │    │                   └─────────────────────────────────────────┤
         │    │                             │                               │
         │    ▼                             ▼                               ▼
         │    └─────────────────────────────┼───────────────────────────────┘
         │                                  │
         └──────────────────────────────────┴──→ 统一持久化（同一数据库）
                                                    │
                                    ┌───────────────┴───────────────┐
                                    │                               │
                                    ▼                               ▼
                            ┌─────────────┐               ┌─────────────────┐
                            │ unified_    │               │ governance_     │
                            │ tasks       │               │ events         │
                            └─────────────┘               └─────────────────┘
```

---

## 职责划分

| 方面 | SubAgent | AC Platform |
|------|----------|-------------|
| **定位** | 专家执行器 | 主调度器 |
| **职责** | 代码生成/文档创作的质量验证 (L1-L3) | 入口路由/任务编排/全局治理 (G0-G4) |
| **验证内容** | 语法、格式、指令遵循 | 事实性、安全性、架构合规性 |
| **持久化** | 通过 UnifiedDispatcher 写入统一DB | 同左 |

---

## 路由决策

```python
class UnifiedDispatcher:
    def dispatch(self, request: str, context: Dict) -> ExecutionResult:
        domain = self._classify_domain(request, context)

        if domain in [CODE_GENERATION, ARCHITECTURE, DOCUMENTATION]:
            # SubAgent 执行，AC G3 治理
            return self._execute_with_subagent(task)
        else:
            # AC 自主执行 + G3 治理
            return self._execute_with_ac(task)
```

| 请求关键词 | 路由到 |
|-----------|--------|
| 代码/函数/class/def/生成代码 | SubAgent |
| 架构/设计模式/系统设计 | SubAgent |
| 文档/README/markdown | SubAgent |
| 什么是/how to/解释/知识 | AC |
| 分析/推理/比较/评估 | AC |

---

## 统一持久化

```python
class UnifiedPersistence:
    # 治理事件（可关联 task）
    def record_governance_event(self, ..., task_id: Optional[str] = None)

    # Session 摘要（可关联 task）
    def save_session_summary(self, ..., task_id: Optional[str] = None)
```

**同一数据库**：unified_platform.db
- unified_tasks：所有任务的执行记录
- task_execution_trace：执行轨迹
- governance_events：治理事件（关联 task_id）
- session_summaries：会话摘要（关联 task_id）

---

## 📊 测试结果

```
✅ 代码生成任务 → 路由到 SubAgent
✅ 知识查询任务 → 路由到 AC
✅ 架构设计任务 → 路由到 SubAgent
✅ 统一持久化 → task 和 governance_events 在同一数据库
```

---

## 🎯 对标你的评审

| 你指出的问题 | 我的实现 |
|-------------|----------|
| 双头架构冲突 | ✅ UnifiedDispatcher 统一入口，AC 为主调度器 |
| 验证规则不统一 | ✅ 职责划分清晰：L1-L3 vs G0-G4 |
| 持久化分散 | ✅ 统一数据库，task 和 events 关联 |
| 可能输出冲突结果 | ✅ 统一 G3 治理，无冲突 |

---

## 后续优化（你评审中提到的）

| 优化项 | 时机 | 状态 |
|--------|------|------|
| 增加 AWAITING_HUMAN 状态 | 做完当前任务再修 | 待做 |
| 动态模型路由 + circuit breaker | 做完当前任务再修 | 待做 |
| API Gateway 统一入口 | 做完当前任务再修 | 待做 |

---

**完成日期：** 2026-05-14
**状态：** ✅ P0/P1 全部完成！SubAgent 和 AC 从"双头架构"升级为"主从协作架构"

