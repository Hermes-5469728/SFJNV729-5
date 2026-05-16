"""
GaiaNode - Gaia L1-L7 校验节点类
封装防御管道为可复用的校验节点

规则集：
- 代码生成：SecurityRule + ArchitectureRule + StyleRule
- 小说创作：WorldConsistencyRule + PlotLogicRule + ToneRule
- PPT生成：LogicFlowRule + FormatRule + ContentConsistencyRule
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from loguru import logger

class Verdict(Enum):
    """校验结果"""
    PASS = "PASS"
    FAIL = "FAIL"

@dataclass
class RuleResult:
    """规则校验结果"""
    rule_name: str
    verdict: Verdict
    message: str
    suggestions: List[str] = None

@dataclass
class GaiaNodeResult:
    """GaiaNode 执行结果"""
    verdict: Verdict
    rule_results: List[RuleResult]
    retry_hint: Optional[str] = None

class Rule:
    """校验规则基类"""
    def __init__(self, name: str):
        self.name = name

    def check(self, content: str, context: Dict[str, Any] = None) -> RuleResult:
        raise NotImplementedError

class SecurityRule(Rule):
    """安全规则"""
    def __init__(self):
        super().__init__("SecurityRule")

    def check(self, content: str, context: Dict[str, Any] = None) -> RuleResult:
        dangerous = ["eval(", "exec(", "__import__", "os.system", "subprocess"]
        for pattern in dangerous:
            if pattern in content:
                return RuleResult(
                    rule_name=self.name,
                    verdict=Verdict.FAIL,
                    message=f"检测到危险模式: {pattern}",
                    suggestions=["移除危险函数调用", "使用安全的替代方案"]
                )
        return RuleResult(rule_name=self.name, verdict=Verdict.PASS, message="安全检查通过")

class ArchitectureRule(Rule):
    """架构规范规则"""
    def __init__(self):
        super().__init__("ArchitectureRule")

    def check(self, content: str, context: Dict[str, Any] = None) -> RuleResult:
        issues = []
        if "def " in content and not any(name.islower() for name in content.split('def ')[1:] if '(' in name):
            issues.append("函数命名不符合小写下划线规范")
        if '"""' not in content and "'''" not in content and '#' not in content:
            issues.append("代码缺少注释")
        if issues:
            return RuleResult(
                rule_name=self.name,
                verdict=Verdict.FAIL,
                message="; ".join(issues),
                suggestions=["使用小写加下划线命名函数", "添加文档字符串"]
            )
        return RuleResult(rule_name=self.name, verdict=Verdict.PASS, message="架构规范检查通过")

class StyleRule(Rule):
    """代码风格规则"""
    def __init__(self):
        super().__init__("StyleRule")

    def check(self, content: str, context: Dict[str, Any] = None) -> RuleResult:
        lines = content.split('\n')
        long_lines = [i+1 for i, line in enumerate(lines) if len(line) > 120]
        if long_lines:
            return RuleResult(
                rule_name=self.name,
                verdict=Verdict.FAIL,
                message=f"存在超长行: {long_lines[:5]}",
                suggestions=["单行不超过120字符"]
            )
        return RuleResult(rule_name=self.name, verdict=Verdict.PASS, message="代码风格检查通过")

class WorldConsistencyRule(Rule):
    """世界观一致性规则"""
    def __init__(self):
        super().__init__("WorldConsistencyRule")

    def check(self, content: str, context: Dict[str, Any] = None) -> RuleResult:
        if "魔法" in content and "科技" in content:
            # 检查是否矛盾
            magic_tech_contradiction = ["科技无法解释魔法", "魔法违反物理定律"]
            if any(phrase in content for phrase in magic_tech_contradiction):
                return RuleResult(
                    rule_name=self.name,
                    verdict=Verdict.FAIL,
                    message="世界观存在矛盾：魔法与科技元素冲突",
                    suggestions=["统一世界观设定", "避免在同一场景混用矛盾元素"]
                )
        return RuleResult(rule_name=self.name, verdict=Verdict.PASS, message="世界观一致性检查通过")

class PlotLogicRule(Rule):
    """剧情逻辑规则"""
    def __init__(self):
        super().__init__("PlotLogicRule")

    def check(self, content: str, context: Dict[str, Any] = None) -> RuleResult:
        # 简单检查：是否有明显的逻辑漏洞
        sentences = content.split('。')
        if len(sentences) < 3:
            return RuleResult(
                rule_name=self.name,
                verdict=Verdict.FAIL,
                message="剧情内容过少",
                suggestions=["充实剧情细节"]
            )
        return RuleResult(rule_name=self.name, verdict=Verdict.PASS, message="剧情逻辑检查通过")

class ToneRule(Rule):
    """语气风格规则"""
    def __init__(self):
        super().__init__("ToneRule")

    def check(self, content: str, context: Dict[str, Any] = None) -> RuleResult:
        # 检查语气是否一致
        formal_count = sum(1 for word in ["因此", "然而", "综上所述"] if word in content)
        casual_count = sum(1 for word in ["哈哈", "没问题", "搞定"] if word in content)
        if formal_count > 0 and casual_count > 3:
            return RuleResult(
                rule_name=self.name,
                verdict=Verdict.FAIL,
                message="语气风格不一致：正式与口语混用",
                suggestions=["统一全文语气风格"]
            )
        return RuleResult(rule_name=self.name, verdict=Verdict.PASS, message="语气风格检查通过")

class LogicFlowRule(Rule):
    """PPT逻辑流程规则"""
    def __init__(self):
        super().__init__("LogicFlowRule")

    def check(self, content: str, context: Dict[str, Any] = None) -> RuleResult:
        required_sections = ["目录", "背景", "方案", "总结"]
        missing = [s for s in required_sections if s not in content]
        if missing:
            return RuleResult(
                rule_name=self.name,
                verdict=Verdict.FAIL,
                message=f"缺少必要章节: {missing}",
                suggestions=["添加目录/背景/方案/总结章节"]
            )
        return RuleResult(rule_name=self.name, verdict=Verdict.PASS, message="逻辑流程检查通过")

class FormatRule(Rule):
    """PPT格式规则"""
    def __init__(self):
        super().__init__("FormatRule")

    def check(self, content: str, context: Dict[str, Any] = None) -> RuleResult:
        if "|" not in content and "表格" in context.get('task_type', ''):
            return RuleResult(
                rule_name=self.name,
                verdict=Verdict.FAIL,
                message="缺少表格格式",
                suggestions=["使用Markdown表格展示数据"]
            )
        return RuleResult(rule_name=self.name, verdict=Verdict.PASS, message="格式检查通过")

class ContentConsistencyRule(Rule):
    """内容一致性规则（L7结构对齐）"""
    def __init__(self):
        super().__init__("ContentConsistencyRule")

    def check(self, content: str, context: Dict[str, Any] = None) -> RuleResult:
        # 检查内容完整性
        if len(content) < 100:
            return RuleResult(
                rule_name=self.name,
                verdict=Verdict.FAIL,
                message="内容过少，不足以支撑结构",
                suggestions=["充实内容"]
            )
        return RuleResult(rule_name=self.name, verdict=Verdict.PASS, message="内容一致性检查通过")

class GaiaNode:
    """Gaia 校验节点"""

    RULE_SETS = {
        "code_generation": [SecurityRule, ArchitectureRule, StyleRule],
        "novel_writing": [WorldConsistencyRule, PlotLogicRule, ToneRule],
        "ppt_generation": [LogicFlowRule, FormatRule, ContentConsistencyRule],
    }

    def __init__(self, node_type: str):
        self.node_type = node_type
        self.rules: List[Rule] = self._build_rule_set(node_type)
        logger.info(f"GaiaNode初始化: {node_type}, 规则数: {len(self.rules)}")

    def _build_rule_set(self, node_type: str) -> List[Rule]:
        """构建规则集"""
        rule_classes = self.RULE_SETS.get(node_type, [ContentConsistencyRule])
        return [cls() for cls in rule_classes]

    def validate(self, content: str, context: Dict[str, Any] = None) -> GaiaNodeResult:
        """执行校验"""
        rule_results = []
        all_passed = True
        hints = []

        for rule in self.rules:
            result = rule.check(content, context)
            rule_results.append(result)
            if result.verdict == Verdict.FAIL:
                all_passed = False
                if result.suggestions:
                    hints.extend(result.suggestions)

        verdict = Verdict.PASS if all_passed else Verdict.FAIL
        retry_hint = "; ".join(hints) if hints else None

        return GaiaNodeResult(
            verdict=verdict,
            rule_results=rule_results,
            retry_hint=retry_hint
        )

# 测试
if __name__ == "__main__":
    # 测试代码生成规则
    node = GaiaNode("code_generation")
    result = node.validate('def hello_world():\n    """测试函数"""\n    print("Hello")')
    print(f"代码校验结果: {result.verdict.value}")
    for r in result.rule_results:
        print(f"  - {r.rule_name}: {r.verdict.value}")

    # 测试PPT规则
    node = GaiaNode("ppt_generation")
    result = node.validate("## 目录\n## 背景\n## 方案\n## 总结")
    print(f"\nPPT校验结果: {result.verdict.value}")
    for r in result.rule_results:
        print(f"  - {r.rule_name}: {r.verdict.value}")