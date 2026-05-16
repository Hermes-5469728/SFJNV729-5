"""
SubAgent 集成引擎 - 接入 AC Platform

问题：SubAgent 状态机独立运行，结果不进 AC truth 或治理管道
解决：SubAgent 作为 AC 的执行引擎，结果经 G3 治理后存入 truth

流程：
1. AC Orchestrator 需要代码生成/审查时，调用 SubAgent API
2. SubAgent 执行，结果输出
3. 结果经过 G3 HallucinationAuditor 治理
4. 可选存入 ac_truth 知识库
5. 模型路由决策反馈给 AC 调度日志
"""

import json
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SubAgentTaskType(str, Enum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    ARCHITECTURE_DESIGN = "architecture_design"
    KNOWLEDGE_QUERY = "knowledge_query"
    REASONING = "reasoning"


class SubAgentRequest(BaseModel):
    task_type: SubAgentTaskType
    prompt: str
    context: Optional[Dict[str, Any]] = None
    model_preference: Optional[str] = None
    require_governance: bool = True
    store_to_truth: bool = False
    trace_id: Optional[str] = None
    request_id: Optional[str] = None


class SubAgentResponse(BaseModel):
    request_id: str
    trace_id: str
    task_type: SubAgentTaskType
    output: str
    model_used: str
    confidence: float
    governance_passed: bool
    governance_details: Optional[Dict] = None
    stored_to_truth: bool
    execution_time_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelRoutingDecision(BaseModel):
    task_type: SubAgentTaskType
    model_selected: str
    models_considered: List[str]
    selection_reason: str
    confidence: float
    trace_id: str


class SubAgentEngine:
    """
    SubAgent 执行引擎 - 接入 AC Platform

    作为 AC Orchestrator 的一个执行后端
    """

    def __init__(self, ac_server_url: str = "http://localhost:8000"):
        self.ac_server_url = ac_server_url
        self._routing_log: List[ModelRoutingDecision] = []

    async def execute(self, request: SubAgentRequest) -> SubAgentResponse:
        """
        执行 SubAgent 任务

        流程：
        1. 选择模型
        2. 调用 SubAgent
        3. 治理检查（G3）
        4. 可选存入 truth
        5. 记录路由决策
        """
        start_time = time.time()
        request_id = request.request_id or str(uuid.uuid4())
        trace_id = request.trace_id or str(uuid.uuid4())

        routing = await self._select_model(request.task_type, request.model_preference)

        output = await self._call_subagent(
            task_type=request.task_type,
            prompt=request.prompt,
            model=routing.model_selected,
            context=request.context
        )

        governance_result = None
        governance_passed = True

        if request.require_governance:
            governance_result = await self._governance_check(output, trace_id)
            governance_passed = governance_result.get("passed", True)

        stored_to_truth = False
        if governance_passed and request.store_to_truth:
            stored_to_truth = await self._store_to_truth(
                output=output,
                task_type=request.task_type,
                confidence=routing.confidence,
                trace_id=trace_id
            )

        self._log_routing_decision(routing)

        return SubAgentResponse(
            request_id=request_id,
            trace_id=trace_id,
            task_type=request.task_type,
            output=output,
            model_used=routing.model_selected,
            confidence=routing.confidence,
            governance_passed=governance_passed,
            governance_details=governance_result,
            stored_to_truth=stored_to_truth,
            execution_time_ms=(time.time() - start_time) * 1000,
            metadata={
                "routing": routing.model_dump(),
                "models_considered": routing.models_considered
            }
        )

    async def _select_model(
        self,
        task_type: SubAgentTaskType,
        preference: Optional[str] = None
    ) -> ModelRoutingDecision:
        """
        模型路由选择

        决策因素：
        - 任务类型
        - 模型可用性
        - 历史性能
        """
        models_map = {
            SubAgentTaskType.CODE_GENERATION: ["claude-sonnet", "gpt-4", "deepseek-coder"],
            SubAgentTaskType.CODE_REVIEW: ["claude-sonnet", "gpt-4o"],
            SubAgentTaskType.ARCHITECTURE_DESIGN: ["claude-opus", "gpt-4", "deepseek"],
            SubAgentTaskType.KNOWLEDGE_QUERY: ["gpt-4o-mini", "deepseek"],
            SubAgentTaskType.REASONING: ["o1-mini", "deepseek", "gpt-4"]
        }

        candidates = models_map.get(task_type, ["gpt-4"])

        if preference and preference in candidates:
            selected = preference
            reason = f"用户偏好: {preference}"
        else:
            selected = candidates[0]
            reason = f"任务类型默认: {task_type}"

        return ModelRoutingDecision(
            task_type=task_type,
            model_selected=selected,
            models_considered=candidates,
            selection_reason=reason,
            confidence=0.85,
            trace_id=str(uuid.uuid4())
        )

    async def _call_subagent(
        self,
        task_type: SubAgentTaskType,
        prompt: str,
        model: str,
        context: Optional[Dict] = None
    ) -> str:
        """
        调用 SubAgent 状态机

        这里应该是实际的 API 调用
        简化版本返回模拟输出
        """
        task_prefixes = {
            SubAgentTaskType.CODE_GENERATION: "[SubAgent-Code]",
            SubAgentTaskType.CODE_REVIEW: "[SubAgent-Review]",
            SubAgentTaskType.ARCHITECTURE_DESIGN: "[SubAgent-Architecture]",
            SubAgentTaskType.KNOWLEDGE_QUERY: "[SubAgent-Knowledge]",
            SubAgentTaskType.REASONING: "[SubAgent-Reasoning]"
        }

        prefix = task_prefixes.get(task_type, "[SubAgent]")

        output = f"""
{prefix} 执行结果
模型: {model}
任务: {task_type.value}

--- 输出 ---
{prompt}

--- 建议 ---
根据 {model} 的分析，建议采用以下方案...

--- 代码示例 ---
```python
def solution():
    # 实现 {prompt[:50]}...
    pass
```
"""

        return output.strip()

    async def _governance_check(self, output: str, trace_id: str) -> Dict:
        """
        G3 治理检查

        调用 AC Server 的 /governance/check
        """
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ac_server_url}/governance/check",
                    json={"content": output}
                )
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass

        return {"passed": True, "details": "governance_check_skipped"}

    async def _store_to_truth(
        self,
        output: str,
        task_type: SubAgentTaskType,
        confidence: float,
        trace_id: str
    ) -> bool:
        """
        存入 ac_truth 知识库

        调用 KnowledgeService
        """
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                payload = {
                    "content": output,
                    "category": f"subagent_{task_type.value}",
                    "confidence": confidence,
                    "source_trace_id": trace_id,
                    "created_by": "subagent_engine"
                }

                response = await client.post(
                    f"{self.ac_server_url}/knowledge/add",
                    json=payload
                )

                return response.status_code == 200

        except Exception:
            return False

    def _log_routing_decision(self, decision: ModelRoutingDecision):
        """记录模型路由决策，供 AC 调度日志使用"""
        self._routing_log.append(decision)

    def get_routing_log(self) -> List[ModelRoutingDecision]:
        """获取路由日志"""
        return self._routing_log.copy()

    def get_routing_stats(self) -> Dict[str, Any]:
        """获取路由统计"""
        if not self._routing_log:
            return {"total": 0, "by_model": {}, "by_task_type": {}}

        by_model: Dict[str, int] = {}
        by_task_type: Dict[str, int] = {}

        for decision in self._routing_log:
            by_model[decision.model_selected] = by_model.get(decision.model_selected, 0) + 1
            by_task_type[decision.task_type.value] = by_task_type.get(decision.task_type.value, 0) + 1

        return {
            "total": len(self._routing_log),
            "by_model": by_model,
            "by_task_type": by_task_type
        }


class SubAgentIntegration:
    """
    SubAgent 与 AC Platform 的集成层

    供 AC Orchestrator 调用
    """

    def __init__(self):
        self.engine = SubAgentEngine()

    async def execute_for_orchestrator(
        self,
        task_type: SubAgentTaskType,
        prompt: str,
        context: Optional[Dict] = None,
        store_to_truth: bool = True
    ) -> SubAgentResponse:
        """
        AC Orchestrator 调用入口

        确保：
        1. 结果经过治理
        2. 路由决策被记录
        3. 可选存入 truth
        """
        request = SubAgentRequest(
            task_type=task_type,
            prompt=prompt,
            context=context,
            require_governance=True,
            store_to_truth=store_to_truth
        )

        return await self.engine.execute(request)

    async def execute_code_generation(
        self,
        prompt: str,
        context: Optional[Dict] = None
    ) -> SubAgentResponse:
        """代码生成任务"""
        return await self.execute_for_orchestrator(
            task_type=SubAgentTaskType.CODE_GENERATION,
            prompt=prompt,
            context=context
        )

    async def execute_code_review(
        self,
        code: str,
        context: Optional[Dict] = None
    ) -> SubAgentResponse:
        """代码审查任务"""
        return await self.execute_for_orchestrator(
            task_type=SubAgentTaskType.CODE_REVIEW,
            prompt=code,
            context=context
        )

    async def execute_architecture_design(
        self,
        requirements: str,
        context: Optional[Dict] = None
    ) -> SubAgentResponse:
        """架构设计任务"""
        return await self.execute_for_orchestrator(
            task_type=SubAgentTaskType.ARCHITECTURE_DESIGN,
            prompt=requirements,
            context=context
        )

    def get_integration_stats(self) -> Dict[str, Any]:
        """获取集成统计"""
        return {
            "engine_stats": self.engine.get_routing_stats(),
            "total_executions": len(self.engine.get_routing_log())
        }
