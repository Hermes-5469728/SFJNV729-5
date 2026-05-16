"""
Agent Connector - Agent连接管理
负责与外部Agent建立和管理连接

功能：
- Agent注册与发现
- 连接池管理
- 消息发送与接收
"""

import asyncio
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from loguru import logger

from .a2a_protocol import A2AMessage, MessageStatus, MessageType, get_a2a_protocol

@dataclass
class AgentConnection:
    """Agent连接状态"""
    agent_id: str
    endpoint: str
    connected: bool = False
    last_heartbeat: str = ""
    message_count: int = 0

class AgentConnector:
    """Agent连接器"""

    def __init__(self):
        self.connections: Dict[str, AgentConnection] = {}
        self.protocol = get_a2a_protocol()
        logger.info("Agent连接器初始化完成")

    def connect(self, agent_id: str, endpoint: str) -> bool:
        """建立连接"""
        try:
            # 模拟连接建立
            self.connections[agent_id] = AgentConnection(
                agent_id=agent_id,
                endpoint=endpoint,
                connected=True,
                last_heartbeat=asyncio.get_event_loop().time()
            )
            logger.info(f"已连接: {agent_id} -> {endpoint}")
            return True
        except Exception as e:
            logger.error(f"连接失败 {agent_id}: {e}")
            return False

    def disconnect(self, agent_id: str):
        """断开连接"""
        if agent_id in self.connections:
            self.connections[agent_id].connected = False
            logger.info(f"已断开: {agent_id}")

    async def send_message(self, message: A2AMessage) -> bool:
        """发送消息"""
        connection = self.connections.get(message.receiver_id)
        if not connection or not connection.connected:
            logger.error(f"发送失败: 未连接到 {message.receiver_id}")
            return False

        try:
            # 模拟发送
            serialized = self.protocol.serialize(message)
            logger.debug(f"发送消息: {message.message_id} -> {message.receiver_id}")

            # 更新连接状态
            connection.message_count += 1
            connection.last_heartbeat = asyncio.get_event_loop().time()

            return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    async def receive_message(self, data: str) -> A2AMessage:
        """接收消息"""
        try:
            message = self.protocol.deserialize(data)
            logger.debug(f"接收消息: {message.message_id} from {message.sender_id}")
            return message
        except Exception as e:
            logger.error(f"接收消息失败: {e}")
            raise

    async def send_heartbeat(self, agent_id: str) -> bool:
        """发送心跳"""
        connection = self.connections.get(agent_id)
        if not connection:
            return False

        heartbeat = self.protocol.create_message(
            sender_id="gateway",
            receiver_id=agent_id,
            task_id="heartbeat",
            content={"action": "ping"},
            message_type=MessageType.HEARTBEAT
        )

        return await self.send_message(heartbeat)

    def is_connected(self, agent_id: str) -> bool:
        """检查连接状态"""
        conn = self.connections.get(agent_id)
        return conn.connected if conn else False

    def get_connection_status(self, agent_id: str) -> Optional[dict]:
        """获取连接状态"""
        conn = self.connections.get(agent_id)
        if conn:
            return {
                "agent_id": conn.agent_id,
                "endpoint": conn.endpoint,
                "connected": conn.connected,
                "message_count": conn.message_count
            }
        return None

# 全局连接器实例
_connector = None

def get_connector() -> AgentConnector:
    """获取连接器单例"""
    global _connector
    if _connector is None:
        _connector = AgentConnector()
    return _connector

# 测试
if __name__ == "__main__":
    async def test():
        connector = get_connector()

        # 建立连接
        connector.connect("agent-coder", "http://localhost:8000/coder")
        connector.connect("agent-reviewer", "http://localhost:8000/reviewer")

        # 发送消息
        protocol = get_a2a_protocol()
        msg = protocol.create_message(
            sender_id="agent-coder",
            receiver_id="agent-reviewer",
            task_id="task-001",
            content={"code": "def hello(): pass"}
        )

        success = await connector.send_message(msg)
        print(f"发送成功: {success}")

        # 检查状态
        status = connector.get_connection_status("agent-coder")
        print(f"连接状态: {status}")

    asyncio.run(test())