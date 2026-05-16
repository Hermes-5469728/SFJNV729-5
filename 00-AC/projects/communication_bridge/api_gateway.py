"""
A2A API Gateway - AI智能体通信网关
负责消息路由、转发、认证和状态管理

架构：
┌─────────┐     ┌──────────┐     ┌─────────┐
│  Agent  │────→│  Gateway │────→│  Agent  │
│    A    │     │          │     │    B    │
└─────────┘     └──────────┘     └─────────┘
                  │
                  ↓
            ┌───────────┐
            │  消息队列  │
            │  状态存储  │
            └───────────┘
"""

from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from loguru import logger
import asyncio

from .a2a_protocol import A2AMessage, MessageStatus, get_a2a_protocol

@dataclass
class AgentEndpoint:
    """Agent端点配置"""
    agent_id: str
    endpoint: str
    api_key: Optional[str] = None
    enabled: bool = True

@dataclass
class Route:
    """路由规则"""
    sender_id: str
    receiver_id: str
    handler: Callable
    priority: int = 0

class A2AGateway:
    """A2A通信网关"""

    def __init__(self):
        self.endpoints: Dict[str, AgentEndpoint] = {}
        self.routes: List[Route] = []
        self.message_store: Dict[str, A2AMessage] = {}  # message_id -> message
        self.task_store: Dict[str, List[str]] = {}  # task_id -> [message_ids]
        self.protocol = get_a2a_protocol()
        logger.info("A2A网关初始化完成")

    def register_endpoint(self, agent_id: str, endpoint: str, api_key: str = None) -> 'A2AGateway':
        """注册Agent端点"""
        self.endpoints[agent_id] = AgentEndpoint(
            agent_id=agent_id,
            endpoint=endpoint,
            api_key=api_key,
            enabled=True
        )
        logger.info(f"端点注册: {agent_id} -> {endpoint}")
        return self

    def add_route(self, sender_id: str, receiver_id: str, handler: Callable) -> 'A2AGateway':
        """添加路由规则"""
        self.routes.append(Route(sender_id, receiver_id, handler))
        logger.info(f"路由添加: {sender_id} -> {receiver_id}")
        return self

    def find_endpoint(self, agent_id: str) -> Optional[AgentEndpoint]:
        """查找Agent端点"""
        return self.endpoints.get(agent_id)

    async def route_message(self, message: A2AMessage) -> A2AMessage:
        """路由消息"""
        # 验证消息
        valid, reason = self.protocol.validate(message)
        if not valid:
            message.status = MessageStatus.FAILED
            message.content["error"] = reason
            return message

        # 查找接收方端点
        endpoint = self.find_endpoint(message.receiver_id)
        if not endpoint or not endpoint.enabled:
            message.status = MessageStatus.FAILED
            message.content["error"] = f"接收方不存在或未启用: {message.receiver_id}"
            return message

        # 查找路由处理器
        route = self._find_route(message.sender_id, message.receiver_id)
        if route:
            try:
                # 调用路由处理器
                message.status = MessageStatus.PROCESSING
                result = await route.handler(message)
                message.status = MessageStatus.COMPLETED
                message.content["result"] = result
            except Exception as e:
                logger.error(f"路由处理失败: {e}")
                message.status = MessageStatus.FAILED
                message.content["error"] = str(e)
        else:
            # 默认直接转发
            message.status = MessageStatus.COMPLETED

        # 存储消息
        self._store_message(message)
        return message

    def _find_route(self, sender_id: str, receiver_id: str) -> Optional[Route]:
        """查找匹配的路由"""
        for route in self.routes:
            if route.sender_id == sender_id and route.receiver_id == receiver_id:
                return route
            if route.sender_id == "*" and route.receiver_id == receiver_id:
                return route
            if route.sender_id == sender_id and route.receiver_id == "*":
                return route
        return None

    def _store_message(self, message: A2AMessage):
        """存储消息"""
        self.message_store[message.message_id] = message
        if message.task_id not in self.task_store:
            self.task_store[message.task_id] = []
        self.task_store[message.task_id].append(message.message_id)

    def get_messages_by_task(self, task_id: str) -> List[A2AMessage]:
        """获取任务相关的所有消息"""
        message_ids = self.task_store.get(task_id, [])
        return [self.message_store.get(mid) for mid in message_ids if self.message_store.get(mid)]

    def get_message(self, message_id: str) -> Optional[A2AMessage]:
        """获取单条消息"""
        return self.message_store.get(message_id)

# 全局网关实例
_gateway = None

def get_gateway() -> A2AGateway:
    """获取网关单例"""
    global _gateway
    if _gateway is None:
        _gateway = A2AGateway()
    return _gateway

# 测试
if __name__ == "__main__":
    async def test_route_handler(msg: A2AMessage):
        return {"processed": True, "by": "test_handler"}

    gateway = get_gateway()
    gateway.register_endpoint("agent-coder", "http://localhost:8000/coder")
    gateway.register_endpoint("agent-reviewer", "http://localhost:8000/reviewer")
    gateway.add_route("agent-coder", "agent-reviewer", test_route_handler)

    # 创建测试消息
    protocol = get_a2a_protocol()
    msg = protocol.create_message(
        sender_id="agent-coder",
        receiver_id="agent-reviewer",
        task_id="task-001",
        content={"code": "def hello(): pass"}
    )

    # 路由消息
    result = asyncio.run(gateway.route_message(msg))
    print(f"路由结果: {result.status.value}")
    print(f"消息内容: {result.content}")