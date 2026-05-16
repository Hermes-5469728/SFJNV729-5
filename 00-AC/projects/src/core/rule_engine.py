"""复杂度判定规则引擎 - 可配置、可回测的责任边界决策系统"""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from pydantic import BaseModel, field_validator
import json
from pathlib import Path


class RuleCondition(BaseModel):
    """规则条件"""
    field: str  # 要检查的字段
    operator: str  # 操作符: eq, ne, gt, lt, ge, le, contains, in, regex
    value: Any  # 比较值
    description: str = ""  # 条件描述


class RuleAction(BaseModel):
    """规则动作"""
    action_type: str  # delegate_to_trae, direct_execute, ask_clarification
    confidence: float = 0.0  # 置信度
    reason: str = ""  # 动作原因


class ComplexityRule(BaseModel):
    """复杂度判定规则"""
    rule_id: str  # 规则唯一标识
    name: str  # 规则名称
    description: str = ""  # 规则描述
    conditions: List[RuleCondition]  # 条件列表
    action: RuleAction  # 执行动作
    priority: int = 100  # 优先级（数字越小优先级越高）
    enabled: bool = True  # 是否启用
    created_at: datetime = datetime.now()
    last_modified: datetime = datetime.now()
    
    @field_validator('priority')
    def validate_priority(cls, v):
        if v < 0 or v > 1000:
            raise ValueError('priority must be between 0 and 1000')
        return v


class RuleEngineConfig(BaseModel):
    """规则引擎配置"""
    default_action: str = "delegate_to_trae"  # 默认动作
    max_rules_to_evaluate: int = 100  # 最大评估规则数
    enable_backtesting: bool = True  # 是否启用回测
    backtesting_window_days: int = 30  # 回测窗口天数


class RuleResult(BaseModel):
    """规则执行结果"""
    rule_id: str
    matched: bool
    action: str
    confidence: float
    reason: str
    evaluation_time: float = 0.0


class ComplexityRuleEngine:
    """复杂度判定规则引擎"""
    
    def __init__(self, config_path: str = "config/rules.json"):
        self.config_path = Path(config_path)
        self.rules: List[ComplexityRule] = []
        self.config = RuleEngineConfig()
        self._load_rules()
    
    def _load_rules(self):
        """加载规则配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载引擎配置
            if 'engine_config' in data:
                self.config = RuleEngineConfig(**data['engine_config'])
            
            # 加载规则
            if 'rules' in data:
                self.rules = [ComplexityRule(**rule) for rule in data['rules']]
            
            # 按优先级排序
            self.rules.sort(key=lambda x: x.priority)
    
    def save_rules(self):
        """保存规则配置"""
        data = {
            'engine_config': self.config.dict(),
            'rules': [rule.dict() for rule in self.rules]
        }
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    def add_rule(self, rule: ComplexityRule):
        """添加规则"""
        # 检查是否已存在
        existing = next((r for r in self.rules if r.rule_id == rule.rule_id), None)
        if existing:
            self.rules.remove(existing)
        
        rule.last_modified = datetime.now()
        self.rules.append(rule)
        self.rules.sort(key=lambda x: x.priority)
        self.save_rules()
    
    def remove_rule(self, rule_id: str):
        """删除规则"""
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        self.save_rules()
    
    def _evaluate_condition(self, condition: RuleCondition, context: Dict[str, Any]) -> bool:
        """评估单个条件"""
        field_value = context.get(condition.field)
        
        if field_value is None:
            return False
        
        try:
            match condition.operator:
                case 'eq':
                    return field_value == condition.value
                case 'ne':
                    return field_value != condition.value
                case 'gt':
                    return field_value > condition.value
                case 'lt':
                    return field_value < condition.value
                case 'ge':
                    return field_value >= condition.value
                case 'le':
                    return field_value <= condition.value
                case 'contains':
                    return str(condition.value) in str(field_value)
                case 'in':
                    return field_value in condition.value
                case 'regex':
                    import re
                    return bool(re.match(str(condition.value), str(field_value)))
                case _:
                    return False
        except Exception:
            return False
    
    def _evaluate_rule(self, rule: ComplexityRule, context: Dict[str, Any]) -> RuleResult:
        """评估单条规则"""
        start_time = datetime.now()
        
        # 检查规则是否启用
        if not rule.enabled:
            return RuleResult(
                rule_id=rule.rule_id,
                matched=False,
                action="",
                confidence=0.0,
                reason="规则未启用"
            )
        
        # 评估所有条件（AND逻辑）
        all_matched = True
        for condition in rule.conditions:
            if not self._evaluate_condition(condition, context):
                all_matched = False
                break
        
        evaluation_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if all_matched:
            return RuleResult(
                rule_id=rule.rule_id,
                matched=True,
                action=rule.action.action_type,
                confidence=rule.action.confidence,
                reason=rule.action.reason,
                evaluation_time=evaluation_time
            )
        
        return RuleResult(
            rule_id=rule.rule_id,
            matched=False,
            action="",
            confidence=0.0,
            reason="条件不匹配",
            evaluation_time=evaluation_time
        )
    
    def evaluate(self, context: Dict[str, Any]) -> RuleResult:
        """评估上下文，返回匹配的规则结果"""
        results = []
        
        for rule in self.rules[:self.config.max_rules_to_evaluate]:
            result = self._evaluate_rule(rule, context)
            results.append(result)
            
            # 如果找到匹配的规则，立即返回（基于优先级）
            if result.matched:
                return result
        
        # 如果没有匹配的规则，返回默认动作
        return RuleResult(
            rule_id="DEFAULT",
            matched=True,
            action=self.config.default_action,
            confidence=0.5,
            reason="无匹配规则，使用默认策略"
        )
    
    def evaluate_all(self, context: Dict[str, Any]) -> List[RuleResult]:
        """评估所有规则，返回所有结果（用于调试）"""
        results = []
        for rule in self.rules[:self.config.max_rules_to_evaluate]:
            result = self._evaluate_rule(rule, context)
            results.append(result)
        return results
    
    def backtest(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """回测历史数据"""
        if not self.config.enable_backtesting:
            return {"error": "回测未启用"}
        
        results = {
            "total_cases": len(historical_data),
            "matches": 0,
            "no_matches": 0,
            "actions": {},
            "average_evaluation_time": 0.0,
            "rule_matches": {}
        }
        
        total_time = 0.0
        
        for record in historical_data:
            context = record.get('context', {})
            expected_action = record.get('expected_action')
            
            result = self.evaluate(context)
            total_time += result.evaluation_time
            
            if result.matched:
                results["matches"] += 1
                results["actions"][result.action] = results["actions"].get(result.action, 0) + 1
                results["rule_matches"][result.rule_id] = results["rule_matches"].get(result.rule_id, 0) + 1
            else:
                results["no_matches"] += 1
        
        if len(historical_data) > 0:
            results["average_evaluation_time"] = total_time / len(historical_data)
        
        return results
    
    def get_rules_summary(self) -> Dict[str, Any]:
        """获取规则摘要"""
        return {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules if r.enabled),
            "disabled_rules": sum(1 for r in self.rules if not r.enabled),
            "default_action": self.config.default_action,
            "enable_backtesting": self.config.enable_backtesting
        }


# 预设规则示例
def create_default_rules() -> List[ComplexityRule]:
    """创建默认规则集"""
    rules = [
        # 规则1：明确的简单任务 - 直接执行
        ComplexityRule(
            rule_id="RULE-001",
            name="简单任务直接执行",
            description="明确的代码修改、文件操作等简单任务",
            conditions=[
                RuleCondition(
                    field="task_type",
                    operator="in",
                    value=["code_fix", "file_operation", "formatting", "simple_query"],
                    description="任务类型为简单操作"
                ),
                RuleCondition(
                    field="estimated_effort_minutes",
                    operator="lt",
                    value=15,
                    description="预估耗时小于15分钟"
                )
            ],
            action=RuleAction(
                action_type="direct_execute",
                confidence=0.95,
                reason="任务明确且简单，Opencode可直接执行"
            ),
            priority=10
        ),
        
        # 规则2：复杂需求分析 - 必须委托Trae
        ComplexityRule(
            rule_id="RULE-002",
            name="复杂需求委托Trae",
            description="涉及架构设计、复杂逻辑分析的任务",
            conditions=[
                RuleCondition(
                    field="task_type",
                    operator="in",
                    value=["architecture_design", "complex_analysis", "system_design", "security_review"],
                    description="任务类型为复杂分析"
                )
            ],
            action=RuleAction(
                action_type="delegate_to_trae",
                confidence=0.99,
                reason="复杂架构任务需要Trae深度分析"
            ),
            priority=20
        ),
        
        # 规则3：医疗领域任务 - 必须委托Trae
        ComplexityRule(
            rule_id="RULE-003",
            name="医疗领域任务委托Trae",
            description="涉及医疗专业知识的任务",
            conditions=[
                RuleCondition(
                    field="domain",
                    operator="eq",
                    value="medical",
                    description="领域为医疗"
                )
            ],
            action=RuleAction(
                action_type="delegate_to_trae",
                confidence=0.99,
                reason="医疗领域任务需要专业知识和审查"
            ),
            priority=25
        ),
        
        # 规则4：高不确定性 - 询问澄清
        ComplexityRule(
            rule_id="RULE-004",
            name="高不确定性需澄清",
            description="需求模糊、信息不全的任务",
            conditions=[
                RuleCondition(
                    field="ambiguity_score",
                    operator="gt",
                    value=0.7,
                    description="模糊度评分高于0.7"
                )
            ],
            action=RuleAction(
                action_type="ask_clarification",
                confidence=0.85,
                reason="需求不够明确，需要进一步澄清"
            ),
            priority=30
        ),
        
        # 规则5：需要API密钥或敏感操作 - 委托Trae
        ComplexityRule(
            rule_id="RULE-005",
            name="敏感操作委托Trae",
            description="涉及API密钥、安全配置的任务",
            conditions=[
                RuleCondition(
                    field="requires_sensitive_info",
                    operator="eq",
                    value=True,
                    description="需要敏感信息"
                )
            ],
            action=RuleAction(
                action_type="delegate_to_trae",
                confidence=0.98,
                reason="敏感操作需要Trae审核"
            ),
            priority=15
        ),
        
        # 规则6：文档生成 - 直接执行
        ComplexityRule(
            rule_id="RULE-006",
            name="文档生成直接执行",
            description="简单的文档生成任务",
            conditions=[
                RuleCondition(
                    field="task_type",
                    operator="eq",
                    value="documentation",
                    description="任务类型为文档生成"
                ),
                RuleCondition(
                    field="template_exists",
                    operator="eq",
                    value=True,
                    description="存在可用模板"
                )
            ],
            action=RuleAction(
                action_type="direct_execute",
                confidence=0.90,
                reason="文档生成任务可直接执行"
            ),
            priority=35
        ),
        
        # 规则7：测试任务 - 直接执行
        ComplexityRule(
            rule_id="RULE-007",
            name="测试任务直接执行",
            description="单元测试、集成测试编写",
            conditions=[
                RuleCondition(
                    field="task_type",
                    operator="eq",
                    value="testing",
                    description="任务类型为测试"
                ),
                RuleCondition(
                    field="test_target",
                    operator="in",
                    value=["unit", "integration"],
                    description="测试类型为单元或集成测试"
                )
            ],
            action=RuleAction(
                action_type="direct_execute",
                confidence=0.92,
                reason="测试编写任务可直接执行"
            ),
            priority=40
        ),
        
        # 规则8：修复已知bug - 直接执行
        ComplexityRule(
            rule_id="RULE-008",
            name="已知bug修复直接执行",
            description="有明确复现步骤和解决方案的bug",
            conditions=[
                RuleCondition(
                    field="task_type",
                    operator="eq",
                    value="bug_fix",
                    description="任务类型为bug修复"
                ),
                RuleCondition(
                    field="reproduction_steps",
                    operator="contains",
                    value="明确",
                    description="有明确复现步骤"
                ),
                RuleCondition(
                    field="solution_known",
                    operator="eq",
                    value=True,
                    description="已知解决方案"
                )
            ],
            action=RuleAction(
                action_type="direct_execute",
                confidence=0.95,
                reason="已知bug修复可直接执行"
            ),
            priority=45
        ),
        
        # 规则9：需要审批的任务 - 委托Trae
        ComplexityRule(
            rule_id="RULE-009",
            name="需要审批的任务委托Trae",
            description="涉及生产环境变更、重大配置修改",
            conditions=[
                RuleCondition(
                    field="requires_approval",
                    operator="eq",
                    value=True,
                    description="需要审批"
                )
            ],
            action=RuleAction(
                action_type="delegate_to_trae",
                confidence=0.99,
                reason="需要审批的任务必须经过Trae审核"
            ),
            priority=5
        ),
        
        # 规则10：紧急任务 - 快速处理
        ComplexityRule(
            rule_id="RULE-010",
            name="紧急任务快速通道",
            description="紧急bug修复或生产问题",
            conditions=[
                RuleCondition(
                    field="priority",
                    operator="eq",
                    value="urgent",
                    description="优先级为紧急"
                ),
                RuleCondition(
                    field="task_type",
                    operator="eq",
                    value="bug_fix",
                    description="任务类型为bug修复"
                )
            ],
            action=RuleAction(
                action_type="direct_execute",
                confidence=0.90,
                reason="紧急任务快速处理"
            ),
            priority=1
        )
    ]
    
    return rules


# 初始化示例
if __name__ == "__main__":
    engine = ComplexityRuleEngine()
    
    # 如果没有规则，创建默认规则
    if not engine.rules:
        default_rules = create_default_rules()
        for rule in default_rules:
            engine.add_rule(rule)
        print("已创建默认规则集")
    
    # 测试评估
    test_context = {
        "task_type": "code_fix",
        "estimated_effort_minutes": 10,
        "domain": "general"
    }
    
    result = engine.evaluate(test_context)
    print(f"评估结果: {result.dict()}")
    
    # 获取规则摘要
    print(f"\n规则摘要: {engine.get_rules_summary()}")
