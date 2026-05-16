"""
DADS Layer - Octuple Review (八重审查机制颗粒)
OpenCode Hooks:
  /dads review-result <result>     # 审查结果
  /dads review-step <step>         # 单步调试审查
  /dads review-summary <results>   # 获取审查摘要
"""

from loguru import logger
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass

class ReviewStatus(Enum):
    """审查状态"""
    PASS = "pass"
    WARNING = "warning"
    BLOCK = "block"

@dataclass
class ReviewResult:
    """审查结果"""
    check_name: str
    status: ReviewStatus
    message: str
    severity: int  # 1-10

class OctupleReview:
    """
    八重审查机制
    颗粒化模块：每个审查步骤都是独立的，可单步调试
    
    OpenCode TUI 交互:
    - /dads review-result <result> -> review_sync()
    - /dads review-step <step> -> _check_xxx() 单独调用
    - /dads review-summary <results> -> get_summary()
    """
    
    def __init__(self):
        self.review_functions = [
            self._check_sensitive_content,
            self._check_medical_accuracy,
            self._check_legal_compliance,
            self._check_ethical_guideline,
            self._check_data_privacy,
            self._check_logical_consistency,
            self._check_output_format,
            self._check_user_intent,
        ]
    
    def _do_review(self, query: str, context: List[Dict], response: str) -> List[ReviewResult]:
        """内部审查逻辑"""
        results = []
        
        for func in self.review_functions:
            try:
                result = func(query, context, response)
                results.append(result)
                
                if result.status == ReviewStatus.BLOCK:
                    logger.warning(f"Blocked by {result.check_name}: {result.message}")
                    return results
                    
            except Exception as e:
                logger.error(f"Review function {func.__name__} failed: {e}")
                results.append(ReviewResult(
                    check_name=func.__name__,
                    status=ReviewStatus.WARNING,
                    message=f"审查函数执行失败: {str(e)}",
                    severity=5
                ))
        
        return results
    
    async def review(self, query: str, context: List[Dict], response: str) -> List[ReviewResult]:
        """异步审查"""
        return self._do_review(query, context, response)
    
    def review_sync(self, query: str, context: List[Dict], response: str) -> List[ReviewResult]:
        """
        同步审查
        OpenCode Hook: /dads review-result <result>
        """
        return self._do_review(query, context, response)
    
    def should_block(self, results: List[ReviewResult]) -> bool:
        """判断是否需要阻断"""
        return any(r.status == ReviewStatus.BLOCK for r in results)
    
    def get_summary(self, results: List[ReviewResult]) -> Dict[str, Any]:
        """
        获取审查摘要
        OpenCode Hook: /dads review-summary <results>
        """
        pass_count = sum(1 for r in results if r.status == ReviewStatus.PASS)
        warning_count = sum(1 for r in results if r.status == ReviewStatus.WARNING)
        block_count = sum(1 for r in results if r.status == ReviewStatus.BLOCK)
        
        return {
            "total_checks": len(results),
            "passed": pass_count,
            "warnings": warning_count,
            "blocked": block_count,
            "overall_status": "passed" if block_count == 0 else "blocked",
            "details": [
                {"check": r.check_name, "status": r.status.value, "severity": r.severity, "message": r.message}
                for r in results
            ]
        }
    
    def get_check_names(self) -> List[str]:
        """获取所有审查步骤名称（供单步调试用）"""
        return [func.__name__ for func in self.review_functions]
    
    def run_single_check(self, check_name: str, query: str, context: List[Dict], response: str) -> Optional[ReviewResult]:
        """
        运行单个审查步骤
        OpenCode Hook: /dads review-step <step>
        """
        for func in self.review_functions:
            if func.__name__ == check_name:
                return func(query, context, response)
        return None
    
    def _check_sensitive_content(self, query: str, context: List[Dict], response: str) -> ReviewResult:
        """第一重：敏感内容审查"""
        sensitive_keywords = ["机密", "隐私", "密码", "银行卡", "身份证"]
        
        for keyword in sensitive_keywords:
            if keyword in response:
                return ReviewResult(
                    check_name="敏感内容审查",
                    status=ReviewStatus.BLOCK,
                    message=f"检测到敏感内容: {keyword}",
                    severity=10
                )
        
        return ReviewResult(
            check_name="敏感内容审查",
            status=ReviewStatus.PASS,
            message="未检测到敏感内容",
            severity=1
        )
    
    def _check_medical_accuracy(self, query: str, context: List[Dict], response: str) -> ReviewResult:
        """第二重：医疗准确性审查"""
        medical_errors = ["癌症可以治愈", "无需手术", "绝对安全"]
        
        for error in medical_errors:
            if error in response:
                return ReviewResult(
                    check_name="医疗准确性审查",
                    status=ReviewStatus.WARNING,
                    message=f"检测到可能不准确的医疗表述: {error}",
                    severity=8
                )
        
        return ReviewResult(
            check_name="医疗准确性审查",
            status=ReviewStatus.PASS,
            message="医疗内容符合规范",
            severity=2
        )
    
    def _check_legal_compliance(self, query: str, context: List[Dict], response: str) -> ReviewResult:
        """第三重：法律法规合规审查"""
        illegal_keywords = ["规避法律", "逃税", "伪造"]
        
        for keyword in illegal_keywords:
            if keyword in response:
                return ReviewResult(
                    check_name="法律法规合规审查",
                    status=ReviewStatus.BLOCK,
                    message=f"检测到违法内容: {keyword}",
                    severity=10
                )
        
        return ReviewResult(
            check_name="法律法规合规审查",
            status=ReviewStatus.PASS,
            message="符合法律法规要求",
            severity=3
        )
    
    def _check_ethical_guideline(self, query: str, context: List[Dict], response: str) -> ReviewResult:
        """第四重：伦理准则审查"""
        unethical_patterns = ["歧视", "偏见", "伤害"]
        
        for pattern in unethical_patterns:
            if pattern in response:
                return ReviewResult(
                    check_name="伦理准则审查",
                    status=ReviewStatus.WARNING,
                    message=f"检测到不符合伦理的内容: {pattern}",
                    severity=7
                )
        
        return ReviewResult(
            check_name="伦理准则审查",
            status=ReviewStatus.PASS,
            message="符合伦理准则",
            severity=4
        )
    
    def _check_data_privacy(self, query: str, context: List[Dict], response: str) -> ReviewResult:
        """第五重：数据隐私保护审查"""
        privacy_patterns = ["姓名:", "电话:", "地址:", "病历号:"]
        
        for pattern in privacy_patterns:
            if pattern in response:
                return ReviewResult(
                    check_name="数据隐私保护审查",
                    status=ReviewStatus.BLOCK,
                    message=f"检测到可能的隐私泄露: {pattern}",
                    severity=10
                )
        
        return ReviewResult(
            check_name="数据隐私保护审查",
            status=ReviewStatus.PASS,
            message="未检测到隐私泄露",
            severity=5
        )
    
    def _check_logical_consistency(self, query: str, context: List[Dict], response: str) -> ReviewResult:
        """第六重：逻辑一致性审查"""
        context_text = " ".join([doc.get("text", "") for doc in context])
        response_words = response.split()[:10]
        missing_words = [w for w in response_words if w not in context_text]
        
        if len(missing_words) > 5:
            return ReviewResult(
                check_name="逻辑一致性审查",
                status=ReviewStatus.WARNING,
                message=f"响应与上下文一致性不足",
                severity=6
            )
        
        return ReviewResult(
            check_name="逻辑一致性审查",
            status=ReviewStatus.PASS,
            message="响应与上下文逻辑一致",
            severity=6
        )
    
    def _check_output_format(self, query: str, context: List[Dict], response: str) -> ReviewResult:
        """第七重：输出格式规范审查"""
        if len(response) < 50:
            return ReviewResult(
                check_name="输出格式规范审查",
                status=ReviewStatus.WARNING,
                message="响应过短，可能信息不足",
                severity=3
            )
        
        if len(response) > 2000:
            return ReviewResult(
                check_name="输出格式规范审查",
                status=ReviewStatus.WARNING,
                message="响应过长，建议精简",
                severity=3
            )
        
        return ReviewResult(
            check_name="输出格式规范审查",
            status=ReviewStatus.PASS,
            message="输出格式符合要求",
            severity=7
        )
    
    def _check_user_intent(self, query: str, context: List[Dict], response: str) -> ReviewResult:
        """第八重：用户意图匹配审查"""
        question_keywords = ["什么", "如何", "为什么", "哪个", "是否", "怎么办"]
        
        has_question = any(k in query for k in question_keywords)
        
        if has_question and "不知道" in response:
            return ReviewResult(
                check_name="用户意图匹配审查",
                status=ReviewStatus.WARNING,
                message="未能有效回答用户问题",
                severity=4
            )
        
        return ReviewResult(
            check_name="用户意图匹配审查",
            status=ReviewStatus.PASS,
            message="响应与用户意图匹配",
            severity=8
        )