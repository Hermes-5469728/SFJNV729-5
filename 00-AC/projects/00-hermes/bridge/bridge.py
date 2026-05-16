"""
A2A 文件桥消息模块
实现 send/reply/check_inbox 功能

使用示例：
```python
from bridge import Bridge

# 初始化桥接器
bridge = Bridge()

# 发送消息
bridge.send("trae", {"action": "request", "data": "..."})

# 检查收件箱
messages = bridge.check_inbox("opencode")

# 回复消息
bridge.reply("msg-id", {"status": "completed", "result": "..."})
```
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class Message:
    """消息结构"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    receiver: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    type: str = "request"
    content: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "timestamp": self.timestamp,
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典解析"""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            sender=data.get("sender", ""),
            receiver=data.get("receiver", ""),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            type=data.get("type", "request"),
            content=data.get("content", {}),
            metadata=data.get("metadata", {})
        )

class Bridge:
    """文件桥接器"""

    def __init__(self, base_path: str = "bridge"):
        self.base_path = base_path
        self.inbox_path = os.path.join(base_path, "inbox")
        self.sent_path = os.path.join(base_path, "sent")
        self.archive_path = os.path.join(base_path, "archive")
        self.blackboard_path = os.path.join(base_path, "blackboard.json")

        # 确保目录存在
        os.makedirs(os.path.join(self.inbox_path, "trae"), exist_ok=True)
        os.makedirs(os.path.join(self.inbox_path, "opencode"), exist_ok=True)
        os.makedirs(self.sent_path, exist_ok=True)
        os.makedirs(self.archive_path, exist_ok=True)

        # 初始化共享状态板
        self._init_blackboard()

    def _init_blackboard(self):
        """初始化共享状态板"""
        if not os.path.exists(self.blackboard_path):
            blackboard = {
                "last_sync": datetime.now().isoformat(),
                "active_tasks": [],
                "completed_tasks": [],
                "pending_actions": []
            }
            with open(self.blackboard_path, 'w', encoding='utf-8') as f:
                json.dump(blackboard, f, ensure_ascii=False, indent=2)

    def send(self, receiver: str, content: Dict[str, Any], 
             message_type: str = "request", **kwargs) -> str:
        """
        发送消息
        
        :param receiver: 接收方（trae/opencode）
        :param content: 消息内容
        :param message_type: 消息类型
        :return: 消息ID
        """
        message = Message(
            sender="opencode" if receiver == "trae" else "trae",
            receiver=receiver,
            type=message_type,
            content=content,
            metadata=kwargs
        )

        # 写入收件箱
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"msg-{date_str}-{message.message_id[:8]}.json"
        inbox_dir = os.path.join(self.inbox_path, receiver)
        filepath = os.path.join(inbox_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(message.to_dict(), f, ensure_ascii=False, indent=2)

        # 记录到已发送
        sent_filepath = os.path.join(self.sent_path, filename)
        with open(sent_filepath, 'w', encoding='utf-8') as f:
            json.dump(message.to_dict(), f, ensure_ascii=False, indent=2)

        # 更新状态板
        self._update_blackboard("sent", message.message_id)

        return message.message_id

    def reply(self, original_message_id: str, content: Dict[str, Any],
              message_type: str = "response") -> str:
        """
        回复消息
        
        :param original_message_id: 原始消息ID
        :param content: 回复内容
        :param message_type: 消息类型
        :return: 回复消息ID
        """
        # 查找原始消息
        original_msg = self._find_message(original_message_id)
        if not original_msg:
            raise ValueError(f"未找到原始消息: {original_message_id}")

        # 发送回复
        return self.send(
            receiver=original_msg.sender,
            content=content,
            message_type=message_type,
            response_to=original_message_id
        )

    def check_inbox(self, receiver: str) -> List[Message]:
        """
        检查收件箱
        
        :param receiver: 接收方（trae/opencode）
        :return: 消息列表
        """
        inbox_dir = os.path.join(self.inbox_path, receiver)
        messages = []

        if os.path.exists(inbox_dir):
            for filename in sorted(os.listdir(inbox_dir)):
                if filename.startswith("msg-") and filename.endswith(".json"):
                    filepath = os.path.join(inbox_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            messages.append(Message.from_dict(data))
                    except Exception as e:
                        print(f"读取消息失败 {filename}: {e}")

        return messages

    def process_message(self, message_id: str):
        """
        处理消息（移到归档）
        
        :param message_id: 消息ID
        """
        # 查找消息
        for receiver in ["trae", "opencode"]:
            inbox_dir = os.path.join(self.inbox_path, receiver)
            if os.path.exists(inbox_dir):
                for filename in os.listdir(inbox_dir):
                    if message_id in filename:
                        src = os.path.join(inbox_dir, filename)
                        dst = os.path.join(self.archive_path, filename)
                        os.rename(src, dst)
                        self._update_blackboard("processed", message_id)
                        return True
        return False

    def _find_message(self, message_id: str) -> Optional[Message]:
        """查找消息"""
        # 在收件箱查找
        for receiver in ["trae", "opencode"]:
            inbox_dir = os.path.join(self.inbox_path, receiver)
            if os.path.exists(inbox_dir):
                for filename in os.listdir(inbox_dir):
                    if message_id in filename:
                        filepath = os.path.join(inbox_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            return Message.from_dict(json.load(f))

        # 在已发送查找
        for filename in os.listdir(self.sent_path):
            if message_id in filename:
                filepath = os.path.join(self.sent_path, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    return Message.from_dict(json.load(f))

        return None

    def _update_blackboard(self, action: str, message_id: str):
        """更新共享状态板"""
        with open(self.blackboard_path, 'r', encoding='utf-8') as f:
            blackboard = json.load(f)

        blackboard["last_sync"] = datetime.now().isoformat()

        if action == "sent":
            blackboard["pending_actions"].append({
                "message_id": message_id,
                "action": "sent",
                "timestamp": datetime.now().isoformat()
            })
        elif action == "processed":
            blackboard["completed_tasks"].append({
                "message_id": message_id,
                "action": "processed",
                "timestamp": datetime.now().isoformat()
            })

        with open(self.blackboard_path, 'w', encoding='utf-8') as f:
            json.dump(blackboard, f, ensure_ascii=False, indent=2)

    def get_blackboard(self) -> Dict[str, Any]:
        """获取共享状态板"""
        with open(self.blackboard_path, 'r', encoding='utf-8') as f:
            return json.load(f)

# 测试
if __name__ == "__main__":
    bridge = Bridge()

    # 发送测试消息
    msg_id = bridge.send("trae", {"action": "test", "message": "Hello from OpenCode!"})
    print(f"发送消息: {msg_id}")

    # 检查收件箱
    messages = bridge.check_inbox("trae")
    print(f"Trae收件箱消息数: {len(messages)}")

    # 检查共享状态板
    blackboard = bridge.get_blackboard()
    print(f"最后同步: {blackboard['last_sync']}")