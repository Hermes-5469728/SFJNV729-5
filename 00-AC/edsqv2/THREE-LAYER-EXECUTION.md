# 三层执行架构 - 层级关系定义

> **时间：** 2026-05-14
> **问题：** Dispatch / Orchestrator / SubAgent 三者并列，协作关系不清晰
> **方案：** 定义三层层级关系，避免"三个并列引擎各管各"

---

## 根因分析

```
当前问题：
┌─────────────────────────────────────────────────────────────┐
│                    三个引擎并列                              │
│                                                             │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │  Dispatch   │  │Orchestrator│  │  SubAgent   │        │
│   │   (流A)     │  │   (流B)     │  │  (多模型)   │        │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│          │                │                │               │
│          └────────────────┴────────────────┘               │
│                    谁调用谁？不清晰                          │
└─────────────────────────────────────────────────────────────┘

风险：
1. Orchestrator EXECUTE 阶段不知道可以调用 SubAgent
2. SubAgent 生成结果不知道需要经过 Orchestrator VERIFY
3. 调度决策分散，三个引擎各自闭环
```

---

## 解决方案：三层执行架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         第一层：Stream Router（路由）                         │
│                                                                             │
│   输入 ──→ 意图分类 ──→ 决定：Dispatch / Orchestrator / SubAgent 直接执行    │
│                                                                             │
│   职责：                                                                     │
│   - 简单知识查询 → Dispatch                                                  │
│   - 复杂推理任务 → Orchestrator                                              │
│   - 纯代码生成（无验证需求）→ SubAgent 直接执行                               │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
        ┌───────────┐   ┌─────────────────┐   ┌───────────┐
        │  Dispatch │   │  Orchestrator   │   │ SubAgent  │
        │   (流A)    │   │    (流B)        │   │  直接执行  │
        └─────┬─────┘   └────────┬────────┘   └───────────┘
              │                  │                      │
              │    ┌─────────────┴─────────────┐        │
              │    │                           │        │
              │    ▼                           ▼        │
              │   EXECUTE                SUBAGENT       │
              │   阶段可以                状态机        │
              │   调用 SubAgent                        │
              │                           │            │
              │    ┌──────────────────────┘            │
              │    │                                    │
              │    ▼                                    │
              │   VERIFY                                │
              │   (验证 SubAgent 输出)                   │
              │                  │                       │
              └──────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────┐
                    │     G3 治理管道     │
                    └─────────────────────┘
```

---

## 层级职责定义

### 第一层：Stream Router（路由层）

**职责**：接收所有请求，决定走哪条执行路径

| 决策 | 路由目标 | 说明 |
|------|---------|------|
| 简单知识查询 | Dispatch | 意图明确，直接返回 |
| 需要多步推理 | Orchestrator | 进入 13 态状态机 |
| 纯代码生成（无验证需求）| SubAgent | 直接执行，快速返回 |
| 复杂任务 + 代码子任务 | Orchestrator → SubAgent | Orchestrator EXECUTE 阶段调用 |

**实现**：`unified_dispatcher.py` 的 `_classify_domain()` 方法

---

### 第二层：Orchestrator（编排层）

**职责**：管理复杂任务的 13 态状态机，编排执行流程

**状态机**：
```
IDLE → RECEIVED → ROUTED → PLANNING → EXECUTING → VERIFYING
                    │                          │
                    ▼                          ▼
                 FAILED ←────────────── VERIFY_FAILED
                    │
                    ▼
              EXECUTING（执行子任务）
                    │
                    ├──→ SubAgent 状态机（代码生成）
                    ├──→ Tool Call（工具调用）
                    └──→ 其他 Agent
                    │
                    ▼
               VERIFYING（验证输出）
```

**关键能力**：EXECUTE 阶段调用 SubAgent

```python
class Orchestrator:
    def execute_step(self, plan: ExecutionPlan):
        for subtask in plan.subtasks:
            if subtask.type == SubtaskType.CODE_GENERATION:
                # 调用 SubAgent 状态机
                result = self.subagent.execute(subtask)
                # SubAgent 结果进入 VERIFY 阶段
                return self.verify(result)
            else:
                # 其他子任务
                ...
```

---

### 第三层：SubAgent（执行层）

**职责**：负责具体的模型调用和重试，是被调用方

**特性**：
- 不知道任务来自哪里（Dispatch / Orchestrator）
- 不负责路由决策
- 只负责：接收任务 → 状态机执行 → 返回结果

**被调用方式**：

```python
# Orchestrator 调用 SubAgent
result = subagent.execute(
    task=code_task,
    context={"trace_id": self.trace_id}
)

# Stream Router 直接调用 SubAgent（简单场景）
result = subagent.execute_simple(task)
```

**结果处理**：
- SubAgent 返回结果给调用方
- **不自行进入 G3 治理**
- 由调用方（Orchestrator / Stream Router）决定是否走 G3

---

## 协作流程示例

### 场景1：简单知识查询

```
用户：什么是高血压？

Stream Router → 分类为 KNOWLEDGE → Dispatch → Expert Pool → 返回结果
```

### 场景2：复杂推理任务

```
用户：分析这个患者的症状并生成治疗方案

Stream Router → 分类为 REASONING → Orchestrator
  → PLANNING：分解为分析子任务 + 方案生成子任务
  → EXECUTE：
      - 分析子任务 → Agent Pool
      - 方案生成子任务 → SubAgent 状态机
  → VERIFY：验证 SubAgent 生成的方案
  → G3 治理管道
  → 返回结果
```

### 场景3：纯代码生成

```
用户：帮我写一个快速排序函数

Stream Router → 分类为 CODE_GENERATION（无验证需求）
  → SubAgent 直接执行
  → 返回代码（跳过 G3，因为是纯生成任务）
```

---

## 文件对应关系

| 层级 | 文件 | 职责 |
|------|------|------|
| 第一层 | `unified_dispatcher.py` | Stream Router，路由决策 |
| 第二层 | `orchestrator.py` | Orchestrator，13态状态机，EXECUTE可调用SubAgent |
| 第三层 | `subagent/` | SubAgent 状态机，被调用方 |
| 治理层 | `governance/` | G3 治理管道 |

---

## 关键约束

1. **SubAgent 不能自行决定路由** - 所有路由经过 Stream Router
2. **SubAgent 结果必须经过 VERIFY** - Orchestrator 的职责
3. **Orchestrator 可以调用 SubAgent** - EXECUTE 阶段的子任务派发
4. **简单任务可跳过 Orchestrator** - Stream Router 直接派发给 SubAgent
5. **G3 治理由调用方决定** - SubAgent 不自行调用 G3

---

## 测试验证

### 测试1：Orchestrator 调用 SubAgent

```python
orchestrator = Orchestrator()
plan = orchestrator.plan_task("分析症状并生成代码")

# EXECUTE 阶段应该调用 SubAgent
result = orchestrator.execute_step(plan)

# 结果应该经过 VERIFY
assert result.verified == True
```

### 测试2：SubAgent 不能直接进入 G3

```python
# 错误做法
subagent_result = subagent.execute(task)
g3.govern(subagent_result)  # ❌ 不应该

# 正确做法
orchestrator_result = orchestrator.execute_with_subagent(task)
g3.govern(orchestrator_result)  # ✅ 由 Orchestrator 调用 G3
```

---

**决策结论：** Dispatch / Orchestrator / SubAgent 是三层嵌套关系，而非并列关系。

