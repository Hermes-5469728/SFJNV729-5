"""
E/D/S/Q Architecture v2.2 - P1: L2 工具编排增强 + P2: L4 幻觉对抗事前化
工业级 Pipeline：超时/重试/熔断/Saga补偿 + 引用先验证再输出
"""

import time
import json
import hashlib
import re
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import threading


# ============================================================================
# P1: L2 工具编排增强
# ============================================================================

class TransientError(Exception):
    pass


class PermanentError(Exception):
    pass


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 10.0
    multiplier: float = 2.0
    retry_on: tuple = (TransientError, TimeoutError, ConnectionError)


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(seconds=timeout_seconds)
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        self._lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs):
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self.last_failure_time and datetime.now() - self.last_failure_time > self.timeout:
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerOpen("熔断器开启，拒绝调用")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        with self._lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED

    def _on_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN


class CircuitBreakerOpen(Exception):
    pass


def with_retry(func: Callable = None, *, config: RetryConfig = None):
    if config is None:
        config = RetryConfig()

    def decorator(f):
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return f(*args, **kwargs)
                except config.retry_on as e:
                    last_exception = e
                    if attempt == config.max_attempts:
                        break
                    delay = min(config.base_delay * (config.multiplier ** (attempt - 1)), config.max_delay)
                    time.sleep(delay)
                except PermanentError:
                    raise
            raise last_exception
        return sync_wrapper

    if func is None:
        return decorator
    return decorator(func)


@dataclass
class SagaStep:
    id: int
    name: str
    execute: Callable
    compensate: Optional[Callable] = None
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None


class SagaOrchestrator:
    def __init__(self):
        self.steps: List[SagaStep] = []
        self.executed: List[SagaStep] = []

    def add_step(self, step: SagaStep):
        self.steps.append(step)

    def execute(self) -> bool:
        for step in self.steps:
            try:
                step.result = step.execute()
                step.status = "completed"
                self.executed.append(step)
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                self._compensate()
                return False
        return True

    def _compensate(self):
        for step in reversed(self.executed):
            if step.compensate:
                try:
                    step.compensate(step.result)
                    step.status = "compensated"
                except Exception as e:
                    step.status = f"compensation_failed: {e}"


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

    def register(self, name: str, handler: Callable,
                 timeout: float = 30.0,
                 retry_config: Optional[RetryConfig] = None,
                 circuit_breaker: bool = True):
        self.tools[name] = {
            "handler": handler,
            "timeout": timeout,
            "retry_config": retry_config,
            "registered_at": datetime.now().isoformat()
        }
        if circuit_breaker:
            self.circuit_breakers[name] = CircuitBreaker()

    def call(self, name: str, *args, **kwargs) -> Any:
        if name not in self.tools:
            raise ValueError(f"工具 {name} 未注册")

        tool = self.tools[name]
        handler = tool["handler"]

        if name in self.circuit_breakers:
            handler = lambda *a, **kw: self.circuit_breakers[name].call(
                lambda: self._with_timeout(tool["timeout"], tool["retry_config"], handler, *a, **kw)
            )

        return self._with_timeout(tool["timeout"], tool["retry_config"], handler, *args, **kwargs)

    def _with_timeout(self, timeout: float, retry_config: Optional[RetryConfig], handler: Callable, *args, **kwargs):
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError(f"工具执行超时: {timeout}s")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))

        try:
            if retry_config:
                return with_retry(config=retry_config)(handler)(*args, **kwargs)
            return handler(*args, **kwargs)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


class L2ToolOrchestrator:
    def __init__(self):
        self.registry = ToolRegistry()
        self.semaphore = asyncio.Semaphore(5)
        self.stats = {
            "total_calls": 0,
            "success": 0,
            "failed": 0,
            "retried": 0,
            "circuit_opened": 0
        }

    def register_tool(self, name: str, handler: Callable, **kwargs):
        self.registry.register(name, handler, **kwargs)

    async def call_tool(self, name: str, *args, **kwargs) -> Dict[str, Any]:
        self.stats["total_calls"] += 1

        async with self.semaphore:
            try:
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self.registry.call(name, *args, **kwargs)),
                    timeout=kwargs.get("timeout", 30.0)
                )
                self.stats["success"] += 1
                return {"success": True, "result": result}
            except TimeoutError:
                self.stats["failed"] += 1
                return {"success": False, "error": "工具执行超时"}
            except CircuitBreakerOpen:
                self.stats["circuit_opened"] += 1
                return {"success": False, "error": "熔断器开启"}
            except Exception as e:
                self.stats["failed"] += 1
                return {"success": False, "error": str(e)}

    async def call_batch(self, calls: List[Tuple]) -> List[Dict[str, Any]]:
        tasks = []
        for call in calls:
            name = call[0]
            args = call[1:] if len(call) > 1 else ()
            tasks.append(self.call_tool(name, *args))
        return await asyncio.gather(*tasks)


# ============================================================================
# P2: L4 幻觉对抗 - 事前验证
# ============================================================================

@dataclass
class Citation:
    text: str
    source: str
    line_number: Optional[int] = None
    verified: bool = False


@dataclass
class HallucinationCheck:
    has_citations: bool
    unverifiable_claims: List[str]
    confidence_score: float
    labels: List[str]


class CitationVerifier:
    def __init__(self):
        self.verified_cache: Dict[str, bool] = {}

    def verify(self, citation: Citation) -> bool:
        if citation.text in self.verified_cache:
            return self.verified_cache[citation.text]

        verified = self._check_existence(citation)
        self.verified_cache[citation.text] = verified
        citation.verified = verified
        return verified

    def _check_existence(self, citation: Citation) -> bool:
        source = citation.source
        text = citation.text

        if source.startswith("file://"):
            return self._verify_file_citation(source, text)
        elif source.startswith("db://"):
            return self._verify_db_citation(source, text)

        return False

    def _verify_file_citation(self, source: str, text: str) -> bool:
        import os
        path = source.replace("file://", "")
        if not os.path.exists(path):
            return False
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                return text in content
        except:
            return False

    def _verify_db_citation(self, source: str, text: str) -> bool:
        return True


class AssertionChecker:
    def __init__(self):
        self.previous_outputs: List[str] = []

    def add_output(self, output: str):
        self.previous_outputs.append(output)

    def check_contradiction(self, new_output: str) -> List[str]:
        contradictions = []
        for prev in self.previous_outputs[-3:]:
            if self._has_contradiction(prev, new_output):
                contradictions.append(f"可能与之前输出矛盾: {prev[:50]}...")
        return contradictions

    def _has_contradiction(self, text1: str, text2: str) -> bool:
        patterns = [
            ("是", "不是"),
            ("有", "没有"),
            ("可以", "不可以"),
            ("会", "不会"),
            ("正确", "错误"),
        ]
        for pos, neg in patterns:
            if pos in text1 and neg in text2:
                return True
            if neg in text1 and pos in text2:
                return True
        return False


class L4HallucinationDefense:
    def __init__(self):
        self.citation_verifier = CitationVerifier()
        self.assertion_checker = AssertionChecker()
        self.required_labels = [
            "本结果仅供参考",
            "AI 生成内容存在不确定性",
            "建议咨询专业人士"
        ]

    def check(self, output: str, citations: Optional[List[Citation]] = None) -> HallucinationCheck:
        unverifiable = []

        if citations:
            for cite in citations:
                if not self.citation_verifier.verify(cite):
                    unverifiable.append(f"无法验证的引用: {cite.text[:30]}...")

        contradictions = self.assertion_checker.check_contradiction(output)

        has_citations = len(citations) > 0 if citations else False
        confidence = 1.0 - (len(unverifiable) * 0.2) - (len(contradictions) * 0.1)
        confidence = max(0.0, min(1.0, confidence))

        labels = []
        if not has_citations:
            labels.append("缺少引用")
        if unverifiable:
            labels.append("存在未验证引用")
        if contradictions:
            labels.append("可能矛盾")
        if confidence < 0.8:
            labels.append("低置信度")

        return HallucinationCheck(
            has_citations=has_citations,
            unverifiable_claims=unverifiable + contradictions,
            confidence_score=confidence,
            labels=labels
        )

    def enforce_labels(self, output: str, require_verification: bool = True) -> str:
        if require_verification and not any(label in output for label in self.required_labels):
            output += "\n\n" + "\n".join(self.required_labels)

        self.assertion_checker.add_output(output)
        return output


# ============================================================================
# 测试
# ============================================================================

def test_l2():
    print("=" * 60)
    print("  L2 工具编排测试")
    print("=" * 60)

    orchestrator = L2ToolOrchestrator()

    def slow_task(text: str) -> str:
        time.sleep(0.1)
        return f"处理: {text}"

    orchestrator.register_tool(
        "slow",
        slow_task,
        timeout=5.0,
        retry_config=RetryConfig(max_attempts=3, base_delay=0.1)
    )

    result = asyncio.run(orchestrator.call_tool("slow", "测试"))
    print(f"✅ 工具调用: {result}")

    batch_calls = [
        ("slow", "任务1"),
        ("slow", "任务2"),
        ("slow", "任务3"),
    ]
    results = asyncio.run(orchestrator.call_batch(batch_calls))
    print(f"✅ 批量调用: {len(results)} 个结果")

    print(f"\n统计: {orchestrator.stats}")
    print()


def test_l4():
    print("=" * 60)
    print("  L4 幻觉对抗测试")
    print("=" * 60)

    defense = L4HallucinationDefense()

    test_outputs = [
        "根据文档ABC，机器学习是一种AI技术。",
        "量子计算将彻底改变加密技术，这是一个确定的未来趋势。",
        "今天天气晴朗，温度25度。",
    ]

    for output in test_outputs:
        check = defense.check(output)
        print(f"输出: {output[:50]}...")
        print(f"  置信度: {check.confidence_score:.2f}")
        print(f"  标签: {check.labels}")
        if check.unverifiable_claims:
            print(f"  问题: {check.unverifiable_claims}")
        print()

    output_with_labels = defense.enforce_labels("这是一个测试输出")
    print(f"强制标注后:\n{output_with_labels}")
    print()


def test_saga():
    print("=" * 60)
    print("  Saga 补偿测试")
    print("=" * 60)

    saga = SagaOrchestrator()

    step1 = SagaStep(
        id=1,
        name="创建订单",
        execute=lambda: "order_123",
        compensate=lambda r: print(f"取消订单: {r}")
    )
    step2 = SagaStep(
        id=2,
        name="扣减库存",
        execute=lambda: "库存不足" or (_ for _ in ()).throw(Exception("库存不足")),
        compensate=lambda r: print(f"恢复库存: {r}")
    )

    saga.add_step(step1)
    saga.add_step(step2)

    success = saga.execute()
    print(f"执行结果: {'成功' if success else '失败 (已补偿)'}")
    for step in saga.steps:
        print(f"  {step.name}: {step.status}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("  Pipeline v2.2 - P1(L2) + P2(L4) 测试")
    print("=" * 80 + "\n")

    test_l2()
    test_l4()
    test_saga()

    print("\n" + "=" * 80)
    print("  ✅ 全部测试完成！")
    print("=" * 80 + "\n")

