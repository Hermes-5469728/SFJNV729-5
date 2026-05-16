# AC Platform 三层架构升级 - P0/P1 完成总结

> **基于你的架构评审，建立 AC Bus（事件总线）+ KnowledgeService（知识服务）+ Central Scheduler（中央调度器）三层架构，一次性覆盖全部7个断点**

---

## ✅ 全部完成状态

| 优先级 | 组件 | 覆盖断点 | 状态 |
|--------|------|---------|------|
| **P0-1** | AC Bus（统一事件总线）| #1 文件绕过G3、#4 auditor未集成 | ✅ 完成 |
| **P0-2** | KnowledgeService（知识服务）| #2 dispatch不查truth、#3 orchestrator不读truth | ✅ 完成 |
| **P1** | Central Scheduler（中央调度器）| #5 Gate缺失、#6 escalate缺失、#7 SubAgent独立 | ✅ 完成 |

---

## 📂 文件结构

```
HERMES-DATE/
├── ac_bus.py                          # 新增：P0-1 统一事件总线
├── unified_dispatcher.py              # 新增：P1 中央调度器
├── knowledge_service_p0.py            # 已有：P0-2 统一知识服务
├── orchestrator.py                   # 现有：AC 13态状态机
├── governance/
│   ├── __init__.py                   # 现有：G3 治理管道（6 checker）
│   ├── hallucination_checker.py       # 现有：第6个 checker
│   └── hallucination_auditor.py       # 现有：幻觉审计引擎
└── governance_events.py               # 现有：P2 治理快照
```

---

## 🏗️ 三层架构

### P0-1: AC Bus（统一事件总线）

```python
# 发布事件
bus = ACBus()
bus.publish(EventType.FILE_WRITTEN, {"path": "src/model.py", "content": "..."}, source="hermes")

# 订阅事件
def handle_file_written(event: BusEvent):
    print(f"文件写入: {event.payload['path']}")

bus.subscribe(EventType.FILE_WRITTEN, handle_file_written)
```

**事件类型**：
- `FILE_WRITTEN/MODIFIED/DELETED` - 文件事件
- `GOVERNANCE_STARTED/COMPLETED/FAILED` - 治理事件
- `TRUTH_STORED/UPDATED/DECAYED` - 知识库事件
- `TASK_CREATED/COMPLETED/FAILED/ESCALATED` - 任务事件
- `SESSION_STARTED/ENDED/MESSAGE` - 对话事件
- `SCHEDULER_ROUTED/SUBAGENT_INVOKED` - 调度事件

**预设处理器**：
- `HallucinationAuditorHandler` - 订阅 FILE_WRITTEN，自动审计文件内容
- `CaseCenterHandler` - 订阅 GOVERNANCE_FAILED，自动捕获问题
- `KnowledgeServiceRefreshHandler` - 订阅 TRUTH_STORED，刷新知识缓存

---

### P0-2: KnowledgeService（统一知识服务）

```python
ks = KnowledgeService()

# dispatch 使用：搜索知识
results = ks.search("高血压", categories=["medical"], min_confidence=0.8)

# orchestrator VERIFY 使用：事实核查
check = ks.check_fact("高血压诊断标准是140/90", category="medical")

# auditor 使用：获取锚点
anchors = ks.get_anchors(category="medical")
```

---

### P1: Central Scheduler（中央调度器）

```python
scheduler = UnifiedDispatcher()

# 统一入口
result = scheduler.dispatch("帮我写一个Python函数")

# 自动路由：
# - 代码生成 → SubAgent
# - 知识查询 → AC
# - 架构设计 → SubAgent
```

**路由决策**：
| 任务类型 | 执行器 | 治理 |
|---------|--------|------|
| KNOWLEDGE | AC | G3 |
| REASONING | AC | G3 |
| CODE_GENERATION | SubAgent | G3 |
| ARCHITECTURE | SubAgent | G3 |
| DOCUMENTATION | SubAgent | G3 |

---

## 📊 测试结果

```
AC Bus 测试:
✅ 基础发布/订阅正常
✅ Case Center 自动捕获正常
✅ 追踪 ID 功能正常
✅ 事件持久化正常

KnowledgeService 测试:
✅ search() 查询正常
✅ check_fact() 核查正常
✅ CDC 增量同步正常

Central Scheduler 测试:
✅ 任务路由正常（代码→SubAgent，知识→AC）
✅ 统一持久化正常
```

---

## 🎯 对标你的7个断点

| 断点 | 问题 | 解决方案 | 状态 |
|------|------|----------|------|
| #1 | 改文件绕过G3 | AC Bus FILE_WRITTEN 事件 → HallucinationAuditor 自动订阅审计 | ✅ |
| #2 | dispatch不查truth | KnowledgeService.search() 注入 ranker | ✅ |
| #3 | orchestrator不读truth | KnowledgeService.check_fact() 注入 VERIFY phase | ✅ |
| #4 | auditor未集成 | HallucinationChecker 作为第6个 checker 接入 G3 | ✅ |
| #5 | Gate缺失 | Central Scheduler 输入分类步骤内置 Gate | ✅ |
| #6 | escalate缺失 | Central Scheduler 路由逻辑内置 escalate | ✅ |
| #7 | SubAgent独立 | SubAgent 改造为 Central Scheduler 的执行引擎 | ✅ |

---

## 改造后的架构全景

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    所有入口 → Central Scheduler                             │
│                           │                                               │
│         ┌─────────────────┼─────────────────┐                              │
│         ▼                 ▼                 ▼                              │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐                        │
│  │   对话端   │   │    CLI     │   │    Web    │                        │
│  └─────┬──────┘   └─────┬──────┘   └─────┬──────┘                        │
│        └─────────────────┼─────────────────┘                              │
│                          ▼                                                │
│              ┌───────────────────────┐                                   │
│              │   输入分类 + 路由决策   │  ← Central Scheduler             │
│              │   + Gate + Escalate  │                                   │
│              └───────────┬───────────┘                                   │
│                          │                                               │
│         ┌────────────────┼────────────────┐                              │
│         ▼                ▼                ▼                              │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐                        │
│  │  AC Pool   │   │Orchestrator│   │ SubAgent  │                        │
│  │ (知识/推理)│   │ (复杂任务) │   │(代码生成)  │                        │
│  └─────┬──────┘   └──────┬─────┘   └─────┬─────┘                        │
│        │                  │                │                              │
│        └──────────────────┼────────────────┘                              │
│                           ▼                                               │
│              ┌───────────────────────┐                                   │
│              │    AC Bus（事件总线）  │                                   │
│              │   统一事件发布/订阅    │                                   │
│              └───────────┬───────────┘                                   │
│                          │                                               │
│         ┌────────────────┼────────────────┐                              │
│         ▼                ▼                ▼                              │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐                        │
│  │ Hallucina- │   │  Case      │   │Knowledge   │                        │
│  │ tionAuditor│   │  Center    │   │ Service    │                        │
│  │ (订阅文件) │   │(订阅失败)  │   │(订阅入库)  │                        │
│  └────────────┘   └────────────┘   └────────────┘                        │
│                          │                                               │
│                          ▼                                               │
│              ┌───────────────────────┐                                   │
│              │   G3 治理管道（统一）  │                                   │
│              │  6个 checker 含幻觉审计│                                   │
│              └───────────┬───────────┘                                   │
│                          │                                               │
│                          ▼                                               │
│              ┌───────────────────────┐                                   │
│              │   AC Truth 知识库     │                                   │
│              └───────────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

**关键变化**：

1. **从"多入口各自决定路由"** → **"Central Scheduler 统一决策"**
2. **从"知识库是被动存储"** → **"KnowledgeService 是主动服务"**
3. **从"模块间隐式依赖"** → **"AC Bus 显式事件契约"**
4. **从"7个独立断点"** → **"三层架构一次覆盖"**

---

**完成日期：** 2026-05-14
**状态：** ✅ P0/P1 全部完成！7个断点已通过三层架构全部覆盖

