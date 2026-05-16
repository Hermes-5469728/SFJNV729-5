"""
A2A Protocol - Agent-to-Agent 通信协议实现
遵循行业标准的智能体间通信协议

消息结构：
{
  "message_id": "uuid",
  "sender_id": "agent-xxx",
  "receiver_id": "agent-yyy",
  "task_id": "task-xxx",
  "context": {...},
  "timestamp": "ISO8601",
  "status": "pending/processing/completed/failed"
}
"""

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum

class MessageStatus(Enum):
    """消息状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"

class MessageType(Enum):
    """消息类型"""
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    HEARTBEAT = "heartbeat"

@dataclass
class A2AMessage:
    """A2A协议消息结构"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    receiver_id: str = ""
    task_id: str = ""
    message_type: MessageType = MessageType.REQUEST
    status: MessageStatus = MessageStatus.PENDING
    content: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "task_id": self.task_id,
            "message_type": self.message_type.value,
            "status": self.status.value,
            "content": self.content,
            "context": self.context,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'A2AMessage':
        """从字典解析"""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            sender_id=data.get("sender_id", ""),
            receiver_id=data.get("receiver_id", ""),
            task_id=data.get("task_id", ""),
            message_type=MessageType(data.get("message_type", "request")),
            status=MessageStatus(data.get("status", "pending")),
            content=data.get("content", {}),
            context=data.get("context", {}),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3)
        )

    def is_valid(self) -> bool:
        """验证消息格式"""
        required_fields = ["message_id", "sender_id", "receiver_id", "task_id"]
        return all(getattr(self, f) for f in required_fields)

class A2AProtocol:
    """A2A协议处理器"""

    def __init__(self):
        self.message_queue: List[A2AMessage] = []

    def create_message(self, sender_id: str, receiver_id: str, task_id: str,
                      content: Dict[str, Any], message_type: MessageType = MessageType.REQUEST) -> A2AMessage:
        """创建消息"""
        return A2AMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            task_id=task_id,
            content=content,
            message_type=message_type
        )

    def serialize(self, message: A2AMessage) -> str:
        """序列化消息"""
        import json
        return json.dumps(message.to_dict(), ensure_ascii=False)

    def deserialize(self, data: str) -> A2AMessage:
        """反序列化消息"""
        import json
        return A2AMessage.from_dict(json.loads(data))

    def validate(self, message: A2AMessage) -> tuple:
        """验证消息"""
        if not message.is_valid():
            return False, "缺少必要字段"
        if message.retry_count > message.max_retries:
            return False, "超过最大重试次数"
        return True, "验证通过"

# 全局协议实例
_a2a_protocol = None

def get_a2a_protocol() -> A2AProtocol:
    """获取A2A协议单例"""
    global _a2a_protocol
    if _a2a_protocol is None:
        _a2a_protocol = A2AProtocol()
    return _a2a_protocol

# 测试
if __name__ == "__main__":
    protocol = get_a2a_protocol()

    # 创建消息
    msg = protocol.create_message(
        sender_id="agent-coder",
        receiver_id="agent-reviewer",
        task_id="task-001",
        content={"code": "def hello(): pass", "action": "review"}
    )

    # 序列化
    serialized = protocol.serialize(msg)
    print("序列化消息:", serialized[:200])

    # 反序列化
    deserialized = protocol.deserialize(serialized)
    print("\n反序列化消息:", deserialized.message_id)

    # 验证
    valid, reason = protocol.validate(msg)
    print("验证结果:", valid, reason)