"""
IterationLoop - 迭代循环与反馈闭环
从"防死循环"升级为"利用循环优化"

功能：
- 执行 -> 校验 -> 失败? -> 注入修正提示 -> 重新执行（最多3次）
- 3次后仍失败 -> 抛出MaxRetriesExceeded
- 每次重试记录输出版本号
"""

from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass, field
from loguru import logger
import time

class MaxRetriesExceeded(Exception):
    """超过最大重试次数异常"""
    def __init__(self, node_name: str, attempts: int, last_error: str):
        self.node_name = node_name
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"节点 {node_name} 重试 {attempts} 次后仍失败: {last_error}")

@dataclass
class IterationResult:
    """迭代结果"""
    success: bool
    output: Any = None
    attempts: int = 0
    versions: List[str] = field(default_factory=list)
    error: Optional[str] = None
    feedback_history: List[str] = field(default_factory=list)

@dataclass
class LoopConfig:
    """循环配置"""
    max_retries: int = 3
    retry_delay_ms: int = 100
    enable_feedback_injection: bool = True

class IterationLoop:
    """迭代循环引擎"""

    def __init__(self, config: LoopConfig = None):
        self.config = config or LoopConfig()
        logger.info(f"IterationLoop初始化: max_retries={self.config.max_retries}")

    def run(self, node_name: str, executor: Callable, validator: Callable,
            context: Dict[str, Any], feedback_template: str = None) -> IterationResult:
        """
        执行迭代循环

        :param node_name: 节点名称
        :param executor: 执行函数，接收context，返回output
        :param validator: 校验函数，接收output，返回 (passed, hint)
        :param context: 执行上下文
        :param feedback_template: 反馈注入模板，如 "请修正以下问题: {hint}"
        :return: IterationResult
        """
        output_versions = []
        feedback_history = []

        for attempt in range(self.config.max_retries):
            logger.info(f"[迭代] {node_name} 第 {attempt + 1} 次尝试")

            try:
                # 执行节点
                start_time = time.time()
                output = executor(context)
                elapsed_ms = int((time.time() - start_time) * 1000)

                # 记录版本
                version_id = f"v{attempt + 1}-{int(time.time() * 1000)}"
                output_versions.append(version_id)

                # 校验输出
                passed, hint = validator(output)

                if passed:
                    logger.info(f"[迭代成功] {node_name} 在第 {attempt + 1} 次尝试通过")
                    return IterationResult(
                        success=True,
                        output=output,
                        attempts=attempt + 1,
                        versions=output_versions,
                        feedback_history=feedback_history
                    )

                # 校验失败，记录反馈
                logger.warning(f"[迭代失败] {node_name} 第 {attempt + 1} 次: {hint}")
                feedback_history.append(hint)

                # 注入修正提示
                if self.config.enable_feedback_injection and hint:
                    if feedback_template:
                        correction_prompt = feedback_template.format(hint=hint)
                    else:
                        correction_prompt = f"请修正以下问题并重新生成: {hint}"

                    # 将修正提示注入到上下文中
                    if 'correction_feedback' not in context:
                        context['correction_feedback'] = []
                    context['correction_feedback'].append({
                        'attempt': attempt + 1,
                        'hint': hint,
                        'prompt': correction_prompt
                    })
                    context['last_correction'] = correction_prompt

                # 延迟重试
                if self.config.retry_delay_ms > 0:
                    time.sleep(self.config.retry_delay_ms / 1000)

            except Exception as e:
                logger.error(f"[迭代异常] {node_name} 第 {attempt + 1} 次: {e}")
                feedback_history.append(f"执行异常: {str(e)}")

        # 达到最大重试次数
        error_msg = feedback_history[-1] if feedback_history else "未知错误"
        logger.error(f"[迭代耗尽] {node_name} 重试 {self.config.max_retries} 次后仍失败")
        return IterationResult(
            success=False,
            attempts=self.config.max_retries,
            versions=output_versions,
            error=error_msg,
            feedback_history=feedback_history
        )

    async def run_async(self, node_name: str, executor: Callable, validator: Callable,
                       context: Dict[str, Any], feedback_template: str = None) -> IterationResult:
        """异步版本"""
        import asyncio

        output_versions = []
        feedback_history = []

        for attempt in range(self.config.max_retries):
            logger.info(f"[迭代-异步] {node_name} 第 {attempt + 1} 次尝试")

            try:
                # 异步执行
                output = await executor(context)

                # 记录版本
                version_id = f"v{attempt + 1}-{int(time.time() * 1000)}"
                output_versions.append(version_id)

                # 校验
                passed, hint = validator(output)

                if passed:
                    return IterationResult(
                        success=True,
                        output=output,
                        attempts=attempt + 1,
                        versions=output_versions,
                        feedback_history=feedback_history
                    )

                feedback_history.append(hint)

                if self.config.enable_feedback_injection and hint:
                    correction_prompt = f"请修正以下问题: {hint}"
                    if 'correction_feedback' not in context:
                        context['correction_feedback'] = []
                    context['correction_feedback'].append({'attempt': attempt + 1, 'hint': hint})
                    context['last_correction'] = correction_prompt

            except Exception as e:
                logger.error(f"[迭代异常] {node_name}: {e}")
                feedback_history.append(f"执行异常: {str(e)}")

        return IterationResult(
            success=False,
            attempts=self.config.max_retries,
            versions=output_versions,
            error=feedback_history[-1] if feedback_history else "未知错误",
            feedback_history=feedback_history
        )

# 辅助函数
def default_validator(output: Any) -> tuple:
    """默认校验器"""
    if output is None:
        return False, "输出为空"
    if isinstance(output, str) and len(output.strip()) < 10:
        return False, "输出内容过短"
    return True, None

# 测试
if __name__ == "__main__":
    loop = IterationLoop(LoopConfig(max_retries=3))

    attempt_count = [0]  # 闭包计数器

    def mock_executor(ctx):
        attempt_count[0] += 1
        print(f"  执行第 {attempt_count[0]} 次...")
        if attempt_count[0] < 3:
            return f"这是第 {attempt_count[0]} 次的输出，内容太短"
        return "这是第3次输出，内容已经足够长，能够通过校验"

    def mock_validator(output):
        if len(output) > 20:
            return True, None
        return False, "输出内容必须超过20个字符"

    result = loop.run("test_node", mock_executor, mock_validator, {})

    print(f"\n结果:")
    print(f"  成功: {result.success}")
    print(f"  尝试次数: {result.attempts}")
    print(f"  版本: {result.versions}")
    print(f"  反馈历史: {result.feedback_history}")
    if result.output:
        print(f"  最终输出: {result.output}")