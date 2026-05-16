"""系统自省记忆系统 - 记录决策失败原因和修正路径"""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from pydantic import BaseModel, field_validator
from enum import Enum
import json
from pathlib import Path


class DecisionType(str, Enum):
    """决策类型枚举"""
    RULE_ENGINE = "rule_engine"  # 规则引擎决策
    LLM_ROUTE = "llm_route"  # LLM路由决策
    CONTRACT_EVALUATION = "contract_evaluation"  # 契约评估
    MODULE_DISPATCH = "module_dispatch"  # 模块分发
    DEFENSE_CHECK = "defense_check"  # 防御检查
    OTHER = "other"


class DecisionOutcome(str, Enum):
    """决策结果枚举"""
    SUCCESS = "success"  # 成功
    PARTIAL_SUCCESS = "partial_success"  # 部分成功
    FAILURE = "failure"  # 失败
    TIMEOUT = "timeout"  # 超时
    ERROR = "error"  # 错误


class FailureCategory(str, Enum):
    """失败类别枚举"""
    LOGIC_ERROR = "logic_error"  # 逻辑错误
    DATA_ISSUE = "data_issue"  # 数据问题
    EXTERNAL_SERVICE = "external_service"  # 外部服务问题
    RATE_LIMIT = "rate_limit"  # 速率限制
    PERMISSION_DENIED = "permission_denied"  # 权限拒绝
    TIMEOUT_ERROR = "timeout_error"  # 超时错误
    CONFIGURATION = "configuration"  # 配置问题
    UNKNOWN = "unknown"  # 未知


class CorrectionStep(BaseModel):
    """修正步骤"""
    step_id: str
    description: str
    action: str  # 执行的操作
    result: str  # 执行结果
    timestamp: datetime = datetime.now()


class DecisionMemory(BaseModel):
    """决策记忆"""
    memory_id: str  # 唯一标识
    decision_type: DecisionType
    timestamp: datetime = datetime.now()
    context: Dict[str, Any]  # 决策上下文
    decision: Dict[str, Any]  # 决策内容
    outcome: DecisionOutcome
    failure_category: Optional[FailureCategory] = None
    failure_reason: Optional[str] = None
    error_message: Optional[str] = None
    corrections: List[CorrectionStep] = []
    learning_notes: List[str] = []  # 学习笔记
    related_memories: List[str] = []  # 关联记忆ID
    
    @field_validator('memory_id')
    def validate_memory_id(cls, v):
        if not v.startswith("MEM-"):
            raise ValueError('memory_id must start with "MEM-"')
        return v


class SelfReflection(BaseModel):
    """自我反思"""
    reflection_id: str
    memory_id: str  # 关联的决策记忆
    timestamp: datetime = datetime.now()
    analysis: str  # 分析内容
    insights: List[str] = []  # 洞察
    action_items: List[str] = []  # 行动项
    implemented: bool = False
    implementation_date: Optional[datetime] = None


class IntrospectionConfig(BaseModel):
    """自省配置"""
    enable_introspection: bool = True  # 启用自省
    max_memory_retention_days: int = 365  # 记忆保留天数
    auto_reflection_enabled: bool = True  # 自动反思
    reflection_threshold: float = 0.3  # 反思阈值（失败率）
    enable_vector_indexing: bool = True  # 启用向量化索引


class IntrospectionMemorySystem:
    """系统自省记忆系统"""
    
    def __init__(self, config_path: str = "config/introspection.json"):
        self.config_path = Path(config_path)
        self.config = IntrospectionConfig()
        self._load_config()
        
        # 内存存储
        self.memories: List[DecisionMemory] = []
        self.reflections: List[SelfReflection] = []
        
        # 存储路径
        self.memory_dir = Path("data/introspection")
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载已存储的记忆
        self._load_memories()
    
    def _load_config(self):
        """加载配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.config = IntrospectionConfig(**data)
    
    def save_config(self):
        """保存配置"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config.dict(), f, ensure_ascii=False, indent=2)
    
    def _load_memories(self):
        """加载已存储的记忆"""
        memory_files = list(self.memory_dir.glob("MEM-*.json"))
        for memory_file in memory_files:
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 转换datetime字符串
                    if 'timestamp' in data:
                        data['timestamp'] = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                    for correction in data.get('corrections', []):
                        if 'timestamp' in correction:
                            correction['timestamp'] = datetime.fromisoformat(correction['timestamp'].replace('Z', '+00:00'))
                    self.memories.append(DecisionMemory(**data))
            except Exception:
                continue
        
        # 按时间排序
        self.memories.sort(key=lambda x: x.timestamp, reverse=True)
    
    def _generate_memory_id(self) -> str:
        """生成唯一记忆ID"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        counter = len(self.memories) + 1
        return f"MEM-{timestamp}-{counter:04d}"
    
    def record_decision(self, 
                       decision_type: DecisionType,
                       context: Dict[str, Any],
                       decision: Dict[str, Any],
                       outcome: DecisionOutcome,
                       failure_category: Optional[FailureCategory] = None,
                       failure_reason: Optional[str] = None,
                       error_message: Optional[str] = None) -> str:
        """记录决策"""
        if not self.config.enable_introspection:
            return ""
        
        memory = DecisionMemory(
            memory_id=self._generate_memory_id(),
            decision_type=decision_type,
            context=context,
            decision=decision,
            outcome=outcome,
            failure_category=failure_category,
            failure_reason=failure_reason,
            error_message=error_message
        )
        
        self.memories.append(memory)
        
        # 保存到文件
        memory_file = self.memory_dir / f"{memory.memory_id}.json"
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory.dict(), f, ensure_ascii=False, indent=2, default=str)
        
        # 如果启用了向量化，添加到向量库
        if self.config.enable_vector_indexing:
            self._index_to_vector_db(memory)
        
        # 如果失败，触发自动反思
        if outcome in [DecisionOutcome.FAILURE, DecisionOutcome.ERROR, DecisionOutcome.TIMEOUT]:
            self._trigger_auto_reflection(memory)
        
        return memory.memory_id
    
    def add_correction(self, memory_id: str, step: CorrectionStep):
        """添加修正步骤"""
        memory = next((m for m in self.memories if m.memory_id == memory_id), None)
        if memory:
            memory.corrections.append(step)
            
            # 更新文件
            memory_file = self.memory_dir / f"{memory_id}.json"
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump(memory.dict(), f, ensure_ascii=False, indent=2, default=str)
    
    def add_learning_note(self, memory_id: str, note: str):
        """添加学习笔记"""
        memory = next((m for m in self.memories if m.memory_id == memory_id), None)
        if memory:
            memory.learning_notes.append(note)
            
            # 更新文件
            memory_file = self.memory_dir / f"{memory_id}.json"
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump(memory.dict(), f, ensure_ascii=False, indent=2, default=str)
    
    def _index_to_vector_db(self, memory: DecisionMemory):
        """将记忆添加到向量库"""
        # 提取关键信息作为向量内容
        content = f"""
        Memory ID: {memory.memory_id}
        Decision Type: {memory.decision_type.value}
        Outcome: {memory.outcome.value}
        Failure Category: {memory.failure_category.value if memory.failure_category else 'None'}
        Failure Reason: {memory.failure_reason or 'None'}
        Context: {json.dumps(memory.context, ensure_ascii=False)}
        Decision: {json.dumps(memory.decision, ensure_ascii=False)}
        """
        
        # 这里应该调用向量存储的添加方法
        # vector_store.add_documents([{
        #     "id": memory.memory_id,
        #     "content": content,
        #     "metadata": {
        #         "decision_type": memory.decision_type.value,
        #         "outcome": memory.outcome.value,
        #         "timestamp": memory.timestamp.isoformat()
        #     }
        # }])
        pass
    
    def _trigger_auto_reflection(self, memory: DecisionMemory):
        """触发自动反思"""
        if not self.config.auto_reflection_enabled:
            return
        
        # 简单的反思逻辑：分析失败原因
        analysis = self._analyze_failure(memory)
        
        reflection = SelfReflection(
            reflection_id=f"REF-{memory.memory_id[4:]}",
            memory_id=memory.memory_id,
            analysis=analysis,
            insights=self._generate_insights(memory),
            action_items=self._generate_action_items(memory)
        )
        
        self.reflections.append(reflection)
        
        # 保存反思
        reflection_file = self.memory_dir / f"{reflection.reflection_id}.json"
        with open(reflection_file, 'w', encoding='utf-8') as f:
            json.dump(reflection.dict(), f, ensure_ascii=False, indent=2, default=str)
    
    def _analyze_failure(self, memory: DecisionMemory) -> str:
        """分析失败原因"""
        analysis = f"""
决策ID: {memory.memory_id}
决策类型: {memory.decision_type.value}
时间: {memory.timestamp}

失败类别: {memory.failure_category.value if memory.failure_category else '未知'}
失败原因: {memory.failure_reason or '未记录'}
错误信息: {memory.error_message or '无'}

上下文摘要:
{json.dumps({k: str(v)[:100] for k, v in memory.context.items()}, ensure_ascii=False, indent=2)}

决策内容:
{json.dumps(memory.decision, ensure_ascii=False, indent=2)}
"""
        return analysis
    
    def _generate_insights(self, memory: DecisionMemory) -> List[str]:
        """生成洞察"""
        insights = []
        
        # 根据失败类别生成洞察
        if memory.failure_category == FailureCategory.EXTERNAL_SERVICE:
            insights.append("外部服务不可靠，需要增加重试机制")
            insights.append("考虑添加降级策略")
        
        if memory.failure_category == FailureCategory.RATE_LIMIT:
            insights.append("当前速率限制过于严格")
            insights.append("需要优化流量控制策略")
        
        if memory.failure_category == FailureCategory.DATA_ISSUE:
            insights.append("数据质量问题影响决策准确性")
            insights.append("需要增加数据验证步骤")
        
        if memory.failure_category == FailureCategory.CONFIGURATION:
            insights.append("配置错误导致决策失败")
            insights.append("需要增加配置验证机制")
        
        if memory.failure_category == FailureCategory.TIMEOUT_ERROR:
            insights.append("响应超时影响用户体验")
            insights.append("需要优化超时设置或增加异步处理")
        
        if not insights:
            insights.append("需要进一步分析失败原因")
        
        return insights
    
    def _generate_action_items(self, memory: DecisionMemory) -> List[str]:
        """生成行动项"""
        items = []
        
        if memory.failure_category == FailureCategory.EXTERNAL_SERVICE:
            items.append("实现服务降级逻辑")
            items.append("添加重试机制")
        
        if memory.failure_category == FailureCategory.RATE_LIMIT:
            items.append("调整速率限制参数")
            items.append("实现请求队列")
        
        if memory.failure_category == FailureCategory.DATA_ISSUE:
            items.append("增加数据验证层")
            items.append("建立数据质量监控")
        
        if memory.failure_category == FailureCategory.CONFIGURATION:
            items.append("增加配置验证步骤")
            items.append("创建配置测试套件")
        
        if not items:
            items.append("记录失败案例供后续分析")
        
        return items
    
    def search_memories(self, query: str, limit: int = 10) -> List[DecisionMemory]:
        """搜索记忆"""
        # 简单的文本匹配搜索
        results = []
        query_lower = query.lower()
        
        for memory in self.memories:
            # 在多个字段中搜索
            search_text = f"{memory.decision_type.value} {memory.outcome.value} " \
                        f"{memory.failure_reason or ''} {memory.error_message or ''}"
            
            if query_lower in search_text.lower():
                results.append(memory)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_failure_rate(self, decision_type: Optional[DecisionType] = None) -> float:
        """计算失败率"""
        if not self.memories:
            return 0.0
        
        filtered = self.memories
        if decision_type:
            filtered = [m for m in self.memories if m.decision_type == decision_type]
        
        if not filtered:
            return 0.0
        
        failure_count = sum(1 for m in filtered 
                          if m.outcome in [DecisionOutcome.FAILURE, DecisionOutcome.ERROR, DecisionOutcome.TIMEOUT])
        
        return failure_count / len(filtered)
    
    def get_insights_report(self, days: int = 7) -> Dict[str, Any]:
        """生成洞察报告"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_memories = [m for m in self.memories if m.timestamp >= cutoff_date]
        
        # 按失败类别统计
        category_counts = {}
        for memory in recent_memories:
            if memory.failure_category:
                category_counts[memory.failure_category.value] = category_counts.get(memory.failure_category.value, 0) + 1
        
        # 获取所有行动项
        all_action_items = []
        for reflection in self.reflections:
            all_action_items.extend(reflection.action_items)
        
        # 获取所有学习笔记
        all_notes = []
        for memory in recent_memories:
            all_notes.extend(memory.learning_notes)
        
        return {
            "period": f"最近{days}天",
            "total_decisions": len(recent_memories),
            "failure_rate": self.get_failure_rate(),
            "failure_category_distribution": category_counts,
            "action_items": list(set(all_action_items))[:20],
            "learning_notes": list(set(all_notes))[:30],
            "recommendations": self._generate_recommendations(category_counts)
        }
    
    def _generate_recommendations(self, category_counts: Dict[str, int]) -> List[str]:
        """根据失败类别生成建议"""
        recommendations = []
        
        if category_counts.get("external_service", 0) > 5:
            recommendations.append("建议增加外部服务的冗余配置和重试机制")
        
        if category_counts.get("rate_limit", 0) > 3:
            recommendations.append("建议调整速率限制策略，考虑增加请求队列")
        
        if category_counts.get("data_issue", 0) > 3:
            recommendations.append("建议加强数据验证和质量监控")
        
        if category_counts.get("configuration", 0) > 2:
            recommendations.append("建议增加配置验证和测试")
        
        if not recommendations:
            recommendations.append("系统运行良好，继续保持监控")
        
        return recommendations


# 自省系统架构图
def get_introspection_architecture() -> str:
    """生成自省系统架构图"""
    return """
```mermaid
flowchart TD
    subgraph 决策层["决策层"]
        A1[规则引擎]
        A2[LLM路由]
        A3[契约评估]
        A4[模块分发]
        A5[防御检查]
    end
    
    subgraph 记忆层["记忆层"]
        B1[决策记录]
        B2[失败分析]
        B3[修正路径]
        B4[学习笔记]
    end
    
    subgraph 反思层["反思层"]
        C1[自动反思]
        C2[洞察提取]
        C3[行动项生成]
        C4[自我进化]
    end
    
    subgraph 存储层["存储层"]
        D1[(JSON存储)]
        D2[(向量数据库)]
    end
    
    A1 --> B1
    A2 --> B1
    A3 --> B1
    A4 --> B1
    A5 --> B1
    
    B1 -->|失败| B2
    B1 -->|成功| B4
    
    B2 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4
    
    B1 --> D1
    B2 --> D1
    B4 --> D1
    
    B1 --> D2
    B2 --> D2
    
    C4 --> A1
    C4 --> A2
```
"""


# 示例使用
if __name__ == "__main__":
    introspection = IntrospectionMemorySystem()
    
    # 记录一个失败的决策
    memory_id = introspection.record_decision(
        decision_type=DecisionType.LLM_ROUTE,
        context={"module": "medical", "task_type": "clinical_decision"},
        decision={"provider": "dashscope", "route_type": "critical"},
        outcome=DecisionOutcome.FAILURE,
        failure_category=FailureCategory.EXTERNAL_SERVICE,
        failure_reason="外部服务超时",
        error_message="Connection timeout after 30s"
    )
    
    print(f"记录的记忆ID: {memory_id}")
    
    # 添加修正步骤
    introspection.add_correction(
        memory_id,
        CorrectionStep(
            step_id="STEP-001",
            description="切换到备用提供商",
            action="将LLM提供商从dashscope切换到deepseek",
            result="成功完成请求"
        )
    )
    
    # 添加学习笔记
    introspection.add_learning_note(memory_id, "需要增加多提供商降级策略")
    
    # 获取洞察报告
    report = introspection.get_insights_report(days=7)
    print("\n洞察报告:")
    print(json.dumps(report, ensure_ascii=False, indent=2))
