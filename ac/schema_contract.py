"""
契约层
AC Platform v2.0 · L1质量门禁 · Schema验证

核心逻辑：
  1. 所有输入输出必须符合预定义JSON Schema
  2. 不符合则自动修正（auto_corrector集成）
  3. 修正失败则拒绝执行
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class ClinicalQuery(BaseModel):
    """临床查询输入契约"""
    question: str = Field(..., min_length=5)
    context: str | None = None
    urgency: str = Field(default="routine", pattern="^(routine|urgent|emergency)$")


class ClinicalResponse(BaseModel):
    """临床响应输出契约"""
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[str] = Field(default_factory=list)
    hallucination_flagged: bool = Field(default=False)


class DualInferenceResult(BaseModel):
    cold: str
    warm: str
    consistent: bool
    conflict_type: str
    details: str
    cold_hash: str
    warm_hash: str
    timestamp: str

    @validator('conflict_type')
    def valid_conflict_type(cls, v):
        allowed = {'none', 'number_mismatch', 'structural', 'fact_mismatch'}
        if v not in allowed:
            raise ValueError(f'冲突类型必须为 {allowed}')
        return v

    @validator('timestamp')
    def iso_timestamp(cls, v):
        try:
            datetime.fromisoformat(v)
        except:
            raise ValueError('timestamp 必须是 ISO 格式')
        return v


class DispatchResponse(BaseModel):
    session_id: str
    query: str
    matched_experts: List[dict]
    governance_passed: bool
    dispatch_mode: str
    timestamp: str
    dual_inference: Optional[DualInferenceResult] = None


def validate_dispatch(data: dict) -> DispatchResponse:
    """验证调度响应，可被 core.py 在返回前调用"""
    return DispatchResponse(**data)
