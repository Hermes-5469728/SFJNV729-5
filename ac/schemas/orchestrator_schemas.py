"""Orchestrator Schema 定义"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional
from enum import Enum

class TaskStateEnum(str, Enum):
    """任务状态枚举"""
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

class OrchestrateInput(BaseModel):
    """orchestrate 命令输入"""
    prompt: str = Field(..., description="任务提示", min_length=1)
    agents: Optional[List[str]] = Field(None, description="可用 Agent 列表")
    max_workers: int = Field(default=2, ge=1, le=10, description="最大并行工作数")
    
    @validator('prompt')
    def validate_prompt(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("任务提示不能为空")
        return v

class OrchestrateOutput(BaseModel):
    """orchestrate 命令输出"""
    session_id: str
    status: str
    total_steps: int
    completed_steps: int
    failed_steps: int
    elapsed_seconds: float
    steps: List[Dict[str, Any]]

class VerifyInput(BaseModel):
    """verify 命令输入"""
    task_id: str = Field(..., description="任务 ID", min_length=1)
    type: str = Field(..., description="验证类型", pattern="^(url|database|file)$")
    params: Dict[str, Any] = Field(..., description="验证参数")
    
    @validator('params')
    def validate_params(cls, v, values):
        if 'type' in values:
            if values['type'] == 'url' and 'url' not in v:
                raise ValueError("URL 验证必须提供 url 参数")
            if values['type'] == 'database' and ('table' not in v and 'query' not in v):
                raise ValueError("数据库验证必须提供 table 或 query 参数")
            if values['type'] == 'file' and 'path' not in v:
                raise ValueError("文件验证必须提供 path 参数")
        return v

class VerifyOutput(BaseModel):
    """verify 命令输出"""
    task_id: str
    status: str
    message: str
    evidence: Dict[str, Any]
    latency_ms: float

class ContractInput(BaseModel):
    """contract 命令输入"""
    agent_id: str = Field(..., description="Agent ID", min_length=1)
    output: Dict[str, Any] = Field(..., description="输出数据")

class ContractOutput(BaseModel):
    """contract 命令输出"""
    agent_id: str
    status: str
    violations: List[Dict[str, Any]]

class StateInput(BaseModel):
    """state 命令输入"""
    task_id: str = Field(..., description="任务 ID", min_length=1)
    agent_id: str = Field(..., description="Agent ID", min_length=1)
    status: str = Field(..., description="状态")
    data: Optional[Dict[str, Any]] = Field(None, description="附加数据")

class StateOutput(BaseModel):
    """state 命令输出"""
    task_id: str
    status: str
    version: int

class RiskInput(BaseModel):
    """risk 命令输入"""
    operation: str = Field(..., description="操作命令", min_length=1)

class RiskOutput(BaseModel):
    """risk 命令输出"""
    operation: str
    allowed: bool
    risk_level: str
    reason: str
    requires_confirmation: bool
    alternatives: List[str]

class LockInput(BaseModel):
    """lock 命令输入"""
    action: str = Field(..., description="操作", pattern="^(acquire|release)$")
    resource_id: str = Field(..., description="资源 ID", min_length=1)
    holder_id: str = Field(..., description="持有者 ID", min_length=1)

class LockOutput(BaseModel):
    """lock 命令输出"""
    action: str
    resource_id: str
    holder_id: str
    success: bool

class OrchStatusOutput(BaseModel):
    """orch-status 命令输出"""
    session_id: str
    status: str
    root_prompt: str
    metrics: Dict[str, Any]
    steps: List[Dict[str, Any]]

class PlanStepSchema(BaseModel):
    """计划步骤 Schema"""
    step_id: str
    description: str
    assigned_agent: str
    depends_on: List[str] = []
    status: TaskStateEnum = TaskStateEnum.CREATED
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

class TaskGraphSchema(BaseModel):
    """任务图 Schema"""
    session_id: str
    status: str
    root_prompt: str
    plan: List[PlanStepSchema] = []
    agent_pool: Dict[str, Any] = {}
    shared_context: Dict[str, Any] = {}
    hitl_queue: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {}
    created_at: float = 0.0
    updated_at: float = 0.0