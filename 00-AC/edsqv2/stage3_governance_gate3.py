"""
E/D/S/Q Architecture v2.0 - Stage 3: Pluggable Q (Governance) Pipeline
"""

import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass


# --- 1. 检查器基础类 ---

class CheckStatus(Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    BLOCK = "block"


@dataclass
class CheckResult:
    status: CheckStatus
    message: str
    check_name: str
    details: Optional[Dict[str, Any]] = None


class BaseChecker(ABC):
    """检查器基类"""
    
    @abstractmethod
    def check(self, text: str, context: Optional[Dict] = None) -> CheckResult:
        pass


# --- 2. 具体检查器 ---

class FormatChecker(BaseChecker):
    """L1 格式检查器"""
    
    def check(self, text: str, context: Optional[Dict] = None) -> CheckResult:
        if len(text.strip()) < 5:
            return CheckResult(
                CheckStatus.FAIL,
                "输出太短",
                "format_length"
            )
        
        if not re.search(r'[\u4e00-\u9fa5a-zA-Z]', text):
            return CheckResult(
                CheckStatus.FAIL,
                "缺少有效内容",
                "format_content"
            )
        
        return CheckResult(CheckStatus.PASS, "格式检查通过", "format")


class ContractChecker(BaseChecker):
    """L2 契约检查器"""
    
    def check(self, text: str, context: Optional[Dict] = None) -> CheckResult:
        forbidden = ["我绝对", "肯定是", "100%", "一定是", "绝对正确"]
        text_lower = text.lower()
        
        for phrase in forbidden:
            if phrase.lower() in text_lower:
                return CheckResult(
                    CheckStatus.WARNING,
                    f"检测到过度确信: {phrase}",
                    "contract_overconfidence"
                )
        
        return CheckResult(CheckStatus.PASS, "契约检查通过", "contract")


class AnchorChecker(BaseChecker):
    """锚点检查器"""
    
    def __init__(self, anchors: Optional[Dict[str, str]] = None):
        self.anchors = anchors or {}
    
    def check(self, text: str, context: Optional[Dict] = None) -> CheckResult:
        text_lower = text.lower()
        
        for topic, truth in self.anchors.items():
            if topic.lower() in text_lower:
                if truth.lower() not in text_lower:
                    return CheckResult(
                        CheckStatus.FAIL,
                        f"锚点冲突: {topic}",
                        "anchor_conflict",
                        {"anchor": topic, "expected": truth}
                    )
        
        return CheckResult(CheckStatus.PASS, "锚点检查通过", "anchor")


class TraceabilityChecker(BaseChecker):
    """L5 溯源检查器（医疗专用）"""
    
    def check(self, text: str, context: Optional[Dict] = None) -> CheckResult:
        trace_tags = ["[VERIFIED]", "[SOURCE:", "[TRACE:"]
        
        if any(tag in text for tag in trace_tags):
            return CheckResult(CheckStatus.PASS, "溯源标签存在", "traceability")
        
        return CheckResult(
            CheckStatus.WARNING,
            "缺少溯源标签",
            "traceability_missing"
        )


class HallucinationLabelChecker(BaseChecker):
    """幻觉标注检查器"""
    
    def check(self, text: str, context: Optional[Dict] = None) -> CheckResult:
        required_label = "本结果仅供参考"
        
        if required_label in text:
            return CheckResult(CheckStatus.PASS, "幻觉标注存在", "hallucination_label")
        
        return CheckResult(
            CheckStatus.FAIL,
            "缺少强制幻觉标注",
            "hallucination_label_missing"
        )


# --- 3. 检查链配置 ---

class InputType(Enum):
    MEDICAL = "medical"
    SIMPLE = "simple"
    CHAT = "chat"
    COMPLEX = "complex"


@dataclass
class PipelineConfig:
    name: str
    checkers: List[Type[BaseChecker]]
    allow_failure: bool = False


# 预设配置
PIPELINE_CONFIGS: Dict[InputType, PipelineConfig] = {
    InputType.MEDICAL: PipelineConfig(
        name="medical_strict",
        checkers=[
            FormatChecker,
            ContractChecker,
            AnchorChecker,
            TraceabilityChecker,
            HallucinationLabelChecker
        ]
    ),
    InputType.SIMPLE: PipelineConfig(
        name="simple",
        checkers=[FormatChecker, ContractChecker]
    ),
    InputType.CHAT: PipelineConfig(
        name="chat",
        checkers=[FormatChecker],
        allow_failure=True
    ),
    InputType.COMPLEX: PipelineConfig(
        name="complex",
        checkers=[FormatChecker, ContractChecker, AnchorChecker]
    )
}


# --- 4. Gate3: 最终检查 ---

@dataclass
class Gate3Result:
    allowed: bool
    reason: str
    pipeline_name: str
    check_results: List[CheckResult]


class Gate3FinalChecker:
    """Gate3 - 最终检查网关"""
    
    def __init__(self):
        self.checker_registry: Dict[str, Type[BaseChecker]] = {
            "format": FormatChecker,
            "contract": ContractChecker,
            "anchor": AnchorChecker,
            "traceability": TraceabilityChecker,
            "hallucination": HallucinationLabelChecker
        }
    
    def check(self, text: str, input_type: InputType, 
             context: Optional[Dict] = None) -> Gate3Result:
        """执行完整检查链"""
        config = PIPELINE_CONFIGS.get(input_type, PIPELINE_CONFIGS[InputType.SIMPLE])
        
        check_results = []
        
        for CheckerClass in config.checkers:
            checker = CheckerClass()
            if isinstance(checker, AnchorChecker) and context and "anchors" in context:
                checker = AnchorChecker(context["anchors"])
            
            result = checker.check(text, context)
            check_results.append(result)
        
        # 判断是否允许输出
        blocked = any(r.status == CheckStatus.BLOCK for r in check_results)
        failed = any(r.status == CheckStatus.FAIL for r in check_results)
        
        allowed = not blocked and (config.allow_failure or not failed)
        reason = "通过" if allowed else "未通过检查"
        
        return Gate3Result(
            allowed=allowed,
            reason=reason,
            pipeline_name=config.name,
            check_results=check_results
        )


# --- 5. 可插拔治理管道 ---

@dataclass
class GovernanceResult:
    passed: bool
    gate3_result: Gate3Result
    output_text: str


class GovernancePipeline:
    """可插拔治理管道 - Q 层"""
    
    def __init__(self):
        self.gate3 = Gate3FinalChecker()
        self.anchors: Dict[str, str] = {}
    
    def add_anchor(self, topic: str, truth: str):
        """添加锚点"""
        self.anchors[topic] = truth
    
    def process(self, text: str, input_type: InputType) -> GovernanceResult:
        """执行治理"""
        # 如果需要幻觉标注，自动添加
        if input_type in [InputType.MEDICAL, InputType.COMPLEX]:
            if "本结果仅供参考" not in text:
                text += "\n\n本结果仅供参考，AI 生成内容存在不确定性。"
        
        # Gate3 检查
        context = {"anchors": self.anchors}
        gate3_result = self.gate3.check(text, input_type, context)
        
        return GovernanceResult(
            passed=gate3_result.allowed,
            gate3_result=gate3_result,
            output_text=text
        )

