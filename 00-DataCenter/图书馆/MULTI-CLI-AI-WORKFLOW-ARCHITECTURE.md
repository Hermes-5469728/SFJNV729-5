# 多CLI + 多AI 单人工作流架构图

> 绝对颗粒度 · 工业级标准 · 13态任务生命周期

---

## 一、系统整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AC Platform · 工作流平台                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     CLI Interaction Layer · CLI交互层                 │   │
│  │                                                                      │   │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │   │dispatch  │  │annotate  │  │orchestrate│ │ verify   │  ...       │   │
│  │   │  命令    │  │  命令    │  │   命令    │  │  命令    │            │   │
│  │   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │   │
│  │        │             │             │             │                   │   │
│  │        └─────────────┴─────────────┴─────────────┘                   │   │
│  │                              │                                        │   │
│  │                    ┌─────────▼─────────┐                              │   │
│  │                    │  Schema Validator │ ← Pydantic Validation         │   │
│  │                    │  Auto Corrector  │ ← Auto-correction Loop        │   │
│  │                    └─────────┬─────────┘                              │   │
│  └──────────────────────────────┼──────────────────────────────────────┘   │
│                                 │                                            │
│  ┌──────────────────────────────▼──────────────────────────────────────┐   │
│  │                    Governance Layer · 治理层                           │   │
│  │                                                                      │   │
│  │   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐        │   │
│  │   │ collaborative_ │  │  high_risk_    │  │  resource_     │        │   │
│  │   │ governor       │  │  interceptor   │  │  lock_manager  │        │   │
│  │   │ (端到端验证)    │  │ (风险拦截)     │  │ (资源锁)       │        │   │
│  │   └───────┬────────┘  └───────┬────────┘  └───────┬────────┘        │   │
│  │           │                   │                   │                   │   │
│  │   ┌───────▼───────────────────▼───────────────────▼────────┐        │   │
│  │   │              HITL Manager · 人在回路管理器                 │        │   │
│  │   │     (CONFIRM / CHOOSE / REVIEW · 异步审批)              │        │   │
│  │   └─────────────────────────┬───────────────────────────────┘        │   │
│  └────────────────────────────┼────────────────────────────────────────┘   │
│                               │                                                │
│  ┌────────────────────────────▼────────────────────────────────────────┐   │
│  │                  Orchestrator Core · 编排核心                        │   │
│  │                                                                      │   │
│  │   ┌────────────────────────────────────────────────────────────┐    │   │
│  │   │              TaskGraph Manager · 任务图管理器                 │    │   │
│  │   │                                                              │    │   │
│  │   │   session_id: str ← 唯一会话标识                             │    │   │
│  │   │   root_prompt: str ← 原始需求                                │    │   │
│  │   │   plan: List[PlanStep] ← 执行计划                           │    │   │
│  │   │   agent_pool: Dict ← 可用Agent池                            │    │   │
│  │   │   shared_context: Dict ← 共享上下文                          │    │   │
│  │   │   hitl_queue: List ← HITL请求队列                          │    │   │
│  │   │   metrics: OrchestratorMetrics ← 指标统计                    │    │   │
│  │   └────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  │   ┌────────────────────────────────────────────────────────────┐    │   │
│  │   │           StateMachine · 状态机（13态严格验证）               │    │   │
│  │   │                                                              │    │   │
│  │   │   CREATED → QUEUED → PLANNING → PLANNED → EXECUTING        │    │   │
│  │   │      ↓         ↓          ↓          ↓           ↓          │    │   │
│  │   │   FAILED     BLOCKED   VERIFYING  REJECTED   VERIFIED      │    │   │
│  │   │      ↓                                        ↓          │    │   │
│  │   │   ROLLING_BACK ← FAILED                    COMPLETED      │    │   │
│  │   │      ↓                                                     │    │   │
│  │   │   ROLLED_BACK                                          │    │   │
│  │   └────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  │   ┌────────────────────────────────────────────────────────────┐    │   │
│  │   │          Five-Phase Loop · 五阶段主循环                     │    │   │
│  │   │                                                              │    │   │
│  │   │      ┌───────┐                                              │    │   │
│  │   │      │ PLAN  │ ──→ 任务拆解 + Agent分配                      │    │   │
│  │   │      └───┬───┘                                              │    │   │
│  │   │          │                                                  │    │   │
│  │   │      ┌───▼───┐                                              │    │   │
│  │   │      │EXECUTE│ ──→ 并行执行 + 依赖管理                        │    │   │
│  │   │      └───┬───┘                                              │    │   │
│  │   │          │                                                  │    │   │
│  │   │      ┌───▼───┐                                              │    │   │
│  │   │      │VERIFY │ ──→ 端到端验证 + 评分                         │    │   │
│  │   │      └───┬───┘                                              │    │   │
│  │   │          │                                                  │    │   │
│  │   │      ┌───▼───┐                                              │    │   │
│  │   │      │RESOLVE│ ──→ 结果汇总 / 回滚                           │    │   │
│  │   │      └───┬───┘                                              │    │   │
│  │   │          │                                                  │    │   │
│  │   │      ┌───▼───┐                                              │    │   │
│  │   │      │  LOG  │ ──→ 经验持久化 + 学习                        │    │   │
│  │   │      └───────┘                                              │    │   │
│  │   └────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Memory & Evolution · 记忆与进化                    │   │
│  │                                                                      │   │
│  │   ┌─────────────────┐              ┌─────────────────┐               │   │
│  │   │ TaskDecomposer │              │  MemoryManager  │               │   │
│  │   │  (任务拆解)     │              │  (向量数据库)    │               │   │
│  │   │                 │              │                 │               │   │
│  │   │ • 未知识别       │              │ • store_exp()  │               │   │
│  │   │ • 澄清反问       │              │ • retrieve()   │               │   │
│  │   │ • 递归拆解       │              │ • similarity   │               │   │
│  │   │ • 并行路径识别   │              │   search       │               │   │
│  │   └─────────────────┘              └────────┬────────┘               │   │
│  │                                              │                       │   │
│  │                                    ┌─────────▼─────────┐             │   │
│  │                                    │    ChromaDB       │             │   │
│  │                                    │  (experience库)    │             │   │
│  │                                    └───────────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、CLI命令体系

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CLI Commands · CLI命令体系                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  dispatch ─────────────────────────────────────────────────────────────►    │
│    └─► Expert Dispatching · 专家调度                                         │
│         └─► Schema: OrchestrateInput/Output                                 │
│                                                                             │
│  annotate ─────────────────────────────────────────────────────────────►    │
│    └─► L5 Annotation · L5标注                                              │
│         └─► Schema: AnnotationInput/Output                                  │
│                                                                             │
│  orchestrate ─────────────────────────────────────────────────────────►    │
│    └─► Multi-Agent Orchestration · 多Agent编排                               │
│         ├─► Schema: OrchestrateInput/Output                                 │
│         ├─► StateMachine Integration                                        │
│         └─► HITL: CONFIRM before execution                                  │
│                                                                             │
│  verify ──────────────────────────────────────────────────────────────►    │
│    └─► End-to-End Verification · 端到端验证                                 │
│         ├─► Schema: VerifyInput/Output                                     │
│         └─► Types: url / database / file                                    │
│                                                                             │
│  contract ────────────────────────────────────────────────────────────►    │
│    └─► Contract Validation · 契约校验                                        │
│         └─► Schema: ContractInput/Output                                    │
│                                                                             │
│  state ───────────────────────────────────────────────────────────────►    │
│    └─► State Management · 状态管理                                          │
│         └─► Schema: StateInput/Output                                      │
│                                                                             │
│  risk ─────────────────────────────────────────────────────────────────►    │
│    └─► Risk Assessment · 风险评估                                           │
│         └─► Schema: RiskInput/Output                                       │
│                                                                             │
│  lock ─────────────────────────────────────────────────────────────────►    │
│    └─► Resource Locking · 资源锁                                            │
│         └─► Schema: LockInput/Output                                       │
│                                                                             │
│  complete ─────────────────────────────────────────────────────────────►    │
│    └─► Full Task Flow · 完整任务流程                                        │
│         └─► contract + verify + state (原子操作)                             │
│                                                                             │
│  orch-status ─────────────────────────────────────────────────────────►    │
│    └─► Query Orchestration Status · 查询编排状态                             │
│         └─► Schema: OrchStatusOutput                                        │
│                                                                             │
│  orch-list ───────────────────────────────────────────────────────────►    │
│    └─► List All Sessions · 列出所有会话                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、13态任务生命周期

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    13-State Task Lifecycle · 13态任务生命周期                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                                                                             │
│    CREATED                                                                 │
│       │                                                                    │
│       ├──► [QUEUED] ────────────────────► PLANNING                        │
│       │         │                                │                         │
│       │         │                    ┌───────────┴───────────┐              │
│       │         │                    │                       │              │
│       │         │               [PLANNED]               [FAILED]          │
│       │         │                    │                       │              │
│       │         │                    ▼                       │              │
│       │         │               ┌─────────┐                  │              │
│       │         │               │ EXECUTE │◄─────────────────┘              │
│       │         │               └────┬────┘                                 │
│       │         │                    │                                      │
│       │         │         ┌─────────┼─────────┐                            │
│       │         │         │                   │                            │
│       │         │    [BLOCKED]          [VERIFYING]                       │
│       │         │         │                   │                            │
│       │         │         └───────────────────┤                            │
│       │         │                         │                              │
│       │         │            ┌────────────┼────────────┐                 │
│       │         │            │                       │                  │
│       │         │       [VERIFIED]              [REJECTED]                │
│       │         │            │                       │                   │
│       │         │            ▼                       ▼                    │
│       │         │      [COMPLETED]             [RETRYING]                │
│       │         │            ▲                       │                   │
│       │         │            └───────────────────────┼──────► [QUEUED]    │
│       │         │                                    │                    │
│       │    [FAILED]                                 │                    │
│       │         │                                    │                    │
│       │         └────────────────────────────────────┘                    │
│       │                        │                                          │
│       │                   [ROLLING_BACK]                                  │
│       │                        │                                          │
│       │                        ▼                                          │
│       │                  [ROLLED_BACK]                                   │
│       │                                                                      │
│       ▼                                                                      │
│    [FAILED] ──────────────────────────► [ROLLING_BACK]                       │
│                                                                             │
│                                                                             │
│  ╔═════════════════════════════════════════════════════════════════════╗   │
│  ║                        状态转换规则 (TRANSITIONS)                        ║   │
│  ╠═════════════════════════════════════════════════════════════════════╣   │
│  ║  CREATED    → [QUEUED, FAILED]                                        ║   │
│  ║  QUEUED     → [EXECUTING, FAILED]                                     ║   │
│  ║  PLANNING   → [PLANNED, FAILED]                                       ║   │
│  ║  PLANNED    → [QUEUED, FAILED]                                        ║   │
│  ║  EXECUTING  → [VERIFYING, FAILED, BLOCKED]                            ║   │
│  ║  BLOCKED    → [QUEUED, FAILED]                                        ║   │
│  ║  VERIFYING  → [VERIFIED, REJECTED, FAILED]                            ║   │
│  ║  VERIFIED   → [COMPLETED]                                             ║   │
│  ║  REJECTED   → [RETRYING, FAILED]                                      ║   │
│  ║  RETRYING   → [QUEUED, FAILED]                                        ║   │
│  ║  FAILED     → [ROLLING_BACK]                                          ║   │
│  ║  ROLLING_BACK → [ROLLED_BACK]                                         ║   │
│  ║  COMPLETED  → [终态，不允许转换]                                        ║   │
│  ║  ROLLED_BACK → [终态，不允许转换]                                       ║   │
│  ╚═════════════════════════════════════════════════════════════════════╝   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 四、Schema验证流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                Schema Validation & Auto-Correction · Schema验证与自动修正     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   User Input                                                                │
│       │                                                                     │
│       ▼                                                                     │
│   ┌───────────────────┐                                                    │
│   │  Parse Arguments   │                                                    │
│   └─────────┬─────────┘                                                    │
│             │                                                               │
│             ▼                                                               │
│   ┌───────────────────┐                                                    │
│   │ Build Input Dict   │                                                    │
│   └─────────┬─────────┘                                                    │
│             │                                                               │
│             ▼                                                               │
│   ┌───────────────────┐                                                    │
│   │ Pydantic Validate │                                                    │
│   └─────────┬─────────┘                                                    │
│             │                                                               │
│       ┌─────┴─────┐                                                         │
│       │  Success? │                                                         │
│       └─────┬─────┘                                                         │
│         Yes │ No                                                            │
│       ┌─────┴─────┐                                                         │
│       │           │                                                         │
│       ▼           ▼                                                         │
│   ┌───────┐  ┌───────────────────┐                                         │
│   │  OK   │  │ AutoCorrector     │                                         │
│   │       │  │                   │                                         │
│   │       │  │ • missing_field   │                                         │
│   │       │  │ • type_error     │                                         │
│   │       │  │ • value_error    │                                         │
│   │       │  │ • constrained    │                                         │
│   │       │  └─────────┬─────────┘                                         │
│   │       │            │                                                  │
│   │       │            ▼                                                  │
│   │       │    ┌───────────────┐                                          │
│   │       │    │ Correction    │                                          │
│   │       │    │   Success?    │                                          │
│   │       │    └───────┬───────┘                                          │
│   │       │        Yes  │ No                                               │
│   │       │    ┌───────┴───────┐                                          │
│   │       │    │               │                                           │
│   │       │    ▼               ▼                                           │
│   │       │  Retry          Raise                                          │
│   │       │  Validation     GuardExit                                      │
│   │       │      │                                                    │
│   │       │      └──────────────────────► Execute Command                  │
│   └───────┘                                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 五、TaskGraph 数据结构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TaskGraph · 任务图结构                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TaskGraph                                                                 │
│  ├── session_id: str                    # 唯一会话标识 (UUID)               │
│  ├── status: OrchestratorStatus        # RUNNING / PAUSED / FAILED / ...   │
│  ├── root_prompt: str                   # 用户原始需求                       │
│  │                                                                         │
│  ├── plan: List[PlanStep]               # 执行计划                          │
│  │   └── PlanStep                       # 每个步骤                          │
│  │       ├── step_id: str               # 步骤ID (step_001)                 │
│  │       ├── description: str           # 步骤描述                          │
│  │       ├── assigned_agent: str        # 分配的Agent                       │
│  │       ├── depends_on: List[str]      # 依赖的步骤ID列表                   │
│  │       ├── status: TaskState          # 当前状态 (13态之一)                │
│  │       ├── retry_count: int           # 已重试次数                        │
│  │       ├── max_retries: int          # 最大重试次数                       │
│  │       ├── timeout_seconds: int      # 超时时间                          │
│  │       ├── output: Dict[str, Any]    # 执行输出                          │
│  │       ├── verification_spec: Dict   # 验证规格                          │
│  │       ├── verification_result: Dict# 验证结果                          │
│  │       ├── error: Optional[str]       # 错误信息                         │
│  │       ├── started_at: Optional[float]# 开始时间戳                        │
│  │       ├── completed_at: Optional[float] # 完成时间戳                   │
│  │       └── elapsed_seconds: float     # 耗时                             │
│  │                                                                         │
│  ├── agent_pool: Dict[str, AgentSpec]   # 可用Agent池                      │
│  │   └── AgentSpec                                                     │
│  │       ├── agent_id: str             # Agent标识                        │
│  │       ├── capabilities: List[str]  # 能力列表                         │
│  │       ├── context_window: str       # 上下文窗口                       │
│  │       └── contract_schema: Dict    # 契约Schema                        │
│  │                                                                         │
│  ├── shared_context: Dict[str, Any]     # 共享上下文                        │
│  ├── hitl_queue: List[HITLRequest]     # HITL请求队列                     │
│  │   └── HITLRequest                                                   │
│  │       ├── request_id: str           # 请求ID                           │
│  │       ├── type: HITLType            # CONFIRM / CHOOSE / REVIEW        │
│  │       ├── prompt: str               # 提示文本                          │
│  │       ├── options: Optional[List]   # 选项列表                          │
│  │       ├── status: HITLStatus       # PENDING / APPROVED / REJECTED    │
│  │       ├── response: Optional[str]   # 用户响应                          │
│  │       └── created_at: float         # 创建时间戳                        │
│  │                                                                         │
│  └── metrics: OrchestratorMetrics      # 指标统计                         │
│      ├── total_steps: int              # 总步骤数                          │
│      ├── completed_steps: int          # 已完成步骤                        │
│      ├── failed_steps: int             # 失败步骤                          │
│      ├── retry_count: int              # 总重试次数                        │
│      ├── elapsed_seconds: float        # 总耗时                            │
│      └── hitl_interruptions: int      # HITL中断次数                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 六、五阶段主循环

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Five-Phase Loop · 五阶段主循环                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                         ┌─────────────┐                                    │
│                         │   START     │                                    │
│                         └──────┬──────┘                                    │
│                                │                                           │
│                                ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         PHASE 1: PLAN                                │  │
│  │                                                                      │  │
│  │   1. TaskDecomposer.decompose(root_prompt)                          │  │
│  │      ├── 识别未知信息 → ClarificationQuestion                        │  │
│  │      ├── 调用LLM拆解 → List[SubTask]                               │  │
│  │      └── 识别并行路径 → parallel_groups                             │  │
│  │                                                                      │  │
│  │   2. HITLManager.create_request(CONFIRM)                            │  │
│  │      └── 用户确认计划                                                 │  │
│  │                                                                      │  │
│  │   3. StateMachine.transition(PLANNING → PLANNED)                    │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                │                                           │
│                                ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         PHASE 2: EXECUTE                             │  │
│  │                                                                      │  │
│  │   while not all_steps_completed:                                    │  │
│  │      │                                                              │  │
│  │      ├── ready_steps = get_ready_steps(graph)                       │  │
│  │      │   └── depends_on all COMPLETED                               │  │
│  │      │                                                              │  │
│  │      ├── limit_to_max_workers(ready_steps)                          │  │
│  │      │                                                              │  │
│  │      └── for step in ready_steps:                                   │  │
│  │             asyncio.create_task(execute_step(graph, step))           │  │
│  │             │                                                       │  │
│  │             └── _safe_transition(CREATED → QUEUED → EXECUTING)     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                │                                           │
│                                ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         PHASE 3: VERIFY                              │  │
│  │                                                                      │  │
│  │   1. _safe_transition(EXECUTING → VERIFYING)                        │  │
│  │                                                                      │  │
│  │   2. VerificationEngine.verify(step)                                │  │
│  │      ├── url验证: requests.get(url)                                 │  │
│  │      ├── database验证: SQLAlchemy query                             │  │
│  │      └── file验证: pathlib.exists()                                 │  │
│  │                                                                      │  │
│  │   3. ScoringAgent.score(output)                                      │  │
│  │      ├── completeness (30%)                                         │  │
│  │      ├── quality (30%)                                              │  │
│  │      ├── compliance (20%)                                           │  │
│  │      └── performance (20%)                                          │  │
│  │                                                                      │  │
│  │   4. if score >= 70:                                                │  │
│  │          _safe_transition(VERIFY → VERIFIED → COMPLETED)            │  │
│  │      else:                                                          │  │
│  │          _safe_transition(VERIFY → REJECTED)                       │  │
│  │          handle_rejection() → RETRYING → QUEUED                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                │                                           │
│                                ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         PHASE 4: RESOLVE                             │  │
│  │                                                                      │  │
│  │   if all_completed:                                                 │  │
│  │      status = COMPLETED                                             │  │
│  │      shared_context["final_summary"] = summary                      │  │
│  │                                                                      │  │
│  │   elif critical_failed:                                             │  │
│  │      # 关键步骤失败 → 回滚                                           │  │
│  │      for step in reversed(COMPLETED):                               │  │
│  │          _safe_transition(COMPLETED → ROLLING_BACK → ROLLED_BACK)  │  │
│  │      status = FAILED                                                │  │
│  │                                                                      │  │
│  │   else:                                                             │  │
│  │      # 非关键失败 → 部分完成                                         │  │
│  │      status = COMPLETED (with warnings)                              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                │                                           │
│                                ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         PHASE 5: LOG                                 │  │
│  │                                                                      │  │
│  │   1. TaskGraphManager.save_graph(graph)                              │  │
│  │      └── SQLite: task_graphs table                                   │  │
│  │                                                                      │  │
│  │   2. MemoryManager.store_experience(experience)                      │  │
│  │      └── ChromaDB: experiences collection                            │  │
│  │          ├── task_type                                              │  │
│  │          ├── goal                                                   │  │
│  │          ├── solution                                               │  │
│  │          └── success / failure_reason                               │  │
│  │                                                                      │  │
│  │   3. Output metrics:                                                 │  │
│  │      ├── total_steps                                                │  │
│  │      ├── completed_steps                                             │  │
│  │      ├── failed_steps                                               │  │
│  │      ├── retry_count                                                │  │
│  │      └── hitl_interruptions                                          │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                │                                           │
│                                ▼                                           │
│                         ┌─────────────┐                                   │
│                         │     END     │                                   │
│                         └─────────────┘                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 七、数据流与依赖关系

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Data Flow · 数据流与依赖关系                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   User                                                                     
│     │                                                                      
│     ▼                                                                      
│   CLI Input ──────────► Schema Validation ──────────► Auto Corrector       
│                             │                            │                  
│                             │ Error                     │ Success          
│                             ▼                            ▼                  
│                        GuardExit                   Execute Command          
│                                                               │              
│                                                               ▼              
│                                              ┌─────────────────────────┐   
│                                              │   Orchestrator.orchestrate │   
│                                              └────────────┬──────────────┘   
│                                                         │                   
│       ┌──────────────────────────────────────────────────┼──────────────┐  
│       │                                                  │              │  
│       ▼                                                  ▼              ▼  
│   ┌─────────┐                                     ┌─────────┐    ┌─────┐
│   │TaskGraph│                                     │MemoryDB │    │SQLite│
│   └────┬────┘                                     └────┬────┘    └─────┘
│        │                                               │              
│        │    ┌──────────────────────────────────────────┘              
│        │    │                                                          
│        ▼    ▼                                                          
│   ┌──────────────────────────────────────────────────────────────┐      
│   │                    Agent Pool · Agent池                       │      
│   │                                                               │      
│   │   ┌────────────┐  ┌────────────┐  ┌────────────┐            │      
│   │   │backend_dev│  │security_expert│ │frontend_dev│  ...      │      
│   │   └─────┬──────┘  └─────┬──────┘  └─────┬──────┘            │      
│   │         │                │                │                    │      
│   │         └────────────────┼────────────────┘                    │      
│   │                          │                                     │      
│   │                          ▼                                     │      
│   │              ┌────────────────────────┐                       │      
│   │              │   Dispatch & Execute   │                       │      
│   │              └────────────────────────┘                       │      
│   │                          │                                     │      
│   └──────────────────────────┼────────────────────────────────────┘      
│                              │                                           
│                              ▼                                           
│                      ┌───────────────┐                                   
│                      │    Output     │                                   
│                      └───────────────┘                                   
│                                                                           
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 八、信任分数与自动化级别

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              Trust Score & Automation Level · 信任分数与自动化级别             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      Trust Score Calculation                         │  │
│   │                                                                      │  │
│   │   trust_score =                                                     │  │
│   │       success_rate × 40  +   // 成功率权重 40%                       │  │
│   │       avg_score × 30     +   // 平均分权重 30%                       │  │
│   │       no_intervention_rate × 30  // 无干预率权重 30%                 │  │
│   │                                                                      │  │
│   │   where:                                                            │  │
│   │       • success_rate = successful_tasks / total_tasks               │  │
│   │       • avg_score = sum(scores) / count(scores)                     │  │
│   │       • no_intervention_rate = no_hitl_tasks / total_tasks          │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      Automation Level Decision                        │  │
│   │                                                                      │  │
│   │      ┌────────────────────────────────────────────────────────┐    │  │
│   │      │                                                         │    │  │
│   │      │     trust_score >= 90  ──────► FULL_AUTO                │    │  │
│   │      │          │                      (完全自动，事后通知)       │    │  │
│   │      │          │                                             │    │  │
│   │      │          ▼                                             │    │  │
│   │      │     trust_score >= 70  ──────► AUTO_WITH_NOTIFY        │    │  │
│   │      │          │                      (自动执行，实时通知)      │    │  │
│   │      │          │                                             │    │  │
│   │      │          ▼                                             │    │  │
│   │      │     trust_score >= 50  ──────► CONFIRM_CRITICAL        │    │  │
│   │      │          │                      (只确认关键步骤)          │    │  │
│   │      │          │                                             │    │  │
│   │      │          ▼                                             │    │  │
│   │      │     trust_score < 50  ───────► MANUAL                  │    │  │
│   │      │                               (完全手动)                 │    │  │
│   │      │                                                         │    │  │
│   │      └────────────────────────────────────────────────────────┘    │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 九、技术栈概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Tech Stack · 技术栈                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Language                                                                 
│   ├── Python >= 3.10                                                      
│   └── Rust (future: digital_twin_sdk)                                     
│                                                                             
│   Web & API                                                                
│   ├── FastAPI 0.104+                                                       
│   └── Uvicorn                                                              
│                                                                             
│   Data & Validation                                                        
│   ├── SQLAlchemy 2.0+ (ORM)                                               
│   ├── SQLite (via SQLAlchemy)                                             
│   └── Pydantic 2.0+ (Schema)                                             
│                                                                             
│   LLM & AI                                                                
│   ├── Ollama (local)                                                      
│   ├── DashScope (Alibaba)                                                  
│   └── DeepSeek (fallback)                                                  
│                                                                             
│   Vector & Search                                                          
│   ├── ChromaDB (experience storage)                                        
│   └── TF-IDF + Cosine Similarity                                          
│                                                                             
│   CLI & Interaction                                                        
│   ├── argparse (CLI)                                                       
│   └── HITL Manager (async approval)                                        
│                                                                             
│   Governance                                                               
│   ├── collaborative_governor (端到端验证)                                   
│   ├── high_risk_interceptor (风险拦截)                                     
│   └── resource_lock_manager (资源锁)                                       
│                                                                             
│   Build & Quality                                                          
│   ├── Makefile                                                            
│   ├── setuptools                                                          
│   ├── Ruff (lint)                                                         
│   └── mypy (type check)                                                   
│                                                                             
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 十、目录结构

```
{USER_HOME}\AC\
│
├── cli.py                           # CLI入口 (15+ commands)
│
├── ac/
│   ├── orchestrator.py              # 编排核心 (StateMachine + 13态)
│   ├── schemas/
│   │   └── orchestrator_schemas.py  # Pydantic Schema定义
│   ├── auto_corrector.py            # 自动修正器
│   ├── task_decomposer.py           # LLM任务拆解器
│   ├── memory_manager.py             # 向量数据库记忆
│   ├── collaborative_governor.py     # 协同治理
│   ├── governor.py                   # 治理引擎
│   ├── input_guard.py                # 输入守卫
│   ├── guard.py                      # 熔断器
│   └── ...
│
├── governance/
│   ├── checker.py                   # 检查器
│   ├── corrector.py                  # 修正器
│   ├── security.py                   # 安全检查
│   ├── semantic.py                   # 语义检查
│   └── syntax.py                     # 语法检查
│
├── qa/
│   ├── pipeline/                    # QA管线
│   │   ├── cleaner.py               
│   │   ├── deduplicator.py         
│   │   ├── language_filter.py      
│   │   └── quality_filter.py       
│   └── tests/                        # 测试用例
│
├── ac_memory/                       # ChromaDB向量数据库
│
├── ac_platform.db                   # SQLite主数据库
│
├── IMPLEMENTATION-CHECKLIST.md       # 实施检查清单
├── 00-AC/图书馆/ORCHESTRATOR-EVALUATION.md  # 评估方案
│
└── requirements.txt                 # 运行时依赖
```

---

## 十一、质量门禁 (Quality Gates)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Quality Gates · 多层质量门禁                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         L1: Format Validation                        │  │
│   │   • JSON/YAML syntax check                                          │  │
│   │   • Required fields present                                         │  │
│   │   • Type correctness                                                │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         L2: Static Analysis                          │  │
│   │   • Ruff linting                                                     │  │
│   │   • mypy type checking                                               │  │
│   │   • Security scan (bandit)                                           │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         L3: Unit Tests                               │  │
│   │   • pytest execution                                                  │  │
│   │   • Coverage >= 80%                                                  │  │
│   │   • All assertions pass                                              │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      L4: Integration Tests                            │  │
│   │   • End-to-end workflow test                                         │  │
│   │   • Database operations                                              │  │
│   │   • External API mocks                                               │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         L5: Health Check                              │  │
│   │   • Service ping                                                     │  │
│   │   • Dependency availability                                          │  │
│   │   • Resource limits                                                  │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 十二、关键不变量

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Invariants · 关键不变量                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ╔═════════════════════════════════════════════════════════════════════╗  │
│   ║  1. 不存在任何LLM输出被当作事实直接采信                                  ║  │
│   ║  2. 所有输出必须携带中英双语幻觉声明                                     ║  │
│   ║  3. 任意两个模块的表名集合交集为空                                       ║  │
│   ║  4. 所有数据库操作通过 Depends(get_db) 注入                             ║  │
│   ║  5. 子体响应 ≠ 母体命令                                                 ║  │
│   ║  6. 累计违宪3次立即SEVER                                               ║  │
│   ║  7. 状态转换必须经过StateMachine验证                                    ║  │
│   ╚═════════════════════════════════════════════════════════════════════╝  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

*文档版本: v1.0 · 基于 Atelier 15条定义 + 13态任务图 + 工业级标准*