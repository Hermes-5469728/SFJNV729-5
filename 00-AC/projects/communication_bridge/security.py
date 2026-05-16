"""
Security Module - 安全认证模块
负责Agent身份认证和权限管理

功能：
- 数字身份管理
- API密钥认证
- 动态群组隔离
- 消息加密
"""

import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from loguru import logger

@dataclass
class AgentIdentity:
    """Agent数字身份"""
    agent_id: str
    name: str
    api_key: str
    permissions: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: str = field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())

@dataclass
class SecurityGroup:
    """动态安全群组"""
    group_id: str
    name: str
    members: List[str] = field(default_factory=list)  # agent_ids
    permissions: List[str] = field(default_factory=list)
    isolation_enabled: bool = True

class SecurityManager:
    """安全管理器"""

    def __init__(self):
        self.identities: Dict[str, AgentIdentity] = {}  # agent_id -> identity
        self.api_keys: Dict[str, str] = {}  # api_key -> agent_id
        self.groups: Dict[str, SecurityGroup] = {}  # group_id -> group
        logger.info("安全管理器初始化完成")

    def create_identity(self, name: str, permissions: List[str] = None) -> AgentIdentity:
        """创建Agent身份"""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        api_key = f"sk-{uuid.uuid4().hex}"

        identity = AgentIdentity(
            agent_id=agent_id,
            name=name,
            api_key=api_key,
            permissions=permissions or []
        )

        self.identities[agent_id] = identity
        self.api_keys[api_key] = agent_id
        logger.info(f"创建身份: {name} ({agent_id})")

        return identity

    def authenticate(self, api_key: str) -> Optional[AgentIdentity]:
        """API密钥认证"""
        agent_id = self.api_keys.get(api_key)
        if agent_id:
            identity = self.identities.get(agent_id)
            if identity and identity.enabled:
                return identity
        return None

    def authorize(self, agent_id: str, permission: str) -> bool:
        """权限校验"""
        identity = self.identities.get(agent_id)
        if not identity or not identity.enabled:
            return False
        return permission in identity.permissions or "*" in identity.permissions

    def create_group(self, name: str, members: List[str] = None) -> SecurityGroup:
        """创建安全群组"""
        group_id = f"group-{uuid.uuid4().hex[:8]}"

        group = SecurityGroup(
            group_id=group_id,
            name=name,
            members=members or [],
            isolation_enabled=True
        )

        self.groups[group_id] = group
        logger.info(f"创建群组: {name} ({group_id})")

        return group

    def add_to_group(self, group_id: str, agent_id: str):
        """添加到群组"""
        group = self.groups.get(group_id)
        if group and agent_id not in group.members:
            group.members.append(agent_id)
            logger.info(f"添加到群组: {agent_id} -> {group_id}")

    def remove_from_group(self, group_id: str, agent_id: str):
        """从群组移除"""
        group = self.groups.get(group_id)
        if group and agent_id in group.members:
            group.members.remove(agent_id)
            logger.info(f"从群组移除: {agent_id} -> {group_id}")

    def can_communicate(self, sender_id: str, receiver_id: str) -> bool:
        """检查是否可以通信"""
        # 检查双方是否存在
        if sender_id not in self.identities or receiver_id not in self.identities:
            return False

        # 检查是否在同一群组（隔离模式下）
        for group in self.groups.values():
            if group.isolation_enabled:
                sender_in_group = sender_id in group.members
                receiver_in_group = receiver_id in group.members
                # 隔离模式下，只有同组成员才能通信
                if sender_in_group != receiver_in_group:
                    return False

        return True

# 全局安全管理器实例
_security_manager = None

def get_security_manager() -> SecurityManager:
    """获取安全管理器单例"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager

# 测试
if __name__ == "__main__":
    security = get_security_manager()

    # 创建身份
    coder = security.create_identity("代码Agent", ["code_write", "code_read"])
    reviewer = security.create_identity("评审Agent", ["code_review"])

    print(f"代码Agent: {coder.agent_id}, API Key: {coder.api_key[:10]}...")
    print(f"评审Agent: {reviewer.agent_id}, API Key: {reviewer.api_key[:10]}...")

    # 认证测试
    auth_result = security.authenticate(coder.api_key)
    print(f"\n认证结果: {auth_result.name if auth_result else '失败'}")

    # 权限测试
    has_permission = security.authorize(coder.agent_id, "code_write")
    print(f"代码Agent有code_write权限: {has_permission}")

    # 创建群组
    group = security.create_group("代码审查组", [coder.agent_id, reviewer.agent_id])
    print(f"\n创建群组: {group.name} ({group.group_id})")

    # 通信检查
    can_comm = security.can_communicate(coder.agent_id, reviewer.agent_id)
    print(f"可以通信: {can_comm}")