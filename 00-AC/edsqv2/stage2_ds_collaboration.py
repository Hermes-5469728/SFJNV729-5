"""
E/D/S/Q Architecture v2.0 - Stage 2: Dispatch + Orchestrator Collaboration
"""

import json
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass


# --- 1. Dispatch 模块 ---

class DispatchType(Enum):
    EXPERT = "expert"
    TOOL = "tool"


@dataclass
class DispatchTask:
    id: str
    input_text: str
    target: str
    dispatch_type: DispatchType
    result: Optional[str] = None
    completed: bool = False


class ExpertRegistry:
    """专家注册中心 - 对应 D 层"""
    
    def __init__(self):
        self.experts: Dict[str, Dict[str, Any]] = {}
    
    def register(self, name: str, handler: Callable, description: str, tags: List[str]):
        self.experts[name] = {
            "handler": handler,
            "description": description,
            "tags": tags,
            "registered_at": datetime.now().isoformat()
        }
    
    def find_expert(self, task: str) -> Optional[str]:
        """根据任务查找合适的专家"""
        task_lower = task.lower()
        for name, info in self.experts.items():
            if any(tag.lower() in task_lower for tag in info["tags"]):
                return name
        return list(self.experts.keys())[0] if self.experts else None


class Dispatcher:
    """调度器 - D 层核心"""
    
    def __init__(self, registry: ExpertRegistry):
        self.registry = registry
        self.tasks: Dict[str, DispatchTask] = {}
    
    def dispatch(self, input_text: str) -> DispatchTask:
        """调度任务到专家"""
        expert_name = self.registry.find_expert(input_text)
        if not expert_name:
            return self._no_expert_fallback(input_text)
        
        task = DispatchTask(
            id=f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            input_text=input_text,
            target=expert_name,
            dispatch_type=DispatchType.EXPERT
        )
        
        expert_info = self.registry.experts[expert_name]
        handler = expert_info["handler"]
        
        try:
            task.result = handler(input_text)
            task.completed = True
        except Exception as e:
            task.result = f"[ERROR] {str(e)}"
        
        self.tasks[task.id] = task
        return task
    
    def _no_expert_fallback(self, input_text: str) -> DispatchTask:
        task = DispatchTask(
            id=f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            input_text=input_text,
            target="fallback",
            dispatch_type=DispatchType.EXPERT,
            completed=True,
            result=f"已接收: {input_text}"
        )
        self.tasks[task.id] = task
        return task


# --- 2. Gate2: 复杂度判断 ---

class ComplexityLevel(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class Gate2Result:
    needs_upgrade: bool
    complexity: ComplexityLevel
    reason: str
    expert_response: str


class Gate2ComplexityJudge:
    """Gate2 - 复杂度判断网关 - 决定是否升级到 S"""
    
    def __init__(self):
        self.upgrade_keywords = [
            "分步", "步骤", "规划", "设计", "构建", "创建", "开发", "实现",
            "1.", "2.", "3.", "第一步", "第二步", "第三步",
            "复杂", "多个", "系列", "链条"
        ]
        self.simple_keywords = [
            "查询", "搜索", "查找", "获取", "查看", "列表", "单个", "简单"
        ]
    
    def judge(self, input_text: str, expert_response: str) -> Gate2Result:
        """判断是否需要升级到 S"""
        score = 0
        
        # 1. 检查输入中的升级关键词
        input_lower = input_text.lower()
        for keyword in self.upgrade_keywords:
            if keyword.lower() in input_lower:
                score += 2
        
        # 2. 检查专家回复是否暗示需要升级
        response_lower = expert_response.lower()
        if any(phrase in response_lower for phrase in ["需要", "建议", "这个", "涉及"]):
            score += 1
        
        # 3. 根据长度判断
        if len(input_text.split()) > 50:
            score += 1
        
        # 4. 判断结果
        if score >= 3:
            return Gate2Result(
                needs_upgrade=True,
                complexity=ComplexityLevel.COMPLEX,
                reason=f"高复杂度得分: {score}",
                expert_response=expert_response
            )
        elif score >= 1:
            return Gate2Result(
                needs_upgrade=True,
                complexity=ComplexityLevel.MEDIUM,
                reason=f"中复杂度得分: {score}",
                expert_response=expert_response
            )
        else:
            return Gate2Result(
                needs_upgrade=False,
                complexity=ComplexityLevel.SIMPLE,
                reason=f"简单得分: {score}",
                expert_response=expert_response
            )


# --- 3. Orchestrator 模块 ---

class TaskState(Enum):
    CREATED = "created"
    PLANNED = "planned"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    DONE = "done"
    FAILED = "failed"


@dataclass
class PlanStep:
    id: int
    description: str
    tool: Optional[str] = None
    status: TaskState = TaskState.CREATED
    result: Optional[str] = None


@dataclass
class OrchestratorTask:
    id: str
    input_text: str
    steps: List[PlanStep]
    status: TaskState = TaskState.CREATED
    final_result: Optional[str] = None


class Orchestrator:
    """编排器 - S 层核心"""
    
    def __init__(self):
        self.tasks: Dict[str, OrchestratorTask] = {}
    
    def plan(self, input_text: str) -> OrchestratorTask:
        """规划任务步骤"""
        steps = self._generate_steps(input_text)
        task = OrchestratorTask(
            id=f"orch_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            input_text=input_text,
            steps=steps,
            status=TaskState.PLANNED
        )
        self.tasks[task.id] = task
        return task
    
    def execute(self, task_id: str) -> OrchestratorTask:
        """执行任务"""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = TaskState.EXECUTING
        
        for step in task.steps:
            step.status = TaskState.EXECUTING
            step.result = self._execute_step(step)
            step.status = TaskState.DONE
        
        task.final_result = self._compile_result(task.steps)
        task.status = TaskState.DONE
        return task
    
    def _generate_steps(self, input_text: str) -> List[PlanStep]:
        """生成执行步骤（简单版本）"""
        return [
            PlanStep(id=1, description=f"分析: {input_text[:30]}"),
            PlanStep(id=2, description="执行核心任务"),
            PlanStep(id=3, description="验证结果"),
            PlanStep(id=4, description="输出最终答案")
        ]
    
    def _execute_step(self, step: PlanStep) -> str:
        """执行单个步骤"""
        return f"[Step {step.id}] {step.description} - 完成"
    
    def _compile_result(self, steps: List[PlanStep]) -> str:
        """编译最终结果"""
        return "\n".join([
            "## 执行结果",
            ""
        ] + [f"{step.id}. {step.result}" for step in steps])


# --- 4. D/S 协作主流程 ---

@dataclass
class DSCollaborationResult:
    used_orchestrator: bool
    dispatch_task: Optional[DispatchTask]
    orchestrator_task: Optional[OrchestratorTask]
    final_result: str
    complexity: ComplexityLevel


class DSCollaboration:
    """D/S 协作主类"""
    
    def __init__(self):
        self.registry = ExpertRegistry()
        self.dispatcher = Dispatcher(self.registry)
        self.gate2 = Gate2ComplexityJudge()
        self.orchestrator = Orchestrator()
    
    def register_experts(self, experts: Dict[str, Callable]):
        """批量注册专家"""
        for name, info in experts.items():
            if isinstance(info, tuple):
                handler, desc, tags = info
                self.registry.register(name, handler, desc, tags)
            else:
                self.registry.register(name, info, name, [])
    
    def process(self, input_text: str) -> DSCollaborationResult:
        """处理输入 - D/S 协作主流程"""
        # 1. 先 D: Dispatch 到专家
        dispatch_task = self.dispatcher.dispatch(input_text)
        
        if not dispatch_task.completed:
            return DSCollaborationResult(
                used_orchestrator=False,
                dispatch_task=dispatch_task,
                orchestrator_task=None,
                final_result=dispatch_task.result or "[ERROR]",
                complexity=ComplexityLevel.SIMPLE
            )
        
        # 2. Gate2: 判断是否需要升级
        gate2_result = self.gate2.judge(input_text, dispatch_task.result)
        
        if not gate2_result.needs_upgrade:
            return DSCollaborationResult(
                used_orchestrator=False,
                dispatch_task=dispatch_task,
                orchestrator_task=None,
                final_result=dispatch_task.result,
                complexity=gate2_result.complexity
            )
        
        # 3. S: 升级到 Orchestrator
        orch_task = self.orchestrator.plan(input_text)
        orch_task = self.orchestrator.execute(orch_task.id)
        
        return DSCollaborationResult(
            used_orchestrator=True,
            dispatch_task=dispatch_task,
            orchestrator_task=orch_task,
            final_result=orch_task.final_result or dispatch_task.result,
            complexity=gate2_result.complexity
        )

