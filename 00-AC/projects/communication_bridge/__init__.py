"""
AI智能体沟通桥 - A2A通信协议实现

核心组件：
- a2a_protocol: A2A协议实现
- api_gateway: 通信网关
- agent_connector: Agent连接器
- security: 安全认证模块

使用示例：
```python
from communication_bridge import get_gateway, get_security_manager

# 初始化
gateway = get_gateway()
security = get_security_manager()

# 创建身份
coder = security.create_identity("代码Agent")
reviewer = security.create_identity("评审Agent")

# 注册端点
gateway.register_endpoint(coder.agent_id, "http://localhost:8000/coder")
gateway.register_endpoint(reviewer.agent_id, "http://localhost:8000/reviewer")

# 发送消息
protocol = get_a2a_protocol()
msg = protocol.create_message(
    sender_id=coder.agent_id,
    receiver_id=reviewer.agent_id,
    task_id="task-001",
    content={"code": "def hello(): pass"}
)

result = await gateway.route_message(msg)
```
"""

from .a2a_protocol import A2AMessage, MessageStatus, MessageType, get_a2a_protocol
from .api_gateway import A2AGateway, get_gateway
from .agent_connector import AgentConnector, get_connector
from .security import SecurityManager, get_security_manager, AgentIdentity

__all__ = [
    # Protocol
    'A2AMessage',
    'MessageStatus',
    'MessageType',
    'get_a2a_protocol',
    # Gateway
    'A2AGateway',
    'get_gateway',
    # Connector
    'AgentConnector',
    'get_connector',
    # Security
    'SecurityManager',
    'get_security_manager',
    'AgentIdentity',
]

__version__ = "1.0.0"