"""
HLinkRouter - 双路径路由器
根据意图类型决定走 FastPath（简单查询）还是 StateMachine（复杂任务）

FastPath 白名单：
- medical_drug_check / medical_interaction / medical_guideline / medical_score
- simple_rag_query / knowledge_lookup
- personal_profile / personal_tracker

其他意图走 StateMachine
"""

from typing import Dict, Any, Optional, Callable, Tuple
from enum import Enum
from loguru import logger

class RouteType(Enum):
    """路由类型"""
    FAST_PATH = "FAST_PATH"      # 简单查询，现有线性管道
    STATE_MACHINE = "STATE_MACHINE"  # 复杂任务，状态机处理

class HLinkRouter:
    """双路径路由器"""

    # FastPath 白名单（简单查询，<10ms）
    FAST_PATH_INTENTS = {
        "medical_drug_check",
        "medical_interaction",
        "medical_guideline",
        "medical_score",
        "simple_rag_query",
        "knowledge_lookup",
        "personal_profile",
        "personal_tracker",
    }

    def __init__(self):
        self.fast_path_handlers: Dict[str, Callable] = {}
        self.state_machine_handlers: Dict[str, Callable] = {}
        logger.info("HLinkRouter初始化")

    def register_fast_path(self, intent: str, handler: Callable) -> 'HLinkRouter':
        """注册FastPath处理器"""
        self.fast_path_handlers[intent] = handler
        logger.debug(f"注册FastPath: {intent}")
        return self

    def register_state_machine(self, intent: str, handler: Callable) -> 'HLinkRouter':
        """注册StateMachine处理器"""
        self.state_machine_handlers[intent] = handler
        logger.debug(f"注册StateMachine: {intent}")
        return self

    def route(self, intent: str, context: Dict[str, Any]) -> Tuple[RouteType, Any]:
        """
        执行路由

        :param intent: 意图类型
        :param context: 执行上下文
        :return: (路由类型, 处理结果)
        """
        logger.info(f"[路由] 意图: {intent}")

        # 检查是否在FastPath白名单
        if intent in self.FAST_PATH_INTENTS:
            logger.info(f"[路由] -> FastPath (<10ms)")
            return RouteType.FAST_PATH, self._handle_fast_path(intent, context)
        else:
            logger.info(f"[路由] -> StateMachine")
            return RouteType.STATE_MACHINE, self._handle_state_machine(intent, context)

    def _handle_fast_path(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理FastPath请求"""
        handler = self.fast_path_handlers.get(intent)
        if handler:
            try:
                result = handler(context)
                return {
                    "route": RouteType.FAST_PATH.value,
                    "intent": intent,
                    "result": result,
                    "latency_ms": 0  # FastPath要求<10ms
                }
            except Exception as e:
                logger.error(f"FastPath处理异常: {e}")
                return {
                    "route": RouteType.FAST_PATH.value,
                    "intent": intent,
                    "error": str(e),
                    "latency_ms": 0
                }
        else:
            # 默认处理器
            return {
                "route": RouteType.FAST_PATH.value,
                "intent": intent,
                "result": f"[FastPath默认响应] 意图: {intent}",
                "latency_ms": 5
            }

    def _handle_state_machine(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理StateMachine请求"""
        handler = self.state_machine_handlers.get(intent)
        if handler:
            try:
                result = handler(context)
                return {
                    "route": RouteType.STATE_MACHINE.value,
                    "intent": intent,
                    "result": result
                }
            except Exception as e:
                logger.error(f"StateMachine处理异常: {e}")
                return {
                    "route": RouteType.STATE_MACHINE.value,
                    "intent": intent,
                    "error": str(e)
                }
        else:
            return {
                "route": RouteType.STATE_MACHINE.value,
                "intent": intent,
                "result": f"[StateMachine默认响应] 意图: {intent}"
            }

    def is_fast_path(self, intent: str) -> bool:
        """判断是否为FastPath"""
        return intent in self.FAST_PATH_INTENTS

# 全局实例
_hlink_router = None

def get_hlink_router() -> HLinkRouter:
    """获取HLinkRouter单例"""
    global _hlink_router
    if _hlink_router is None:
        _hlink_router = HLinkRouter()
    return _hlink_router

# 测试
if __name__ == "__main__":
    router = get_hlink_router()

    # 注册处理器
    def drug_check_handler(ctx):
        return {"drug": "华法林", "result": "与阿司匹林存在相互作用"}

    def code_gen_handler(ctx):
        return {"task": "代码生成", "status": "completed"}

    router.register_fast_path("medical_drug_check", drug_check_handler)
    router.register_state_machine("code_generation", code_gen_handler)

    # 测试路由
    test_intents = [
        "medical_drug_check",  # FastPath
        "medical_interaction",  # FastPath
        "code_generation",     # StateMachine
        "ppt_generation",      # StateMachine
    ]

    print("路由测试:")
    print("=" * 50)
    for intent in test_intents:
        route_type, result = router.route(intent, {})
        print(f"\n意图: {intent}")
        print(f"路由: {route_type.value}")
        print(f"结果: {result}")
        print("-" * 50)