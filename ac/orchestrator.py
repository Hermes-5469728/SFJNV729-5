#!/usr/bin/env python3
"""
Orchestrator · 多轮规划循环引擎

职责：将单轮 dispatch 升级为完整的规划→执行→验证→循环体系
核心功能：
1. TaskGraph 任务图管理
2. 13态任务生命周期状态机
3. PLAN/EXECUTE/VERIFY/RESOLVE/LOG 五阶段循环
4. HITL（人在回路）中断机制
5. 依赖树驱动的任务调度
6. 失败恢复与回滚
7. 经验学习（写入 ac_truth）
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# ==================== 枚举定义 ====================

class TaskState(Enum):
    """任务状态（13态）"""
    CREATED = "created"          # 任务已定义，未调度
    QUEUED = "queued"            # 等待依赖的上游完成
    PLANNING = "planning"        # Orchestrator 正在生成执行计划
    PLANNED = "planned"          # 计划已确认
    EXECUTING = "executing"      # Agent 正在执行
    BLOCKED = "blocked"          # 等待外部输入/用户确认
    VERIFYING = "verifying"      # 执行完，正在端到端验证
    VERIFIED = "verified"        # 验证通过
    REJECTED = "rejected"        # 验证不通过，打回重做
    RETRYING = "retrying"        # 失败后自动重试
    FAILED = "failed"            # 超过重试上限
    ROLLING_BACK = "rolling_back" # 回滚中
    ROLLED_BACK = "rolled_back"  # 回滚完成
    COMPLETED = "completed"      # 最终完成

class HITLType(Enum):
    """人在回路请求类型"""
    CONFIRM = "confirm"          # 确认继续
    CHOOSE = "choose"            # 选择选项
    REVIEW = "review"            # 审核内容

class HITLStatus(Enum):
    """人在回路状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class OrchestratorStatus(Enum):
    """Orchestrator 全局状态"""
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"

# ==================== 状态机验证 ====================

class InvalidStateTransition(Exception):
    """非法状态转换异常"""
    def __init__(self, current: TaskState, next_state: TaskState):
        super().__init__(f"非法状态转换：{current.value} -> {next_state.value}")
        self.current = current
        self.next_state = next_state

class StateMachine:
    """严格的状态机，防止非法状态转换"""
    
    # 状态转换规则：当前状态 -> 允许的下一状态列表
    TRANSITIONS = {
        TaskState.CREATED: [TaskState.QUEUED, TaskState.FAILED],
        TaskState.QUEUED: [TaskState.EXECUTING, TaskState.FAILED],
        TaskState.PLANNING: [TaskState.PLANNED, TaskState.FAILED],
        TaskState.PLANNED: [TaskState.QUEUED, TaskState.FAILED],
        TaskState.EXECUTING: [TaskState.VERIFYING, TaskState.FAILED, TaskState.BLOCKED],
        TaskState.BLOCKED: [TaskState.QUEUED, TaskState.FAILED],
        TaskState.VERIFYING: [TaskState.VERIFIED, TaskState.REJECTED, TaskState.FAILED],
        TaskState.VERIFIED: [TaskState.COMPLETED],
        TaskState.REJECTED: [TaskState.RETRYING, TaskState.FAILED],
        TaskState.RETRYING: [TaskState.QUEUED, TaskState.FAILED],
        TaskState.FAILED: [TaskState.ROLLING_BACK],
        TaskState.ROLLING_BACK: [TaskState.ROLLED_BACK],
        # 终态：不允许任何转换
        TaskState.COMPLETED: [],
        TaskState.ROLLED_BACK: [],
    }
    
    def can_transition(self, current: TaskState, next_state: TaskState) -> bool:
        """检查状态转换是否合法"""
        allowed = self.TRANSITIONS.get(current, [])
        return next_state in allowed
    
    def transition(self, current: TaskState, next_state: TaskState) -> TaskState:
        """执行状态转换，返回新状态"""
        if not self.can_transition(current, next_state):
            raise InvalidStateTransition(current, next_state)
        
        print(f"🔄 [STATE] {current.value} -> {next_state.value}")
        return next_state
    
    def get_allowed_transitions(self, current: TaskState) -> List[TaskState]:
        """获取当前状态允许的下一状态"""
        return self.TRANSITIONS.get(current, [])
    
    def is_terminal(self, state: TaskState) -> bool:
        """检查是否为终态"""
        return len(self.TRANSITIONS.get(state, [])) == 0

# ==================== 数据结构 ====================

@dataclass
class PlanStep:
    """计划步骤"""
    step_id: str
    description: str
    assigned_agent: str
    depends_on: List[str] = field(default_factory=list)
    status: TaskState = TaskState.CREATED
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    output: Optional[Dict[str, Any]] = None
    verification_spec: Optional[Dict[str, Any]] = None
    verification_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    elapsed_seconds: float = 0.0

@dataclass
class AgentSpec:
    """Agent 规格"""
    agent_id: str
    capabilities: List[str] = field(default_factory=list)
    context_window: str = ""
    contract_schema: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HITLRequest:
    """人在回路请求"""
    request_id: str
    type: HITLType
    prompt: str
    options: Optional[List[str]] = None
    status: HITLStatus = HITLStatus.PENDING
    response: Optional[str] = None
    created_at: float = field(default_factory=lambda: time.time())

@dataclass
class OrchestratorMetrics:
    """指标统计"""
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    retry_count: int = 0
    elapsed_seconds: float = 0.0
    hitl_interruptions: int = 0

@dataclass
class TaskGraph:
    """任务图"""
    session_id: str
    status: OrchestratorStatus = OrchestratorStatus.RUNNING
    root_prompt: str = ""
    plan: List[PlanStep] = field(default_factory=list)
    agent_pool: Dict[str, AgentSpec] = field(default_factory=dict)
    shared_context: Dict[str, Any] = field(default_factory=dict)
    hitl_queue: List[HITLRequest] = field(default_factory=list)
    metrics: OrchestratorMetrics = field(default_factory=OrchestratorMetrics)
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())

# ==================== 核心组件 ====================

class TaskGraphManager:
    """任务图管理器"""
    
    def __init__(self, db_path: str = "ac_platform.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建任务图表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_graphs (
                session_id TEXT PRIMARY KEY,
                status TEXT,
                root_prompt TEXT,
                plan TEXT,
                agent_pool TEXT,
                shared_context TEXT,
                hitl_queue TEXT,
                metrics TEXT,
                created_at REAL,
                updated_at REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_graph(self, graph: TaskGraph):
        """保存任务图到数据库"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO task_graphs (
                session_id, status, root_prompt, plan, agent_pool,
                shared_context, hitl_queue, metrics, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            graph.session_id,
            graph.status.value,
            graph.root_prompt,
            json.dumps([self._step_to_dict(s) for s in graph.plan]),
            json.dumps({k: self._agent_to_dict(v) for k, v in graph.agent_pool.items()}),
            json.dumps(graph.shared_context),
            json.dumps([self._hitl_to_dict(h) for h in graph.hitl_queue]),
            json.dumps(self._metrics_to_dict(graph.metrics)),
            graph.created_at,
            time.time()
        ))
        
        conn.commit()
        conn.close()
    
    def load_graph(self, session_id: str) -> Optional[TaskGraph]:
        """从数据库加载任务图"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM task_graphs WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return TaskGraph(
            session_id=row[0],
            status=OrchestratorStatus(row[1]),
            root_prompt=row[2],
            plan=[self._dict_to_step(s) for s in json.loads(row[3])],
            agent_pool={k: self._agent_to_spec(v) for k, v in json.loads(row[4]).items()},
            shared_context=json.loads(row[5]),
            hitl_queue=[self._dict_to_hitl(h) for h in json.loads(row[6])],
            metrics=self._dict_to_metrics(json.loads(row[7])),
            created_at=row[8],
            updated_at=row[9]
        )
    
    def _step_to_dict(self, step: PlanStep) -> Dict[str, Any]:
        return {
            "step_id": step.step_id,
            "description": step.description,
            "assigned_agent": step.assigned_agent,
            "depends_on": step.depends_on,
            "status": step.status.value,
            "retry_count": step.retry_count,
            "max_retries": step.max_retries,
            "timeout_seconds": step.timeout_seconds,
            "output": step.output,
            "verification_spec": step.verification_spec,
            "verification_result": step.verification_result,
            "error": step.error,
            "started_at": step.started_at,
            "completed_at": step.completed_at,
            "elapsed_seconds": step.elapsed_seconds
        }
    
    def _dict_to_step(self, d: Dict[str, Any]) -> PlanStep:
        return PlanStep(
            step_id=d["step_id"],
            description=d["description"],
            assigned_agent=d["assigned_agent"],
            depends_on=d["depends_on"],
            status=TaskState(d["status"]),
            retry_count=d["retry_count"],
            max_retries=d["max_retries"],
            timeout_seconds=d["timeout_seconds"],
            output=d["output"],
            verification_spec=d["verification_spec"],
            verification_result=d["verification_result"],
            error=d["error"],
            started_at=d["started_at"],
            completed_at=d["completed_at"],
            elapsed_seconds=d["elapsed_seconds"]
        )
    
    def _agent_to_dict(self, agent: AgentSpec) -> Dict[str, Any]:
        return {
            "agent_id": agent.agent_id,
            "capabilities": agent.capabilities,
            "context_window": agent.context_window,
            "contract_schema": agent.contract_schema
        }
    
    def _agent_to_spec(self, d: Dict[str, Any]) -> AgentSpec:
        return AgentSpec(
            agent_id=d["agent_id"],
            capabilities=d["capabilities"],
            context_window=d["context_window"],
            contract_schema=d["contract_schema"]
        )
    
    def _hitl_to_dict(self, hitl: HITLRequest) -> Dict[str, Any]:
        return {
            "request_id": hitl.request_id,
            "type": hitl.type.value,
            "prompt": hitl.prompt,
            "options": hitl.options,
            "status": hitl.status.value,
            "response": hitl.response,
            "created_at": hitl.created_at
        }
    
    def _dict_to_hitl(self, d: Dict[str, Any]) -> HITLRequest:
        return HITLRequest(
            request_id=d["request_id"],
            type=HITLType(d["type"]),
            prompt=d["prompt"],
            options=d["options"],
            status=HITLStatus(d["status"]),
            response=d["response"],
            created_at=d["created_at"]
        )
    
    def _metrics_to_dict(self, metrics: OrchestratorMetrics) -> Dict[str, Any]:
        return {
            "total_steps": metrics.total_steps,
            "completed_steps": metrics.completed_steps,
            "failed_steps": metrics.failed_steps,
            "retry_count": metrics.retry_count,
            "elapsed_seconds": metrics.elapsed_seconds,
            "hitl_interruptions": metrics.hitl_interruptions
        }
    
    def _dict_to_metrics(self, d: Dict[str, Any]) -> OrchestratorMetrics:
        return OrchestratorMetrics(
            total_steps=d["total_steps"],
            completed_steps=d["completed_steps"],
            failed_steps=d["failed_steps"],
            retry_count=d["retry_count"],
            elapsed_seconds=d["elapsed_seconds"],
            hitl_interruptions=d["hitl_interruptions"]
        )

class HITLManager:
    """人在回路管理器"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
    
    def create_request(self, type: HITLType, prompt: str, options: Optional[List[str]] = None) -> HITLRequest:
        """创建 HITL 请求"""
        return HITLRequest(
            request_id=str(uuid.uuid4()),
            type=type,
            prompt=prompt,
            options=options
        )
    
    async def wait_for_response(self, request: HITLRequest, timeout: int = 300) -> bool:
        """等待用户响应"""
        if not self.enabled:
            return True
        
        print(f"\n⚠️  [HITL - {request.type.value.upper()}] {request.prompt}")
        if request.options:
            print("选项:")
            for i, opt in enumerate(request.options, 1):
                print(f"  {i}. {opt}")
        
        print("\n请输入响应 (APPROVE/REJECT 或选项序号):")
        try:
            # 在CLI环境中读取用户输入
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, input, "> ")
            response = response.strip().upper()
            
            if response in ["APPROVE", "YES", "CONFIRM", "1"]:
                request.status = HITLStatus.APPROVED
                request.response = response
                return True
            elif response in ["REJECT", "NO", "CANCEL", "0"]:
                request.status = HITLStatus.REJECTED
                request.response = response
                return False
            else:
                # 处理选项选择
                try:
                    idx = int(response) - 1
                    if 0 <= idx < len(request.options):
                        request.status = HITLStatus.APPROVED
                        request.response = request.options[idx]
                        return True
                except:
                    pass
                request.status = HITLStatus.REJECTED
                request.response = "INVALID_INPUT"
                return False
        except EOFError:
            request.status = HITLStatus.REJECTED
            request.response = "EOF"
            return False

class VerificationEngine:
    """端到端验证引擎（复用 collaborative_governor）"""
    
    def __init__(self):
        from ac.collaborative_governor import collaborative_governor
        self.governor = collaborative_governor
    
    async def verify(self, step: PlanStep) -> bool:
        """验证步骤输出"""
        if not step.verification_spec:
            return True
        
        spec = step.verification_spec
        verify_type = spec.get("type")
        params = spec.get("params", {})
        
        result = await self.governor.verify_task(step.step_id, verify_type, params)
        step.verification_result = {
            "status": result.status.value,
            "message": result.message,
            "evidence": result.evidence,
            "latency_ms": result.latency_ms
        }
        
        return result.status.value == "pass"

class ScoringAgent:
    """评分代理"""
    
    def __init__(self):
        self.rubric = {
            "completeness": {"weight": 0.3, "description": "完整性"},
            "quality": {"weight": 0.3, "description": "质量"},
            "compliance": {"weight": 0.2, "description": "合规性"},
            "performance": {"weight": 0.2, "description": "性能"}
        }
    
    def score(self, output: Dict[str, Any], step: PlanStep) -> float:
        """计算分数（0-100）"""
        score = 0.0
        
        # 完整性检查
        if output and isinstance(output, dict):
            score += 30
        
        # 质量检查（简单模拟）
        content = output.get("content", "") if output else ""
        if len(content) >= 100:
            score += 30
        else:
            score += min(len(content), 30)
        
        # 合规性检查
        if step.assigned_agent in ["security_expert", "backend_dev"]:
            if "security" in str(output).lower():
                score += 20
        
        # 性能检查（基于执行时间）
        if step.elapsed_seconds < 60:
            score += 20
        elif step.elapsed_seconds < 120:
            score += 10
        
        return min(score, 100.0)

class Orchestrator:
    """编排器核心"""
    
    def __init__(self, max_active_workers: int = 2):
        self.graph_manager = TaskGraphManager()
        self.hitl_manager = HITLManager()
        self.verification_engine = VerificationEngine()
        self.scoring_agent = ScoringAgent()
        self.state_machine = StateMachine()  # 集成状态机
        self.max_active_workers = max_active_workers
        self.active_tasks = set()
    
    def _safe_transition(self, step: PlanStep, next_state: TaskState, step_name: str = ""):
        """安全状态转换：使用状态机验证转换合法性"""
        try:
            step.status = self.state_machine.transition(step.status, next_state)
            return True
        except InvalidStateTransition as e:
            print(f"❌ [STATE ERROR] {step_name}: {e}")
            step.status = TaskState.FAILED
            step.error = str(e)
            return False
    
    async def orchestrate(self, root_prompt: str, agent_pool: Dict[str, AgentSpec]) -> TaskGraph:
        """
        完整编排流程：PLAN → EXECUTE → VERIFY → RESOLVE → LOG
        """
        session_id = str(uuid.uuid4())
        graph = TaskGraph(
            session_id=session_id,
            root_prompt=root_prompt,
            agent_pool=agent_pool,
            metrics=OrchestratorMetrics(total_steps=0)
        )
        
        start_time = time.time()
        
        try:
            # 1. PLAN phase
            await self._plan_phase(graph)
            
            # 2. EXECUTE phase (循环)
            await self._execute_phase(graph)
            
            # 3. RESOLVE phase
            await self._resolve_phase(graph)
            
        except Exception as e:
            graph.status = OrchestratorStatus.FAILED
            graph.metrics.elapsed_seconds = time.time() - start_time
            raise
        finally:
            # 5. LOG phase
            await self._log_phase(graph)
        
        graph.metrics.elapsed_seconds = time.time() - start_time
        return graph
    
    async def _plan_phase(self, graph: TaskGraph):
        """PLAN 阶段：拆解任务、分配 Agent"""
        print(f"🔄 [PLAN] 开始规划: {graph.root_prompt}")
        
        # 标记状态
        graph.status = OrchestratorStatus.RUNNING
        
        # 简单的手动构图示例（后续可接入LLM自动拆解）
        # TODO: 接入LLM生成PlanSteps
        await self._manual_plan(graph)
        
        # HITL: 用户确认计划
        plan_summary = "\n".join([
            f"{i+1}. [{s.assigned_agent}] {s.description}"
            for i, s in enumerate(graph.plan)
        ])
        
        hitl_request = self.hitl_manager.create_request(
            HITLType.CONFIRM,
            f"计划已生成，共 {len(graph.plan)} 个步骤:\n{plan_summary}\n\n确认执行此计划？"
        )
        graph.hitl_queue.append(hitl_request)
        graph.metrics.hitl_interruptions += 1
        
        confirmed = await self.hitl_manager.wait_for_response(hitl_request)
        if not confirmed:
            raise RuntimeError("用户取消执行")
        
        # 更新步骤状态（使用安全转换）
        for step in graph.plan:
            self._safe_transition(step, TaskState.PLANNED, f"规划完成 {step.step_id}")
        
        graph.metrics.total_steps = len(graph.plan)
        self.graph_manager.save_graph(graph)
        
        print(f"✅ [PLAN] 计划已确认")
    
    async def _manual_plan(self, graph: TaskGraph):
        """手动构图（演示用，后续替换为LLM自动拆解）"""
        # 基于关键词匹配生成步骤
        prompt = graph.root_prompt.lower()
        
        steps = []
        
        # 登录模块示例规划
        if "登录" in prompt or "login" in prompt:
            steps = [
                PlanStep(
                    step_id="step_001",
                    description="设计用户登录表结构",
                    assigned_agent="backend_dev",
                    depends_on=[],
                    verification_spec={"type": "database", "params": {"table": "users", "query": "SELECT * FROM users LIMIT 1"}}
                ),
                PlanStep(
                    step_id="step_002",
                    description="实现密码加密与验证逻辑",
                    assigned_agent="security_expert",
                    depends_on=["step_001"],
                    verification_spec={"type": "file", "params": {"path": "src/auth/password.py"}}
                ),
                PlanStep(
                    step_id="step_003",
                    description="实现JWT token生成与验证",
                    assigned_agent="backend_dev",
                    depends_on=["step_002"],
                    verification_spec={"type": "file", "params": {"path": "src/auth/jwt.py"}}
                ),
                PlanStep(
                    step_id="step_004",
                    description="实现登录API端点",
                    assigned_agent="backend_dev",
                    depends_on=["step_003"],
                    verification_spec={"type": "file", "params": {"path": "src/api/login.py"}}
                )
            ]
        
        # 通用默认规划
        elif len(graph.agent_pool) > 0:
            first_agent = list(graph.agent_pool.keys())[0]
            steps = [
                PlanStep(
                    step_id="step_001",
                    description=f"执行任务: {graph.root_prompt}",
                    assigned_agent=first_agent,
                    depends_on=[]
                )
            ]
        
        graph.plan = steps
    
    async def _execute_phase(self, graph: TaskGraph):
        """EXECUTE 阶段：执行任务循环"""
        print(f"🔄 [EXECUTE] 开始执行 {len(graph.plan)} 个步骤")
        
        while True:
            # 检查是否所有步骤都完成
            completed = all(s.status in [TaskState.COMPLETED, TaskState.FAILED, TaskState.ROLLED_BACK] for s in graph.plan)
            if completed:
                break
            
            # 找出可执行的步骤（依赖已满足）
            ready_steps = self._get_ready_steps(graph)
            
            # 限制并发数
            ready_steps = ready_steps[:self.max_active_workers - len(self.active_tasks)]
            
            if not ready_steps:
                # 检查是否有 BLOCKED 步骤（等待用户输入）
                blocked = [s for s in graph.plan if s.status == TaskState.BLOCKED]
                if blocked:
                    for step in blocked:
                        await self._handle_blocked_step(graph, step)
                else:
                    # 等待一下再检查
                    await asyncio.sleep(1)
                continue
            
            # 并行执行
            tasks = []
            for step in ready_steps:
                task = asyncio.create_task(self._execute_step(graph, step))
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks)
            
            self.graph_manager.save_graph(graph)
        
        print(f"✅ [EXECUTE] 执行阶段完成")
    
    def _get_ready_steps(self, graph: TaskGraph) -> List[PlanStep]:
        """获取可执行的步骤（依赖已满足且未完成）"""
        ready = []
        
        for step in graph.plan:
            # 跳过已完成或正在执行的步骤
            if step.status in [TaskState.COMPLETED, TaskState.FAILED, TaskState.EXECUTING, TaskState.RETRYING]:
                continue
            
            # 检查依赖是否都已完成
            dependencies_satisfied = all(
                self._get_step_by_id(graph, dep_id) is not None and
                self._get_step_by_id(graph, dep_id).status == TaskState.COMPLETED
                for dep_id in step.depends_on
            )
            
            if dependencies_satisfied and step.status == TaskState.CREATED:
                self._safe_transition(step, TaskState.QUEUED, f"入队 {step.step_id}")
            
            if dependencies_satisfied and step.status == TaskState.QUEUED:
                ready.append(step)
        
        return ready
    
    def _get_step_by_id(self, graph: TaskGraph, step_id: str) -> Optional[PlanStep]:
        """根据ID获取步骤"""
        for step in graph.plan:
            if step.step_id == step_id:
                return step
        return None
    
    async def _execute_step(self, graph: TaskGraph, step: PlanStep):
        """执行单个步骤"""
        if step.step_id in self.active_tasks:
            return
        
        self.active_tasks.add(step.step_id)
        self._safe_transition(step, TaskState.EXECUTING, f"开始执行 {step.step_id}")
        step.started_at = time.time()
        
        print(f"🔄 [EXECUTE] 执行步骤: {step.step_id} - {step.description}")
        
        try:
            # 模拟 dispatch 调用（实际应调用 real dispatch）
            result = await self._simulate_dispatch(graph, step)
            
            if result["success"]:
                step.output = result["output"]
                step.completed_at = time.time()
                step.elapsed_seconds = step.completed_at - step.started_at
                
                # VERIFY phase
                await self._verify_step(graph, step)
            else:
                step.error = result.get("error", "Unknown error")
                await self._handle_failure(graph, step)
        
        except Exception as e:
            step.error = str(e)
            await self._handle_failure(graph, step)
        
        finally:
            self.active_tasks.discard(step.step_id)
    
    async def _simulate_dispatch(self, graph: TaskGraph, step: PlanStep) -> Dict[str, Any]:
        """模拟 dispatch 调用（实际应接入 real dispatch）"""
        await asyncio.sleep(1)  # 模拟执行时间
        
        # 模拟成功执行
        return {
            "success": True,
            "output": {
                "content": f"Step {step.step_id} executed successfully",
                "agent": step.assigned_agent,
                "step_id": step.step_id
            }
        }
    
    async def _verify_step(self, graph: TaskGraph, step: PlanStep):
        """VERIFY 阶段：验证步骤"""
        self._safe_transition(step, TaskState.VERIFYING, f"开始验证 {step.step_id}")
        print(f"🔍 [VERIFY] 验证步骤: {step.step_id}")
        
        # 端到端验证
        verified = await self.verification_engine.verify(step)
        
        if verified:
            # 评分
            score = self.scoring_agent.score(step.output, step)
            print(f"📊 [VERIFY] 步骤 {step.step_id} 评分: {score:.1f}/100")
            
            if score >= 70:
                self._safe_transition(step, TaskState.VERIFIED, f"验证通过 {step.step_id}")
                self._safe_transition(step, TaskState.COMPLETED, f"完成 {step.step_id}")
                graph.metrics.completed_steps += 1
                print(f"✅ [VERIFY] 步骤 {step.step_id} 通过")
            else:
                self._safe_transition(step, TaskState.REJECTED, f"评分不足 {step.step_id}")
                print(f"❌ [VERIFY] 步骤 {step.step_id} 评分不足，打回重做")
                await self._handle_rejection(graph, step)
        else:
            self._safe_transition(step, TaskState.REJECTED, f"验证失败 {step.step_id}")
            print(f"❌ [VERIFY] 步骤 {step.step_id} 验证失败")
            await self._handle_rejection(graph, step)
    
    async def _handle_rejection(self, graph: TaskGraph, step: PlanStep):
        """处理验证不通过"""
        if step.retry_count < step.max_retries:
            step.retry_count += 1
            graph.metrics.retry_count += 1
            self._safe_transition(step, TaskState.RETRYING, f"重试中 {step.step_id}")
            self._safe_transition(step, TaskState.QUEUED, f"重新入队 {step.step_id}")
            print(f"🔄 [RETRY] 步骤 {step.step_id} 重试 ({step.retry_count}/{step.max_retries})")
        else:
            self._safe_transition(step, TaskState.FAILED, f"失败 {step.step_id}")
            graph.metrics.failed_steps += 1
            print(f"❌ [FAILED] 步骤 {step.step_id} 超过重试上限")
    
    async def _handle_failure(self, graph: TaskGraph, step: PlanStep):
        """处理执行失败"""
        if step.retry_count < step.max_retries:
            step.retry_count += 1
            graph.metrics.retry_count += 1
            self._safe_transition(step, TaskState.RETRYING, f"重试中 {step.step_id}")
            self._safe_transition(step, TaskState.QUEUED, f"重新入队 {step.step_id}")
            print(f"🔄 [RETRY] 步骤 {step.step_id} 执行失败重试 ({step.retry_count}/{step.max_retries})")
        else:
            self._safe_transition(step, TaskState.FAILED, f"失败 {step.step_id}")
            graph.metrics.failed_steps += 1
            print(f"❌ [FAILED] 步骤 {step.step_id} 执行失败")
    
    async def _handle_blocked_step(self, graph: TaskGraph, step: PlanStep):
        """处理阻塞步骤（等待用户输入）"""
        hitl_request = self.hitl_manager.create_request(
            HITLType.CONFIRM,
            f"步骤 {step.step_id} 等待确认:\n{step.description}\n\n继续执行？"
        )
        graph.hitl_queue.append(hitl_request)
        graph.metrics.hitl_interruptions += 1
        
        confirmed = await self.hitl_manager.wait_for_response(hitl_request)
        if confirmed:
            step.status = TaskState.QUEUED
        else:
            step.status = TaskState.FAILED
            graph.metrics.failed_steps += 1
    
    async def _resolve_phase(self, graph: TaskGraph):
        """RESOLVE 阶段：汇总结果或回滚"""
        print(f"🔄 [RESOLVE] 汇总结果")
        
        # 检查是否全部完成
        all_completed = all(s.status == TaskState.COMPLETED for s in graph.plan)
        
        if all_completed:
            graph.status = OrchestratorStatus.COMPLETED
            print(f"✅ [RESOLVE] 所有步骤完成")
            
            # 汇总输出到共享上下文
            summary = {
                "session_id": graph.session_id,
                "total_steps": len(graph.plan),
                "completed_steps": graph.metrics.completed_steps,
                "steps": [{"step_id": s.step_id, "output": s.output} for s in graph.plan]
            }
            graph.shared_context["final_summary"] = summary
        else:
            # 检查失败步骤
            failed_steps = [s for s in graph.plan if s.status == TaskState.FAILED]
            
            if failed_steps:
                # 判断是否可降级
                critical_failed = any(s.depends_on == [] for s in failed_steps)
                
                if critical_failed:
                    # 关键步骤失败，执行回滚
                    await self._rollback(graph)
                else:
                    # 非关键步骤失败，标记部分完成
                    graph.status = OrchestratorStatus.COMPLETED
                    print(f"⚠️ [RESOLVE] 部分步骤失败，继续汇总")
    
    async def _rollback(self, graph: TaskGraph):
        """执行回滚"""
        print(f"🔄 [ROLLBACK] 执行回滚")
        
        # 按逆序依赖清理
        steps_to_rollback = sorted(
            [s for s in graph.plan if s.status == TaskState.COMPLETED],
            key=lambda x: len(x.depends_on),
            reverse=True
        )
        
        for step in steps_to_rollback:
            step.status = TaskState.ROLLING_BACK
            print(f"🔄 [ROLLBACK] 回滚步骤: {step.step_id}")
            await asyncio.sleep(0.5)  # 模拟回滚操作
            step.status = TaskState.ROLLED_BACK
        
        graph.status = OrchestratorStatus.FAILED
        print(f"❌ [ROLLBACK] 回滚完成")
    
    async def _log_phase(self, graph: TaskGraph):
        """LOG 阶段：持久化经验"""
        print(f"🔄 [LOG] 记录任务图")
        
        # 保存到数据库
        self.graph_manager.save_graph(graph)
        
        # 输出统计
        print(f"""📊 [LOG] 任务完成统计:
  总步骤: {graph.metrics.total_steps}
  完成: {graph.metrics.completed_steps}
  失败: {graph.metrics.failed_steps}
  重试次数: {graph.metrics.retry_count}
  HITL中断: {graph.metrics.hitl_interruptions}
  耗时: {graph.metrics.elapsed_seconds:.2f}秒
  状态: {graph.status.value}""")

# ==================== CLI 入口 ====================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Orchestrator · 多轮规划循环引擎")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # orchestrate 命令
    orch_parser = subparsers.add_parser("orchestrate", help="启动编排")
    orch_parser.add_argument("--prompt", "-p", required=True, help="任务提示")
    orch_parser.add_argument("--agent", "-a", action="append", help="可用Agent（可多次）")
    
    # status 命令
    status_parser = subparsers.add_parser("status", help="查询状态")
    status_parser.add_argument("--session-id", required=True, help="会话ID")
    
    # list 命令
    list_parser = subparsers.add_parser("list", help="列出任务")
    
    args = parser.parse_args()
    
    orchestrator = Orchestrator()
    
    if args.command == "orchestrate":
        # 构建 Agent 池
        agent_pool = {}
        if args.agent:
            for agent_id in args.agent:
                agent_pool[agent_id] = AgentSpec(agent_id=agent_id, capabilities=["general"])
        else:
            # 默认 Agent
            agent_pool = {
                "backend_dev": AgentSpec(agent_id="backend_dev", capabilities=["backend", "database"]),
                "security_expert": AgentSpec(agent_id="security_expert", capabilities=["security", "encryption"])
            }
        
        # 执行编排
        result = asyncio.run(orchestrator.orchestrate(args.prompt, agent_pool))
        
        print(f"\n🎉 编排完成 ({result.status.value})")
        print(f"会话ID: {result.session_id}")
        
        if "final_summary" in result.shared_context:
            print("\n📋 任务摘要:")
            summary = result.shared_context["final_summary"]
            for step in summary["steps"]:
                print(f"  - {step['step_id']}: {step['output'].get('content', '')[:50]}...")
    
    elif args.command == "status":
        graph = orchestrator.graph_manager.load_graph(args.session_id)
        if graph:
            print(json.dumps({
                "session_id": graph.session_id,
                "status": graph.status.value,
                "root_prompt": graph.root_prompt,
                "metrics": {
                    "total_steps": graph.metrics.total_steps,
                    "completed_steps": graph.metrics.completed_steps,
                    "failed_steps": graph.metrics.failed_steps,
                    "elapsed_seconds": graph.metrics.elapsed_seconds
                },
                "steps": [{
                    "step_id": s.step_id,
                    "status": s.status.value,
                    "description": s.description,
                    "assigned_agent": s.assigned_agent
                } for s in graph.plan]
            }, ensure_ascii=False, indent=2))
        else:
            print(f"未找到会话: {args.session_id}")
    
    elif args.command == "list":
        # 简单列出所有会话（需要在DB中查询）
        import sqlite3
        conn = sqlite3.connect("ac_platform.db")
        cursor = conn.cursor()
        cursor.execute('SELECT session_id, status, root_prompt, created_at FROM task_graphs ORDER BY created_at DESC')
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "session_id": row[0],
                "status": row[1],
                "root_prompt": row[2][:50] + "..." if len(row[2]) > 50 else row[2],
                "created_at": row[3]
            })
        
        conn.close()
        print(json.dumps(sessions, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()