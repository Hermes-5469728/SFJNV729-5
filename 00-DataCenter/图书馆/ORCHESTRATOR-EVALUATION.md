# Orchestrator 顶级评估方案

> 基于 24 个考察项目的工业级标准评估体系

---

## 📊 评估总览

| 维度 | 考察项目数 | 当前得分 | 目标得分 | 完成度 |
|------|-----------|---------|---------|--------|
| 一、编排与认知核心 | 3 | 1.5/3 | 3 | 50% |
| 二、执行与工具链 | 3 | 1/3 | 3 | 33% |
| 三、治理与质量控制 | 3 | 2/3 | 3 | 67% |
| 四、人机交互 | 3 | 2/3 | 3 | 67% |
| 五、记忆与进化 | 2 | 0.5/2 | 2 | 25% |
| 六、单人效能指标 | 2 | 0/2 | 2 | 0% |
| **总计** | **16** | **7/18** | **18** | **39%** |

---

## 🧠 维度一：编排与认知核心

### 1.1 任务拆解

**当前实现：**
```python
# orchestrator.py:293-326
async def _manual_plan(self, graph: TaskGraph):
    """手动构图（演示用，后续替换为 LLM 自动拆解）"""
    # 基于关键词匹配生成步骤
    prompt = graph.root_prompt.lower()
    
    if "登录" in prompt or "login" in prompt:
        steps = [
            PlanStep(step_id="step_001", description="设计用户登录表结构", ...),
            PlanStep(step_id="step_002", description="实现密码加密与验证逻辑", ...),
            # ... 硬编码的步骤定义
        ]
```

**评估：**
- ✅ **有依赖树意识**：步骤间存在 `depends_on` 关系
- ❌ **硬编码规则**：基于关键词匹配，非智能拆解
- ❌ **无递归能力**：无法处理复杂嵌套任务
- ❌ **无反问机制**：遇到模糊需求不会主动澄清

**顶级标准：**
```python
# 目标实现：递归式任务树生成
class TaskDecomposer:
    async def decompose(self, goal: str) -> TaskTree:
        # 1. 识别未知信息
        unknowns = await self._identify_unknowns(goal)
        if unknowns:
            return ClarificationRequest(unknowns)
        
        # 2. 递归拆解为 DAG
        tree = await self._recursive_decompose(goal, depth=0)
        
        # 3. 识别并行路径
        parallel_groups = self._identify_parallel_paths(tree)
        
        return TaskTree(root=goal, nodes=tree, parallel_groups=parallel_groups)
    
    async def _recursive_decompose(self, goal: str, depth: int) -> List[SubTask]:
        if depth > MAX_DEPTH or self._is_atomic(goal):
            return [AtomicTask(goal)]
        
        # 调用 LLM 进行智能拆解
        prompt = f"""
        将以下目标拆解为可执行的子任务（有向无环图）：
        目标：{goal}
        
        要求：
        1. 每个子任务必须是原子操作
        2. 标注子任务间的依赖关系
        3. 识别可并行执行的子任务组
        4. 如果信息不足，列出需要澄清的问题
        """
        # ...
```

**改进路径：**
1. 接入 LLM 进行智能拆解（Iteration 3）
2. 实现未知信息识别与反问机制
3. 支持递归拆解（最大深度 3-5 层）
4. 自动识别并行执行路径

---

### 1.2 上下文管理

**当前实现：**
```python
# orchestrator.py:78-82
@dataclass
class TaskGraph:
    # ...
    shared_context: Dict[str, Any] = field(default_factory=dict)
    # 所有信息都堆在这里，无分离机制
```

**评估：**
- ❌ **无 RAG 检索**：所有上下文都在内存中
- ❌ **无长期记忆**：任务结束后上下文丢失
- ❌ **无窗口管理**：可能超出 Token 限制

**顶级标准：**
```python
class ContextManager:
    def __init__(self):
        self.short_term = TaskContext()  # 当前任务状态
        self.long_term = VectorMemory()   # 向量数据库
        self.working_set = set()          # 当前激活的上下文
    
    async def inject_context(self, step: PlanStep) -> str:
        """动态注入上下文"""
        # 1. 检索相关记忆
        relevant = await self.long_term.retrieve(
            query=step.description,
            top_k=5
        )
        
        # 2. 过滤短期记忆
        short_term = self.short_term.get_relevant(step)
        
        # 3. 构建精简上下文
        context = self._build_context(relevant, short_term)
        
        # 4. 检查 Token 限制
        if self._exceeds_limit(context):
            context = self._compress_context(context)
        
        return context
    
    async def persist_memory(self, experience: Experience):
        """将经验存入长期记忆"""
        await self.long_term.store(
            content=experience.summary,
            metadata={
                "task_type": experience.type,
                "success": experience.success,
                "solution": experience.solution
            }
        )
```

**改进路径：**
1. 引入向量数据库（ChromaDB/Qdrant）
2. 实现长短记忆分离
3. 添加上下文压缩机制
4. 支持基于 RAG 的相关记忆检索

---

### 1.3 多模态路由

**当前实现：**
```python
# orchestrator.py:258-263
agent_pool = {
    "backend_dev": AgentSpec(agent_id="backend_dev", capabilities=["backend", "database"]),
    "security_expert": AgentSpec(agent_id="security_expert", capabilities=["security", "encryption"]),
    # 固定 Agent 池，无动态路由
}
```

**评估：**
- ✅ **有 Agent 分工意识**：不同 Agent 有不同 capabilities
- ❌ **无模型路由**：未考虑底层 LLM 模型选择
- ❌ **无成本优化**：不考虑 Token 成本/速度平衡

**顶级标准：**
```python
class ModelRouter:
    def __init__(self):
        self.model_registry = {
            "claude-35-sonnet": {
                "strengths": ["code", "reasoning", "security"],
                "cost_per_1k": 0.003,
                "speed": "fast",
                "context_window": 200000
            },
            "gpt-4o": {
                "strengths": ["creative", "multimodal"],
                "cost_per_1k": 0.005,
                "speed": "medium",
                "context_window": 128000
            },
            "deepseek-v3": {
                "strengths": ["logic", "math", "chinese"],
                "cost_per_1k": 0.0005,
                "speed": "very_fast",
                "context_window": 128000
            }
        }
    
    def select_model(self, task: SubTask, budget: float = None) -> str:
        """基于任务类型和预算选择最优模型"""
        # 1. 分析任务需求
        requirements = self._analyze_task(task)
        
        # 2. 过滤候选模型
        candidates = [
            (model_id, spec)
            for model_id, spec in self.model_registry.items()
            if self._matches_requirements(spec, requirements)
        ]
        
        # 3. 成本 - 速度优化
        if budget:
            candidates = [(m, s) for m, s in candidates if s["cost_per_1k"] <= budget]
        
        # 4. 选择最优（加权评分）
        best = max(candidates, key=lambda x: self._score(x[1], requirements))
        return best[0]
```

**改进路径：**
1. 建立模型注册表（能力/成本/速度）
2. 实现基于任务类型的自动路由
3. 添加成本预算控制
4. 支持降级策略（主模型不可用时切换备用）

---

## ⚙️ 维度二：执行与工具链

### 2.1 工具定义

**当前实现：**
```python
# cli.py 中的命令定义
parser.add_argument("--task-id", required=True, help="任务 ID")
parser.add_argument("--type", required=True, choices=["url", "database", "file"])
# 参数验证依赖 argparse，无严格 Schema
```

**评估：**
- ✅ **有参数验证**：argparse 提供基础验证
- ❌ **无 Pydantic Schema**：缺少严格的类型约束
- ❌ **无自动修正**：格式错误直接失败

**顶级标准：**
```python
from pydantic import BaseModel, Field, validator

class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    
    class Config:
        arbitrary_types_allowed = True

class VerifyTool(ToolDefinition):
    class Input(BaseModel):
        task_id: str = Field(..., description="任务 ID", min_length=1)
        type: str = Field(..., description="验证类型", pattern="^(url|database|file)$")
        params: Dict[str, Any] = Field(..., description="验证参数")
        
        @validator('params')
        def validate_params(cls, v, values):
            if values['type'] == 'url' and 'url' not in v:
                raise ValueError("URL 验证必须提供 url 参数")
            if values['type'] == 'database' and 'query' not in v:
                raise ValueError("数据库验证必须提供 query 参数")
            return v
    
    class Output(BaseModel):
        success: bool
        evidence: Dict[str, Any]
        latency_ms: float
        error: Optional[str] = None

class ToolExecutor:
    def __init__(self, tools: List[ToolDefinition]):
        self.tools = {t.name: t for t in tools}
        self.retry_policy = ExponentialBackoff(max_retries=3)
    
    async def execute(self, tool_name: str, input_data: Dict) -> Dict:
        """执行工具，带自动修正循环"""
        tool = self.tools[tool_name]
        
        # 1. 验证输入 Schema
        try:
            validated_input = tool.Input(**input_data)
        except ValidationError as e:
            # 2. 自动修正尝试
            corrected = await self._auto_correct(input_data, e)
            validated_input = tool.Input(**corrected)
        
        # 3. 执行工具
        result = await self._call_tool(tool, validated_input)
        
        # 4. 验证输出 Schema
        try:
            return tool.Output(**result).dict()
        except ValidationError:
            # 输出格式错误，记录但返回
            return {"success": False, "error": "Invalid output format"}
```

**改进路径：**
1. 为所有 CLI 命令定义 Pydantic Input/Output Schema
2. 实现自动修正循环（格式错误时尝试修复）
3. 添加工具注册机制
4. 支持工具版本管理

---

### 2.2 环境隔离

**当前实现：**
```python
# 直接在当前进程执行
result = await self._simulate_dispatch(graph, step)
# 无沙箱、无容器化
```

**评估：**
- ❌ **无沙箱**：任务直接在主环境运行
- ❌ **无隔离**：可能污染全局状态
- ❌ **无清理机制**：临时文件可能残留

**顶级标准：**
```python
import docker
import tempfile
import shutil
from pathlib import Path

class SandboxExecutor:
    def __init__(self):
        self.docker_client = docker.from_client()
        self.sandbox_dir = Path("/tmp/ac_sandboxes")
        self.sandbox_dir.mkdir(exist_ok=True)
    
    async def execute_in_sandbox(self, step: PlanStep) -> ExecutionResult:
        """在隔离环境中执行步骤"""
        # 1. 创建临时工作目录
        work_dir = self.sandbox_dir / step.step_id
        work_dir.mkdir(exist_ok=True)
        
        try:
            # 2. 启动 Docker 容器
            container = self.docker_client.containers.run(
                image="python:3.10-slim",
                command="tail -f /dev/null",
                working_dir="/workspace",
                volumes={str(work_dir): {"bind": "/workspace", "mode": "rw"}},
                network_disabled=False,
                detach=True
            )
            
            # 3. 在容器中执行命令
            result = container.exec_run(
                cmd=self._build_command(step),
                workdir="/workspace"
            )
            
            # 4. 捕获输出和错误
            return ExecutionResult(
                stdout=result.output.decode(),
                exit_code=result.exit_code,
                duration=result.duration
            )
            
        finally:
            # 5. 清理容器和工作目录
            container.stop()
            container.remove()
            shutil.rmtree(work_dir)
```

**改进路径：**
1. 集成 Docker SDK 实现容器化执行
2. 为每个任务创建独立工作目录
3. 执行后自动清理资源
4. 支持资源限制（CPU/内存）

---

### 2.3 执行反馈

**当前实现：**
```python
# orchestrator.py:497-501
async def _simulate_dispatch(self, graph: TaskGraph, step: PlanStep) -> Dict[str, Any]:
    """模拟 dispatch 调用（实际应接入 real dispatch）"""
    await asyncio.sleep(1)  # 模拟执行时间
    
    # 模拟成功执行
    return {
        "success": True,
        "output": {"content": f"Step {step.step_id} executed successfully"}
    }
```

**评估：**
- ❌ **无错误分析**：不捕获退出码、资源占用
- ❌ **无自我修复**：遇到错误直接失败
- ❌ **无带外信号**：只捕获 stdout

**顶级标准：**
```python
class ExecutionMonitor:
    def __init__(self):
        self.metrics_collector = MetricsCollector()
    
    async def execute_with_monitoring(self, command: str) -> ExecutionResult:
        """带完整监控的执行"""
        start_time = time.time()
        
        try:
            # 1. 执行命令
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300
            )
            
            # 2. 收集指标
            result = ExecutionResult(
                stdout=stdout.decode(),
                stderr=stderr.decode(),
                exit_code=process.returncode,
                duration=time.time() - start_time,
                memory_usage=self._get_memory_usage(process.pid)
            )
            
            # 3. 错误分析与自我修复
            if result.exit_code != 0:
                repair_suggestion = await self._analyze_error(stderr.decode())
                if repair_suggestion:
                    # 尝试修复命令
                    return await self.execute_with_monitoring(repair_suggestion)
            
            return result
            
        except asyncio.TimeoutError:
            return ExecutionResult(
                error="Timeout",
                exit_code=-1,
                duration=300
            )
    
    async def _analyze_error(self, error_log: str) -> Optional[str]:
        """分析错误日志，返回修复建议"""
        # 使用 LLM 分析错误
        patterns = {
            "command not found": self._handle_command_not_found,
            "permission denied": self._handle_permission_error,
            "no space left": self._handle_disk_full,
        }
        
        for pattern, handler in patterns.items():
            if pattern in error_log.lower():
                return await handler(error_log)
        
        return None
```

**改进路径：**
1. 捕获完整执行指标（退出码、耗时、资源占用）
2. 实现错误模式识别
3. 添加自动修复循环
4. 支持超时控制

---

## 🛡️ 维度三：治理与质量控制

### 3.1 状态机管理

**当前实现：**
```python
# orchestrator.py:28-42
class TaskState(Enum):
    """任务状态（13 态）"""
    CREATED = "created"
    QUEUED = "queued"
    PLANNING = "planning"
    PLANNED = "planned"
    EXECUTING = "executing"
    BLOCKED = "blocked"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    REJECTED = "rejected"
    RETRYING = "retrying"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    COMPLETED = "completed"
```

**评估：**
- ✅ **完整的 13 态定义**：覆盖全生命周期
- ✅ **状态流转逻辑**：有明确的转换规则
- ⚠️ **部分状态未实现**：如 ROLLING_BACK 的实际清理逻辑

**顶级标准：**
```python
class StateMachine:
    """严格的状态机，防止非法状态转换"""
    
    TRANSITIONS = {
        TaskState.CREATED: [TaskState.QUEUED, TaskState.FAILED],
        TaskState.QUEUED: [TaskState.EXECUTING, TaskState.FAILED],
        TaskState.EXECUTING: [TaskState.VERIFYING, TaskState.FAILED, TaskState.BLOCKED],
        TaskState.VERIFYING: [TaskState.VERIFIED, TaskState.REJECTED, TaskState.FAILED],
        TaskState.VERIFIED: [TaskState.COMPLETED],
        TaskState.REJECTED: [TaskState.RETRYING, TaskState.FAILED],
        TaskState.RETRYING: [TaskState.QUEUED, TaskState.FAILED],
        TaskState.BLOCKED: [TaskState.QUEUED, TaskState.FAILED],
        TaskState.FAILED: [TaskState.ROLLING_BACK],
        TaskState.ROLLING_BACK: [TaskState.ROLLED_BACK],
        # 终态
        TaskState.COMPLETED: [],
        TaskState.ROLLED_BACK: [],
    }
    
    def transition(self, current: TaskState, next_state: TaskState) -> bool:
        """执行状态转换，防止非法转换"""
        allowed = self.TRANSITIONS.get(current, [])
        if next_state not in allowed:
            raise InvalidStateTransition(current, next_state)
        return True
```

**改进路径：**
1. 实现严格的状态转换验证
2. 完善回滚状态的实际清理逻辑
3. 添加状态转换日志
4. 支持状态恢复（从失败中恢复）

---

### 3.2 质量门禁

**当前实现：**
```python
# orchestrator.py:529-547
async def _verify_step(self, graph: TaskGraph, step: PlanStep):
    """VERIFY 阶段：验证步骤"""
    step.status = TaskState.VERIFYING
    print(f"🔍 [VERIFY] 验证步骤：{step.step_id}")
    
    # 端到端验证
    verified = await self.verification_engine.verify(step)
    
    if verified:
        # 评分
        score = self.scoring_agent.score(step.output, step)
        # ...
```

**评估：**
- ✅ **有端到端验证**：复用 collaborative_governor
- ✅ **有评分机制**：低于阈值打回重做
- ⚠️ **验证类型有限**：主要支持 file/database/url

**顶级标准：**
```python
class QualityGate:
    """多层质量门禁"""
    
    async def verify(self, step: PlanStep) -> VerificationResult:
        """完整的质量检查流程"""
        results = []
        
        # L1: 格式验证
        results.append(await self._validate_format(step))
        
        # L2: 静态检查
        if step.output.get("type") == "code":
            results.append(await self._lint_code(step.output["content"]))
        
        # L3: 单元测试
        if step.verification_spec.get("require_tests"):
            results.append(await self._run_tests(step))
        
        # L4: 集成测试
        if step.verification_spec.get("require_integration"):
            results.append(await self._integration_test(step))
        
        # L5: 健康检查
        if step.verification_spec.get("health_check"):
            results.append(await self._health_check(step))
        
        # 综合评分
        passed = all(r.passed for r in results)
        score = sum(r.score for r in results) / len(results)
        
        return VerificationResult(
            passed=passed,
            score=score,
            details=results
        )
```

**改进路径：**
1. 实现分层质量检查（L1-L5）
2. 添加代码静态分析（Ruff/mypy）
3. 支持自动运行单元测试
4. 集成健康检查（启动服务验证）

---

### 3.3 熔断与降级

**当前实现：**
```python
# guard.py 中的 HeartbeatReporter
class HeartbeatReporter:
    def __init__(self):
        self.cb = CircuitBreaker()  # 简单的熔断器
    
    def can_proceed(self) -> bool:
        return self.cb.state != "open"
```

**评估：**
- ✅ **有熔断器概念**：防止连续失败
- ⚠️ **降级策略简单**：仅打开/关闭，无中间状态
- ❌ **无备用路由**：熔断后无替代方案

**顶级标准：**
```python
class AdvancedCircuitBreaker:
    """高级熔断器，支持降级和半开状态"""
    
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = "closed"  # closed/half-open/open
        self.failure_count = 0
        self.last_failure_time = None
        self.fallback_strategy = None
    
    def call(self, func, fallback=None, *args, **kwargs):
        """带降级的调用"""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
            elif fallback:
                return fallback(*args, **kwargs)  # 降级执行
            else:
                raise CircuitBreakerOpen("熔断器打开")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            
            if fallback:
                return fallback(*args, **kwargs)
            raise

class ModelFallbackRouter:
    """模型降级路由"""
    
    def __init__(self):
        self.primary = "claude-35-sonnet"
        self.fallbacks = ["gpt-4o", "deepseek-v3", "gpt-3.5-turbo"]
        self.breakers = {model: AdvancedCircuitBreaker() for model in [self.primary] + self.fallbacks}
    
    def select_with_fallback(self, task: SubTask) -> str:
        """选择模型，主模型不可用时自动降级"""
        models_to_try = [self.primary] + self.fallbacks
        
        for model in models_to_try:
            try:
                return self.breakers[model].call(
                    lambda: self._check_model_available(model),
                    fallback=None
                )
                return model
            except CircuitBreakerOpen:
                continue
        
        raise RuntimeError("所有模型都不可用")
```

**改进路径：**
1. 实现半开状态（自动恢复尝试）
2. 添加降级策略（备用模型/简化流程）
3. 支持指数退避重试
4. 为每个模型/工具独立熔断器

---

## 🤝 维度四：人机交互

### 4.1 干预模式

**当前实现：**
```python
# orchestrator.py:168-186
class HITLManager:
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
        # ...
```

**评估：**
- ✅ **支持三种 HITL 类型**：CONFIRM/CHOOSE/REVIEW
- ✅ **有超时控制**：默认 300 秒
- ⚠️ **仅 CLI 交互**：无 Web 界面
- ❌ **无异步批准**：必须实时响应

**顶级标准：**
```python
class AsyncHITLManager:
    """异步人在回路管理器"""
    
    def __init__(self):
        self.pending_requests = {}
        self.notification_channels = ["cli", "webhook", "email"]
    
    async def request_approval(self, request: HITLRequest) -> str:
        """发送审批请求，支持多种通知渠道"""
        # 1. 生成审批链接
        approval_url = f"https://ac-dashboard.local/approve/{request.request_id}"
        
        # 2. 发送通知
        await self._notify(request, approval_url)
        
        # 3. 等待异步响应（轮询或 webhook）
        while True:
            status = await self._check_status(request.request_id)
            if status:
                return status
            await asyncio.sleep(5)
    
    async def _notify(self, request: HITLRequest, url: str):
        """多渠道通知"""
        # CLI
        print(f"📝 [HITL] {request.prompt}\n审批链接：{url}")
        
        # Webhook（如钉钉/飞书）
        if "webhook" in self.notification_channels:
            await self._send_webhook(request, url)
        
        # Email
        if "email" in self.notification_channels:
            await self._send_email(request, url)
```

**改进路径：**
1. 实现 Web Dashboard 查看审批请求
2. 支持异步通知（钉钉/飞书/邮件）
3. 添加审批链接（点击即可批准）
4. 支持批量审批

---

### 4.2 可观测性

**当前实现：**
```python
# orchestrator.py:579-591
async def _log_phase(self, graph: TaskGraph):
    """LOG 阶段：持久化经验"""
    print(f"🔄 [LOG] 记录任务图")
    
    # 保存到数据库
    self.graph_manager.save_graph(graph)
    
    # 输出统计
    print(f"""📊 [LOG] 任务完成统计:
  总步骤：{graph.metrics.total_steps}
  完成：{graph.metrics.completed_steps}
  ...""")
```

**评估：**
- ✅ **有基础指标统计**
- ✅ **持久化到数据库**
- ❌ **无实时可视化**：只能看文本日志
- ❌ **无进度预测**：不知道剩余时间

**顶级标准：**
```python
class RealTimeDashboard:
    """实时可视化仪表盘"""
    
    def __init__(self):
        self.ws_clients = []  # WebSocket 客户端
        self.metrics_stream = asyncio.Queue()
    
    async def start_server(self):
        """启动 WebSocket 服务器"""
        async with websockets.serve(self._handle_client, "localhost", 8765):
            await asyncio.Future()  # 永久运行
    
    async def broadcast(self, event: Dict):
        """广播实时事件"""
        message = json.dumps(event)
        for client in self.ws_clients:
            await client.send(message)
    
    def build_task_graph(self, graph: TaskGraph) -> Dict:
        """构建任务图可视化数据"""
        return {
            "type": "task_graph_update",
            "data": {
                "session_id": graph.session_id,
                "status": graph.status.value,
                "nodes": [
                    {
                        "id": step.step_id,
                        "label": step.description[:30],
                        "status": step.status.value,
                        "agent": step.assigned_agent,
                        "progress": self._calculate_progress(step)
                    }
                    for step in graph.plan
                ],
                "edges": [
                    {"from": dep, "to": step.step_id}
                    for step in graph.plan
                    for dep in step.depends_on
                ],
                "metrics": {
                    "total": graph.metrics.total_steps,
                    "completed": graph.metrics.completed_steps,
                    "failed": graph.metrics.failed_steps,
                    "elapsed": graph.metrics.elapsed_seconds,
                    "eta": self._estimate_remaining_time(graph)
                }
            }
        }
```

**改进路径：**
1. 实现 WebSocket 实时推送
2. 构建前端 Dashboard（React/Vue）
3. 显示任务拓扑图进度
4. 添加 ETA（预计剩余时间）

---

### 4.3 意图对齐

**当前实现：**
```python
# orchestrator.py:233-243
# HITL: 用户确认计划
plan_summary = "\n".join([
    f"{i+1}. [{s.assigned_agent}] {s.description}"
    for i, s in enumerate(graph.plan)
])

hitl_request = self.hitl_manager.create_request(
    HITLType.CONFIRM,
    f"计划已生成，共 {len(graph.plan)} 个步骤:\n{plan_summary}\n\n确认执行此计划？"
)
```

**评估：**
- ✅ **有计划确认机制**：执行前用户确认
- ⚠️ **确认信息简单**：只有步骤列表
- ❌ **无修改支持**：只能 approve/reject

**顶级标准：**
```python
class PlanNegotiator:
    """计划协商器"""
    
    async def present_plan(self, graph: TaskGraph) -> PlanDecision:
        """展示计划，支持修改"""
        # 1. 生成详细计划书
        plan_doc = await self._generate_plan_document(graph)
        
        # 2. 展示关键信息
        print(f"""
📋 执行计划书

目标：{graph.root_prompt}

步骤概览:
{self._render_plan_tree(graph.plan)}

预计耗时：{self._estimate_duration(graph)}
预计成本：${self._estimate_cost(graph)}

风险点:
{self._identify_risks(graph)}

---
选项:
1. ✅ 确认执行
2. ✏️ 修改计划（指定步骤）
3. ❌ 取消执行
4. 💬 询问细节
""")
        
        # 3. 处理用户反馈
        choice = await self._get_user_input()
        
        if choice == "modify":
            return await self._handle_modification(graph)
        elif choice == "ask":
            return await self._answer_questions(graph)
        
        return PlanDecision(approved=(choice == "confirm"))
```

**改进路径：**
1. 生成详细计划书（含成本/风险）
2. 支持步骤级别的修改
3. 添加问答环节（澄清疑问）
4. 可视化展示依赖关系

---

## 📚 维度五：记忆与进化

### 5.1 经验沉淀

**当前实现：**
```python
# orchestrator.py:579
# 保存到数据库
self.graph_manager.save_graph(graph)
# 但无经验提取和检索机制
```

**评估：**
- ✅ **有持久化**：任务图存入 SQLite
- ❌ **无经验提取**：未从成功/失败中提取模式
- ❌ **无检索机制**：下次遇到同样问题还会犯错

**顶级标准：**
```python
class ExperienceDatabase:
    """经验数据库（向量检索）"""
    
    def __init__(self):
        self.vector_db = ChromaDB(collection="experiences")
        self.relational_db = SQLiteDB("ac_truth.db")
    
    async def store_experience(self, experience: Experience):
        """存储经验"""
        # 1. 提取关键信息
        embedding_text = f"""
        任务类型：{experience.task_type}
        目标：{experience.goal}
        失败原因：{experience.failure_reason}
        解决方案：{experience.solution}
        """
        
        # 2. 生成向量嵌入
        embedding = await self._generate_embedding(embedding_text)
        
        # 3. 存储到向量数据库
        self.vector_db.add(
            text=experience.summary,
            embedding=embedding,
            metadata={
                "task_type": experience.task_type,
                "success": experience.success,
                "duration": experience.duration,
                "timestamp": time.time()
            }
        )
        
        # 4. 存储详细记录到关系数据库
        self.relational_db.insert("experiences", experience.to_dict())
    
    async def retrieve_similar(self, task: str, top_k=3) -> List[Experience]:
        """检索相似任务的经验"""
        # 1. 生成查询向量
        query_embedding = await self._generate_embedding(task)
        
        # 2. 向量检索
        results = self.vector_db.query(
            query_embedding=query_embedding,
            top_k=top_k,
            filter={"success": True}  # 只检索成功经验
        )
        
        # 3. 返回经验
        return [Experience.from_dict(r.metadata) for r in results]
```

**改进路径：**
1. 集成向量数据库（ChromaDB/Qdrant）
2. 实现经验提取（从任务图中总结）
3. 支持相似度检索
4. 优先检索成功经验

---

### 5.2 技能自学

**当前实现：**
```python
# 无技能自学机制
# 工具集是固定的
```

**评估：**
- ❌ **无技能发现**：无法识别重复模式
- ❌ **无工具生成**：不会自动创建新工具
- ❌ **无注册机制**：新工具无法加入工具库

**顶级标准：**
```python
class SkillLearner:
    """技能学习器"""
    
    def __init__(self):
        self.pattern_detector = PatternDetector()
        self.script_generator = ScriptGenerator()
        self.tool_registry = ToolRegistry()
    
    async def analyze_and_learn(self, execution_logs: List[ExecutionLog]):
        """分析执行日志，发现可固化的模式"""
        # 1. 检测重复模式
        patterns = self.pattern_detector.find_frequent_sequences(
            logs=execution_logs,
            min_support=3  # 至少出现 3 次
        )
        
        for pattern in patterns:
            # 2. 生成脚本
            script = await self.script_generator.generate(
                pattern=pattern,
                language="python"
            )
            
            # 3. 创建工具定义
            tool_def = ToolDefinition(
                name=f"auto_{pattern.name}",
                description=f"自动化工具：{pattern.description}",
                input_schema=pattern.input_schema,
                output_schema=pattern.output_schema
            )
            
            # 4. 注册工具
            self.tool_registry.register(tool_def, script)
            
            # 5. 通知用户
            await self._notify_new_tool(tool_def)
```

**改进路径：**
1. 实现模式检测（频繁序列挖掘）
2. 自动生成脚本（Shell/Python）
3. 工具自动注册
4. 用户确认后激活

---

## 📊 维度六：单人效能指标

### 6.1 无人值守率

**当前实现：**
```python
# 无自动化程度统计
# 需要人工确认每个计划
```

**评估：**
- ❌ **无指标追踪**：不统计人工干预次数
- ❌ **无自动化分级**：所有任务都需要确认
- ❌ **无信任机制**：无法根据历史表现提升自动化级别

**顶级标准：**
```python
class AutomationLevelManager:
    """自动化级别管理"""
    
    def __init__(self):
        self.trust_scores = {}  # 每个 Agent 的信任分数
        self.auto_levels = {}   # 每个任务类型的自动化级别
    
    def calculate_trust_score(self, agent_id: str) -> float:
        """计算 Agent 信任分数（0-100）"""
        recent_tasks = self._get_recent_tasks(agent_id, limit=20)
        
        if not recent_tasks:
            return 50.0  # 默认
        
        success_rate = sum(1 for t in recent_tasks if t.success) / len(recent_tasks)
        avg_score = sum(t.score for t in recent_tasks) / len(recent_tasks)
        no_intervention_rate = sum(1 for t in recent_tasks if not t.required_intervention) / len(recent_tasks)
        
        return (success_rate * 40 + avg_score * 30 + no_intervention_rate * 30)
    
    def determine_auto_level(self, task_type: str, agent_id: str) -> AutoLevel:
        """根据信任分数决定自动化级别"""
        trust_score = self.calculate_trust_score(agent_id)
        
        if trust_score >= 90:
            return AutoLevel.FULL_AUTO  # 完全自动，事后通知
        elif trust_score >= 70:
            return AutoLevel.AUTO_WITH_NOTIFY  # 自动执行，实时通知
        elif trust_score >= 50:
            return AutoLevel.CONFIRM_CRITICAL  # 只确认关键步骤
        else:
            return AutoLevel.MANUAL  # 完全手动
    
    async def execute_with_auto_level(self, task: Task, auto_level: AutoLevel):
        """根据自动化级别执行"""
        if auto_level == AutoLevel.FULL_AUTO:
            return await self._execute_and_notify(task)
        elif auto_level == AutoLevel.CONFIRM_CRITICAL:
            critical_steps = self._identify_critical_steps(task)
            for step in task.steps:
                if step in critical_steps:
                    await self._request_confirmation(step)
                await self._execute_step(step)
```

**改进路径：**
1. 定义自动化级别（FULL_AUTO/MANUAL 等）
2. 实现信任分数计算
3. 根据信任分数动态调整自动化级别
4. 统计无人值守率指标

---

### 6.2 恢复时间

**当前实现：**
```python
# orchestrator.py:559-577
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
        print(f"🔄 [ROLLBACK] 回滚步骤：{step.step_id}")
        await asyncio.sleep(0.5)  # 模拟回滚操作
        step.status = TaskState.ROLLED_BACK
```

**评估：**
- ✅ **有回滚概念**：按依赖逆序清理
- ⚠️ **回滚逻辑简单**：只是标记状态，无实际清理
- ❌ **无 Git 集成**：无法快速恢复到稳定版本
- ❌ **无沙箱清理**：临时文件可能残留

**顶级标准：**
```python
class RollbackEngine:
    """快速回滚引擎"""
    
    def __init__(self):
        self.git_client = GitClient()
        self.sandbox_manager = SandboxManager()
        self.db_client = DatabaseClient()
    
    async def rollback_to_checkpoint(self, session_id: str, checkpoint_id: str):
        """回滚到检查点"""
        start_time = time.time()
        
        try:
            # 1. 停止所有运行中的任务
            await self._stop_running_tasks(session_id)
            
            # 2. Git 回滚（代码变更）
            self.git_client.checkout(checkpoint_id)
            
            # 3. 数据库回滚
            await self.db_client.restore_snapshot(checkpoint_id)
            
            # 4. 清理沙箱
            await self.sandbox_manager.cleanup(session_id)
            
            # 5. 更新状态
            await self._mark_rolled_back(session_id, checkpoint_id)
            
            duration = time.time() - start_time
            
            # 6. 验证回滚成功
            if duration > 10:
                print(f"⚠️ 回滚耗时 {duration:.1f}秒，超过 10 秒目标")
            
            return RollbackResult(success=True, duration=duration)
            
        except Exception as e:
            return RollbackResult(success=False, error=str(e))
    
    async def auto_rollback_on_failure(self, step: PlanStep):
        """检测到破坏性错误时自动回滚"""
        # 1. 检测错误类型
        if self._is_destructive_error(step.error):
            # 2. 自动触发回滚
            latest_checkpoint = await self._get_latest_checkpoint(step.session_id)
            await self.rollback_to_checkpoint(step.session_id, latest_checkpoint)
            
            # 3. 通知用户
            await self._notify_rollback(step.session_id)
```

**改进路径：**
1. 集成 Git 操作（checkout/revert）
2. 实现数据库快照恢复
3. 沙箱自动清理
4. 目标：回滚时间 < 10 秒

---

## 📈 改进路线图

### Phase 1: 基础完善（1-2 周）
- [ ] 为所有 CLI 命令添加 Pydantic Schema
- [ ] 实现严格的状态转换验证
- [ ] 完善回滚逻辑（实际清理资源）
- [ ] 添加执行指标收集（退出码/耗时）

### Phase 2: 智能化升级（2-3 周）
- [ ] 接入 LLM 进行任务拆解（Iteration 3）
- [ ] 实现未知信息识别与反问
- [ ] 集成向量数据库（经验存储）
- [ ] 实现基于 RAG 的上下文注入

### Phase 3: 工业化（3-4 周）
- [ ] 实现 Docker 沙箱执行
- [ ] 添加多层质量门禁（Lint/测试）
- [ ] 实现高级熔断与降级
- [ ] 集成 Git 回滚机制

### Phase 4: 可观测性（4-5 周）
- [ ] 实现 WebSocket 实时推送
- [ ] 构建前端 Dashboard
- [ ] 添加 ETA 预测
- [ ] 实现多渠道通知（钉钉/飞书）

### Phase 5: 自动化进化（5-6 周）
- [ ] 实现信任分数系统
- [ ] 动态调整自动化级别
- [ ] 模式检测与工具自动生成
- [ ] 无人值守率 > 90%

---

## 🎯 顶级标准达成清单

当你看到以下场景时，说明系统已达到工业级：

- ✅ **任务图在控制台中生长**：实时看到节点状态流转、依赖关系
- ✅ **AI 会质疑模糊需求**："您提到的'登录模块'需要支持第三方登录吗？"
- ✅ **自动修复命令**：`apt install` 失败后自动尝试 `yum install`
- ✅ **90% 任务无需人工干预**：AI 独立完成编码→测试→部署
- ✅ **10 秒内回滚**：检测到破坏性错误自动恢复到稳定状态
- ✅ **越用越聪明**：上次犯的错这次自动避免，还学会了新工具

---

*评估方案 v1.0 · 基于 Atelier 架构原则 + 业界最佳实践*
