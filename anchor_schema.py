from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class FactAnchor(BaseModel):
    """事实锚点数据结构 - 经过人工验证的不可动摇的真值"""
    id: str = Field(description="锚点唯一标识")
    topic: str = Field(description="锚点主题/关键词")
    verified_truth: str = Field(description="经过验证的绝对事实")
    source: str = Field(description="事实来源")
    confidence_score: float = Field(default=1.0, description="置信度，默认为1.0", ge=0.0, le=1.0)
    verified_at: str = Field(description="验证日期")
    tags: List[str] = Field(default=[], description="标签列表")


class AnchorDB(BaseModel):
    """锚点数据库"""
    schema_version: str = Field(description="数据库schema版本")
    anchors: List[FactAnchor] = Field(description="锚点列表")
    metadata: Dict = Field(description="元数据")


class DeviationReport(BaseModel):
    """偏差报告 - 当检测到AI回答与锚点冲突时生成"""
    status: str = Field(description="校验状态: PASSED/FAILED")
    query_topic: str = Field(description="用户查询主题")
    conflicting_anchor: Optional[FactAnchor] = Field(default=None, description="冲突的锚点")
    conflict_point: str = Field(description="冲突点描述")
    ai_response: str = Field(description="AI生成的回答")
    verified_truth: str = Field(description="锚点中的真值")
    deviation_score: float = Field(description="偏差率 0-1", ge=0.0, le=1.0)
    timestamp: str = Field(description="检测时间")


class ValidationPass(BaseModel):
    """校验通过报告"""
    status: str = Field(default="PASSED", description="校验状态")
    query_topic: str = Field(description="用户查询主题")
    matched_anchors: List[FactAnchor] = Field(description="匹配的锚点列表")
    confidence_score: float = Field(description="整体置信度")
    timestamp: str = Field(description="检测时间")


class MetricsRecord(BaseModel):
    """偏差率记录"""
    timestamp: str = Field(description="时间戳")
    question_type: str = Field(description="问题类型")
    triggered_anchor: bool = Field(description="是否触发锚点校验")
    initial_deviation_rate: float = Field(description="初次生成偏差率", ge=0.0, le=1.0)
    rewrote: bool = Field(description="是否进行了重写")
    final_deviation_rate: Optional[float] = Field(default=None, description="重写后的偏差率")
    query: str = Field(description="用户查询")
    anchor_topic: Optional[str] = Field(default=None, description="匹配的锚点主题")