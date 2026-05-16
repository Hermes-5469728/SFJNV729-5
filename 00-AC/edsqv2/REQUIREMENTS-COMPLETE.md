# AC Platform 架构需求清单 - 完整版

> **整理时间：** 2026-05-14
> **版本：** v4.0
> **状态：** 持续更新

---

## 📋 需求总览

| 优先级 | 编号 | 需求 | 状态 | 关联文件 |
|--------|------|------|------|---------|
| **P0** | R-01 | AC Bus - 统一事件总线 | ✅ 已完成 | `ac_bus.py` |
| **P0** | R-02 | 持久化消息队列 | ✅ 已完成 | `persistent_queue.py` |
| **P0** | R-03 | 优雅关闭 | ✅ 已完成 | `graceful_shutdown.py` |
| **P0** | R-04 | 全局请求追踪 | ✅ 已完成 | `request_context.py` |
| **P0** | R-05 | CI/CD 流水线 | ✅ 已完成 | `.github/workflows/` |
| **P0** | R-05a | GitHub Pages 部署 | ✅ 已完成 | `.github/workflows/deploy-pages.yml` |
| **P0** | R-05b | 失败通知 | ✅ 已完成 | `.github/workflows/notify.yml` |
| **P0** | R-05c | Dependabot 依赖扫描 | ✅ 已完成 | `dependabot.yml` |
| **P0** | R-05d | 自动版本 + CHANGELOG | ✅ 已完成 | `.github/workflows/cd.yml` |
| **P0** | R-05e | 自动回滚 | ✅ 已完成 | `.github/workflows/cd.yml` |
| **P0** | R-06 | 模块间通信总线 | ✅ 已完成 | `ac_bus.py` + `Server模式` |
| **P0** | R-15 | 单一源码架构 | ✅ 已完成 | `SINGLE-SOURCE-OF-TRUTH.md` |
| **P1** | R-07 | 知识服务层 (KnowledgeService) | ✅ 已完成 | `knowledge_service_p0.py` |
| **P1** | R-08 | 中央调度器 (Central Scheduler) | ✅ 已完成 | `unified_dispatcher.py` |
| **P1** | R-09 | 资源锁 (TTL + 心跳) | ✅ 已完成 | `resource_lock.py` |
| **P1** | R-10 | 三层执行架构 | ✅ 已完成 | `THREE-LAYER-EXECUTION.md` |
| **P1** | R-11 | CLI 薄客户端改造 | ✅ 已完成 | `ac_client.py` |
| **P1** | R-12 | Server 模式 (FastAPI + WebSocket) | ✅ 已完成 | `ac_server.py` |
| **P1** | R-16 | SubAgent 集成引擎 | ✅ 已完成 | `subagent_integration.py` |
| **P1** | R-17 | 统一健康检查总线 | ✅ 已完成 | `health_monitor.py` |
| **P1** | R-18 | Phase A 生产级 Server | ✅ 已完成 | `ac_server.py` |
| **P1** | R-19 | Phase B WebSocket + File Watch | ✅ 已完成 | `ws_message_queue.py`, `file_watch.py` |
| **P1** | R-20 | AC AI Bus - 多 AI 协作总线 | ✅ 已完成 | `ai_registry.py`, `ai_bus.py` |
| **P2** | R-14 | AWAITING_HUMAN 状态 | 🔲 待实施 | - |

---

## P0 需求详情

### R-01: AC Bus - 统一事件总线

**问题**：模块间通过隐式约定协作，形成"治理真空"

**解决方案**：
- 所有模块的状态变更、治理事件、知识更新都通过 Bus 发布/订阅
- 从"模块间隐式依赖"变成"AC Bus 显式事件契约"

**文件**：`ac_bus.py`

---

### R-05: CI/CD 流水线

**问题**：
1. 系统无法自行进化（无 CI/CD，任何更新都靠人触发）
2. 系统无法自行协作（模块间互不感知，依赖人工转述）

**解决方案**：

```
CI (持续集成)：
┌─────────────────────────────────────────────┐
│  push/pull_request → Lint → TypeCheck → Test → Security → Build
└─────────────────────────────────────────────┘

CD (持续部署)：
┌─────────────────────────────────────────────┐
│  tag v* → Release → Deploy Staging → Deploy Production
│                  ↓
            自动回滚（失败时）
└─────────────────────────────────────────────┘
```

**流水线文件**：
- `.github/workflows/ci.yml` - 持续集成
- `.github/workflows/cd.yml` - 持续部署
- `.github/workflows/events.yml` - 事件同步

---

### R-06: 模块间通信总线

**问题**：星型结构，所有协作必须经过"对话端"作为中间人

**解决方案**：
```
改造前（星型）：
  Module A → 你 → Module B
  Module A → 你 → Module C
  （串行瓶颈）

改造后（总线型）：
  Module A ──┐
             ├──→ AC Bus ──→ Module B
  Module C ──┘          └──→ Module D
  （并行解耦）
```

**组件**：
- AC Bus（事件总线）- 异步事件驱动
- Server 模式（HTTP/WS API）- 同步 API 调用

**文件**：`ac_bus.py`, `Server模式(待实现)`

---

### R-02: PersistentMessageQueue - 持久化消息队列

**问题**：`asyncio.Queue` 内存队列，进程重启丢消息

**解决方案**：
- SQLite 持久化，进程重启不丢消息
- ACK 机制：Worker 处理完成后确认
- 超时重试：未确认消息自动重新入队
- 追踪 ID：关联同一请求的所有消息

**核心 API**：
```python
queue = PersistentMessageQueue("message_queue.db")

msg_id = queue.enqueue("dispatch", {"request": "..."}, trace_id="trace_001")
msg = queue.dequeue("dispatch")
queue.ack(msg.id)
queue.nack(msg.id, requeue=True)
```

**文件**：`persistent_queue.py`

---

### R-03: GracefulShutdown - 优雅关闭

**问题**：Server 模式接收请求期间，如何停止服务而不丢失正在处理的请求？

**解决方案**：
```
流程：
RUNNING → DRAINING → STOPPING → STOPPED

1. RUNNING → DRAINING：停止接收新任务，保留处理中的任务
2. DRAINING → STOPPING：所有任务处理完成后，开始关闭
3. STOPPING → STOPPED：超时则强制关闭
```

**核心 API**：
```python
shutdown = GracefulShutdown(timeout_seconds=60)

if shutdown.should_accept_request():
    queue.enqueue(...)
else:
    return 503

shutdown.track_task(worker_id, task_id)
try:
    process_task()
finally:
    shutdown.untrack_task(task_id)

shutdown.initiate_shutdown()
shutdown.wait_for_completion()
```

**文件**：`graceful_shutdown.py`

---

### R-04: RequestContext - 全局请求追踪

**问题**：多 CLT + 多 Agent 并行场景下，没有全局 Trace ID，问题定位困难

**解决方案**：
- `request_id`：请求唯一ID，在 Queue 层生成
- `trace_id`：追踪ID，关联同一次用户会话
- `RequestSpan`：追踪Span，记录模块操作和耗时
- 贯穿所有下游模块，所有日志和数据库写入都携带 request_id

**核心 API**：
```python
tracker = RequestTracker("tracking.db")
middleware = RequestContextMiddleware(tracker)

with middleware.request_context(user_id="user_001"):
    ctx = RequestContext.get_current()

    span = create_span("Queue", "enqueue")
    end_span(span)
```

**完整链路**：
```
Queue (enqueue)        → span[0]
    ↓
Worker (process)       → span[1]
    ↓
Orchestrator (execute) → span[2]
    ↓
G3 (govern)            → span[n]
```

**文件**：`request_context.py`

---

## P1 需求详情

### R-07: KnowledgeService - 知识服务层

**问题**：ac_truth 知识库是"只进不出"的存储，不参与调度、验证、幻觉检测

**解决方案**：
- 统一 API：search() / check_fact() / get_anchors()
- 事件驱动：新知识入库 → 通知相关模块重算
- TTL 衰减：confidence 随时间自动降低

**文件**：`knowledge_service_p0.py`

---

### R-08: Central Scheduler - 中央调度器

**问题**：多入口各自决定路由，形成双头架构

**解决方案**：
- 统一入口：所有请求经过 Central Scheduler
- 路由决策：简单查询 → Dispatch，复杂任务 → Orchestrator，代码生成 → SubAgent
- 统一持久化：task 和 governance_events 合并

**文件**：`unified_dispatcher.py`

---

### R-09: ResourceLock - 资源锁

**问题**：无 TTL 资源锁，CLT 崩溃后锁永不释放，导致资源永久阻塞

**解决方案**：
- TTL 自动释放：锁超时后自动过期
- 心跳联动：Worker 心跳丢失时自动清理其持有的所有锁
- 多粒度锁：Agent 级、记录级、字段级

**文件**：`resource_lock.py`

---

### R-10: 三层执行架构

**问题**：Dispatch / Orchestrator / SubAgent 三个引擎并列，协作关系不清晰

**解决方案**：
```
第一层：Stream Router（路由层）
        ├── 简单知识查询 → Dispatch
        ├── 复杂推理任务 → Orchestrator
        └── 纯代码生成 → SubAgent 直接执行

第二层：Orchestrator（编排层）
        ├── 13态状态机管理
        ├── EXECUTE 阶段派发子任务给 SubAgent
        └── VERIFY 阶段验证 SubAgent 输出

第三层：SubAgent（执行层）
        ├── 被调用方，不知道任务来自哪里
        ├── 负责模型调用和重试
        └── 结果交给调用方处理，不自行调用 G3
```

**文件**：`THREE-LAYER-EXECUTION.md`

---

## P1 待实施需求

### R-11: CLI 薄客户端改造

**内容**：
- CLI 改为 HTTP/WS 客户端，仅保留输入/显示
- 所有业务逻辑集中在 Server
- 配置 Server URL（支持本地/远程）

**依赖**：R-12 完成

---

### R-12: Server 模式

**内容**：
- FastAPI 服务端点 `/dispatch`
- WebSocket 端点 `/ws`
- 接入 PersistentMessageQueue
- 接入 AC Bus
- 接入 GracefulShutdown

**前置**：R-02, R-03

---

## P2 待实施需求

### R-13: 动态模型路由

**内容**：
- 模型健康检查（心跳、错误率）
- 速率限制和成本预算
- 动态降级链

**依赖**：R-08 完成

---

### R-14: AWAITING_HUMAN 状态

**内容**：
- Human-in-the-loop 暂停态
- 从该状态恢复到 generate 或 contract_validation
- 暂停超时自动 FAILED

---

## 文件清单

| 文件 | 用途 | 优先级 |
|------|------|--------|
| `ac_bus.py` | 统一事件总线 | P0 |
| `persistent_queue.py` | 持久化消息队列 | P0 |
| `graceful_shutdown.py` | 优雅关闭 | P0 |
| `request_context.py` | 全局请求追踪 | P0 |
| `knowledge_service_p0.py` | 知识服务层 | P1 |
| `unified_dispatcher.py` | 中央调度器 | P1 |
| `resource_lock.py` | 资源锁 | P1 |
| `governance_events.py` | 治理事件存储 | P1 |
| `governance_tasks.py` | 治理任务队列 | P1 |
| `governance/hallucination_checker.py` | 幻觉检查器 | P1 |
| `.github/workflows/ci.yml` | CI/CD 流水线 - 持续集成 | P0 |
| `.github/workflows/cd.yml` | CI/CD 流水线 - 持续部署 | P0 |

---

## 架构全景图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           所有入口 → Central Scheduler                       │
│                                      │                                      │
│         ┌────────────────────────────┼────────────────────────────┐        │
│         ▼                            ▼                            ▼        │
│  ┌────────────┐              ┌────────────┐              ┌────────────┐   │
│  │   CLI      │              │   Server   │              │  WebSocket │   │
│  │ (薄客户端) │              │ (FastAPI)  │              │            │   │
│  └─────┬──────┘              └─────┬──────┘              └─────┬──────┘   │
│        └───────────────────────────┼───────────────────────────┘          │
│                                    ▼                                       │
│                    ┌───────────────────────────────┐                       │
│                    │     Queue (持久化 + 优雅关闭)   │                       │
│                    │   PersistentMessageQueue      │                       │
│                    └───────────────┬───────────────┘                       │
│                                    │                                       │
│    ┌───────────────────────────────┼───────────────────────────────┐     │
│    ▼                               ▼                               ▼        │
│ ┌────────────┐            ┌────────────┐                 ┌────────────┐ │
│ │  Dispatch  │            │Orchestrator│                 │  SubAgent  │ │
│ │   (流A)     │            │   (流B)    │                 │  (执行层)  │ │
│ └─────┬──────┘            └──────┬─────┘                 └─────┬──────┘ │
│       │                          │                             │         │
│       └──────────────────────────┼─────────────────────────────┘         │
│                                  ▼                                        │
│                    ┌───────────────────────┐                             │
│                    │      AC Bus           │                             │
│                    │   (统一事件总线)       │                             │
│                    └───────────┬───────────┘                             │
│                                │                                         │
│    ┌───────────────────────────┼───────────────────────────────┐         │
│    ▼                           ▼                               ▼         │
│ ┌────────────┐          ┌────────────┐                 ┌────────────┐   │
│ │Hallucina-  │          │   Case     │                 │Knowledge   │   │
│ │tionAuditor │          │   Center   │                 │ Service    │   │
│ └────────────┘          └────────────┘                 └────────────┘   │
│                                │                                         │
│                                ▼                                         │
│                    ┌───────────────────────┐                             │
│                    │      G3 治理管道      │                             │
│                    │    (6 checker)        │                             │
│                    └───────────┬───────────┘                             │
│                                │                                         │
│                                ▼                                         │
│                    ┌───────────────────────┐                             │
│                    │   AC Truth 知识库    │                             │
│                    └───────────────────────┘                             │
└─────────────────────────────────────────────────────────────────────────────┘

追踪层：
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RequestContext (全局请求追踪)                            │
│                    trace_id + request_id + spans                           │
└─────────────────────────────────────────────────────────────────────────────┘

资源层：
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ResourceLock (TTL + 心跳联动)                            │
│                    Agent级 / 记录级 / 字段级                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

