"""
AC AI Bus - AI 协作总线

核心规则：
1. 所有 AI 必须通过 AC Bus 中转通信，不得点对点直接通信
2. 所有消息都被记录和路由
3. AC 本身不可被任何 AI 修改（只读审计）

消息流：
AI A → AC Bus → AI B
       ↓
    审计日志
"""

import json
import sqlite3
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class AIMessageType(str, Enum):
    REQUEST = "request"              # 请求
    RESPONSE = "response"           # 响应
    EVENT = "event"                 # 事件
    BROADCAST = "broadcast"         # 广播
    HEARTBEAT = "heartbeat"         # 心跳


class AIPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class AIMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    orchestration_id: Optional[str] = Field(default=None, description="编排ID，用于追踪协作任务")
    message_type: AIMessageType = Field(..., description="消息类型")
    source_ai: str = Field(..., description="源 AI")
    target_ai: Optional[str] = Field(default=None, description="目标 AI，None 则广播")
    priority: AIPriority = Field(default=AIPriority.NORMAL)

    action: str = Field(..., description="动作，如 code_generation, governance_check")
    payload: Dict[str, Any] = Field(default_factory=dict, description="消息内容")

    reply_to: Optional[str] = Field(default=None, description="回复消息ID")
    in_response_to: Optional[str] = Field(default=None, description="回复的消息ID")

    trace_id: Optional[str] = Field(default=None, description="追踪ID")
    parent_span_id: Optional[str] = Field(default=None, description="父 Span ID")

    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = Field(default=None, description="过期时间")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AIRouteResult(BaseModel):
    success: bool
    message_id: str
    delivered_to: List[str]
    failed_to: List[str]
    error: Optional[str] = None


class AIAuditEntry(BaseModel):
    message_id: str
    orchestration_id: Optional[str]
    source_ai: str
    target_ai: Optional[str]
    action: str
    message_type: AIMessageType
    payload_preview: str
    status: str
    created_at: str
    delivered_at: Optional[str] = None
    error: Optional[str] = None


class AIAudit:
    """AI 消息审计日志"""

    def __init__(self, db_path: str = "ai_audit.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT NOT NULL,
                    orchestration_id TEXT,
                    source_ai TEXT NOT NULL,
                    target_ai TEXT,
                    action TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    payload_preview TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    delivered_at TEXT,
                    error TEXT
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_orchestration
                ON ai_audit(orchestration_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_source
                ON ai_audit(source_ai)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_created
                ON ai_audit(created_at)
            """)

    def log(self, entry: AIAuditEntry):
        """记录审计日志"""
        with sqlite3.connect(self.db_path) as conn:
            payload_preview = entry.payload_preview[:200] if entry.payload_preview else ""

            conn.execute("""
                INSERT INTO ai_audit
                (message_id, orchestration_id, source_ai, target_ai, action,
                 message_type, payload_preview, status, created_at, delivered_at, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.message_id,
                entry.orchestration_id,
                entry.source_ai,
                entry.target_ai,
                entry.action,
                entry.message_type.value,
                payload_preview,
                entry.status,
                entry.created_at,
                entry.delivered_at,
                entry.error
            ))

    def query(
        self,
        orchestration_id: Optional[str] = None,
        source_ai: Optional[str] = None,
        limit: int = 100
    ) -> List[AIAuditEntry]:
        """查询审计日志"""
        query = "SELECT * FROM ai_audit WHERE 1=1"
        params: List[Any] = []

        if orchestration_id:
            query += " AND orchestration_id = ?"
            params.append(orchestration_id)

        if source_ai:
            query += " AND source_ai = ?"
            params.append(source_ai)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return [
                AIAuditEntry(
                    message_id=row[1],
                    orchestration_id=row[2],
                    source_ai=row[3],
                    target_ai=row[4],
                    action=row[5],
                    message_type=AIMessageType(row[6]),
                    payload_preview=row[7],
                    status=row[8],
                    created_at=row[9],
                    delivered_at=row[10],
                    error=row[11]
                )
                for row in cursor
            ]


class AIHandlers:
    """AI 消息处理器注册表"""

    def __init__(self):
        self._handlers: Dict[str, Dict[str, Callable]] = {}

    def register(self, ai_id: str, action: str, handler: Callable):
        """注册处理器"""
        if ai_id not in self._handlers:
            self._handlers[ai_id] = {}

        self._handlers[ai_id][action] = handler

    def get_handler(self, ai_id: str, action: str) -> Optional[Callable]:
        """获取处理器"""
        if ai_id in self._handlers:
            return self._handlers[ai_id].get(action)
        return None

    def get_ai_handlers(self, ai_id: str) -> Dict[str, Callable]:
        """获取 AI 的所有处理器"""
        return self._handlers.get(ai_id, {})


class ACAIBus:
    """
    AC AI Bus - AI 协作总线

    核心功能：
    1. 消息路由（publish/subscribe + 点对点）
    2. 审计日志（所有消息都被记录）
    3. 编排追踪（支持 orchestration_id）
    4. 冲突检测（当多个 AI 对同一实体产生矛盾结论时）
    """

    def __init__(
        self,
        registry_db: str = "ai_registry.db",
        audit_db: str = "ai_audit.db"
    ):
        from ai_registry import AIRegistry

        self.registry = AIRegistry(registry_db)
        self.audit = AIAudit(audit_db)
        self.handlers = AIHandlers()

        self._subscriptions: Dict[str, List[str]] = {}
        self._in_flight: Dict[str, AIMessage] = {}

        self._legitimate_senders: set = {
            "api",
            "websocket",
            "hermes_conversation",
            "trae_editor",
            "trae",
            "subagent_executor",
            "opencode",
            "ac_server",
            "cli",
        }

    def add_legitimate_sender(self, sender: str):
        """添加合法发送者到白名单"""
        self._legitimate_senders.add(sender)

    def is_sender_legitimate(self, sender: str) -> bool:
        """检查发送者是否在白名单中"""
        return sender in self._legitimate_senders

    def subscribe(self, ai_id: str, actions: List[str]):
        """订阅动作"""
        for action in actions:
            if action not in self._subscriptions:
                self._subscriptions[action] = []

            if ai_id not in self._subscriptions[action]:
                self._subscriptions[action].append(ai_id)

    def unsubscribe(self, ai_id: str, actions: Optional[List[str]] = None):
        """取消订阅"""
        if actions is None:
            for action in self._subscriptions:
                if ai_id in self._subscriptions[action]:
                    self._subscriptions[action].remove(ai_id)
        else:
            for action in actions:
                if action in self._subscriptions and ai_id in self._subscriptions[action]:
                    self._subscriptions[action].remove(ai_id)

    def publish(self, message: AIMessage) -> AIRouteResult:
        """
        发布消息

        规则：
        1. 所有消息必须先经过审计
        2. 发送者必须在白名单中
        3. 目标 AI 必须在 Registry 中注册
        4. 广播消息发送给所有订阅者
        """
        if not self.is_sender_legitimate(message.source_ai):
            print(f"[AIBus] 拒绝非法发送者: {message.source_ai}")
            return AIRouteResult(
                success=False,
                message_id=message.message_id,
                delivered_to=[],
                failed_to=[],
                error=f"发送者 {message.source_ai} 不在白名单中"
            )

        message_id = message.message_id
        self._in_flight[message_id] = message

        self.registry.update_last_seen(message.source_ai)

        audit_entry = AIAuditEntry(
            message_id=message_id,
            orchestration_id=message.orchestration_id,
            source_ai=message.source_ai,
            target_ai=message.target_ai,
            action=message.action,
            message_type=message.message_type,
            payload_preview=json.dumps(message.payload)[:200],
            status="published",
            created_at=message.created_at
        )
        self.audit.log(audit_entry)

        delivered_to = []
        failed_to = []

        if message.target_ai:
            target = self.registry.get(message.target_ai)
            if target:
                delivered_to = [message.target_ai]
                self._deliver(message, message.target_ai)
            else:
                failed_to = [message.target_ai]

        elif message.message_type == AIMessageType.BROADCAST:
            if message.action in self._subscriptions:
                for ai_id in self._subscriptions[message.action]:
                    if ai_id != message.source_ai:
                        self._deliver(message, ai_id)
                        delivered_to.append(ai_id)

        elif message.action in self._subscriptions:
            for ai_id in self._subscriptions[message.action]:
                if ai_id != message.source_ai:
                    self._deliver(message, ai_id)
                    delivered_to.append(ai_id)

        audit_entry.status = "delivered"
        audit_entry.delivered_at = datetime.now().isoformat()
        audit_entry.target_ai = ", ".join(delivered_to) if delivered_to else message.target_ai
        self.audit.log(audit_entry)

        self._in_flight.pop(message_id, None)

        return AIRouteResult(
            success=len(failed_to) == 0,
            message_id=message_id,
            delivered_to=delivered_to,
            failed_to=failed_to,
            error=f"目标 AI 不存在: {failed_to}" if failed_to else None
        )

    def _deliver(self, message: AIMessage, target_ai: str):
        """投递消息到目标 AI"""
        handler = self.handlers.get_handler(target_ai, message.action)

        if handler:
            try:
                handler(message)
                self.registry.update_last_seen(target_ai)
            except Exception as e:
                print(f"[AIBus] 投递错误 {target_ai}: {e}")

    def request(
        self,
        source_ai: str,
        target_ai: str,
        action: str,
        payload: Dict[str, Any],
        orchestration_id: Optional[str] = None,
        priority: AIPriority = AIPriority.NORMAL,
        timeout_seconds: float = 30.0
    ) -> AIMessage:
        """
        点对点请求（带响应）

        AI A 调用此方法向 AI B 发送请求
        AC 记录后转发给 B，B 的结果也经 AC 返回
        """
        message = AIMessage(
            message_type=AIMessageType.REQUEST,
            source_ai=source_ai,
            target_ai=target_ai,
            action=action,
            payload=payload,
            orchestration_id=orchestration_id,
            priority=priority,
            trace_id=uuid.uuid4().hex
        )

        self.publish(message)

        return message

    def broadcast(
        self,
        source_ai: str,
        action: str,
        payload: Dict[str, Any],
        orchestration_id: Optional[str] = None
    ) -> AIRouteResult:
        """广播消息"""
        message = AIMessage(
            message_type=AIMessageType.BROADCAST,
            source_ai=source_ai,
            action=action,
            payload=payload,
            orchestration_id=orchestration_id
        )

        return self.publish(message)

    def check_conflict(
        self,
        entity_id: str,
        conclusion_a: str,
        conclusion_b: str
    ) -> bool:
        """
        检测冲突

        当多个 AI 对同一实体产生矛盾结论时，返回 True
        """
        if conclusion_a == conclusion_b:
            return False

        audit_entry = AIAuditEntry(
            message_id=uuid.uuid4().hex,
            orchestration_id=None,
            source_ai="system",
            target_ai=None,
            action="conflict_detected",
            message_type=AIMessageType.EVENT,
            payload_preview=f"实体 {entity_id} 存在冲突: {conclusion_a} vs {conclusion_b}",
            status="conflict",
            created_at=datetime.now().isoformat(),
            error=f"冲突检测: {conclusion_a} != {conclusion_b}"
        )
        self.audit.log(audit_entry)

        print(f"[AIBus] 冲突检测: 实体 {entity_id}")
        print(f"  结论 A: {conclusion_a}")
        print(f"  结论 B: {conclusion_b}")

        return True

    def get_trace(self, orchestration_id: str) -> List[AIAuditEntry]:
        """获取编排追踪"""
        return self.audit.query(orchestration_id=orchestration_id)


ai_bus = ACAIBus()


def register_ai_handler(ai_id: str, action: str, handler: Callable):
    """注册 AI 消息处理器的便捷函数"""
    ai_bus.handlers.register(ai_id, action, handler)


if __name__ == "__main__":
    from ai_registry import AIRegistry, bootstrap_registry

    print("=" * 60)
    print("  AC AI Bus 初始化")
    print("=" * 60)

    registry = bootstrap_registry()
    bus = ACAIBus()

    bus.subscribe("trae_editor", ["code_generation", "code_review"])
    bus.subscribe("subagent_executor", ["code_generation", "architecture_design"])

    print("\n订阅关系：")
    for action, subscribers in bus._subscriptions.items():
        print(f"  {action}: {subscribers}")

    print("\n测试消息发布：")
    result = bus.publish(AIMessage(
        message_type=AIMessageType.BROADCAST,
        source_ai="hermes_conversation",
        action="governance_check",
        payload={"content": "测试代码"}
    ))

    print(f"  结果: {result.success}")
    print(f"  投递到: {result.delivered_to}")
