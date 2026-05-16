"""
AI Registry - AI 能力注册表

所有加入系统的 AI 必须在此注册，声明：
- 身份标识 (ai_id)
- 能力类型（代码生成、审查、知识检索等）
- 准入契约（遵循 AC 治理规则、只读/可写等）
"""

import json
import sqlite3
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AIAgentType(str, Enum):
    CONVERSATION = "conversation"      # 对话端（你）
    TRAE = "trae"                      # Trae 编辑器
    SUBAGENT = "subagent"              # SubAgent 执行器
    ORCHESTRATOR = "orchestrator"      # 多 AI 编排器
    GOVERNANCE = "governance"          # 治理模块
    KNOWLEDGE = "knowledge"            # 知识服务
    EXTERNAL = "external"              # 外部 AI


class AIAgentStatus(str, Enum):
    ACTIVE = "active"                  # 运行中
    IDLE = "idle"                      # 空闲
    BUSY = "busy"                      # 忙碌
    OFFLINE = "offline"                 # 离线
    BANNED = "banned"                  # 禁用


class AIAgentCapability(str, Enum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    ARCHITECTURE_DESIGN = "architecture_design"
    KNOWLEDGE_QUERY = "knowledge_query"
    KNOWLEDGE_WRITE = "knowledge_write"
    GOVERNANCE_CHECK = "governance_check"
    ORCHESTRATION = "orchestration"
    FILE_WATCH = "file_watch"
    REASONING = "reasoning"
    CREATIVE = "creative"


class AIAgentContract(str, Enum):
    READ_ONLY = "read_only"            # 只读（只能查询，不能写入）
    READ_WRITE = "read_write"          # 可读写
    GOVERNANCE_ONLY = "governance_only" # 仅治理
    ORCHESTRATOR_ONLY = "orchestrator_only" # 仅编排


class AIRegistryEntry(BaseModel):
    ai_id: str = Field(..., description="AI 唯一标识")
    name: str = Field(..., description="AI 名称")
    agent_type: AIAgentType = Field(..., description="AI 类型")
    capabilities: List[AIAgentCapability] = Field(..., description="能力列表")
    contract: AIAgentContract = Field(..., description="准入契约")
    status: AIAgentStatus = Field(default=AIAgentStatus.OFFLINE, description="状态")
    endpoint: Optional[str] = Field(default=None, description="API 端点")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    registered_at: str = Field(..., description="注册时间")
    last_seen: Optional[str] = Field(default=None, description="最后活跃时间")
    version: str = Field(default="1.0.0", description="版本")


class AIRegistry:
    """
    AI 注册表

    所有加入系统的 AI 必须在此注册
    """

    def __init__(self, db_path: str = "ai_registry.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_agents (
                    ai_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    capabilities TEXT NOT NULL,
                    contract TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'offline',
                    endpoint TEXT,
                    metadata TEXT,
                    registered_at TEXT NOT NULL,
                    last_seen TEXT,
                    version TEXT NOT NULL DEFAULT '1.0.0'
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agents_type
                ON ai_agents(agent_type)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agents_status
                ON ai_agents(status)
            """)

    def register(self, entry: AIRegistryEntry) -> bool:
        """注册 AI"""
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("""
                    INSERT INTO ai_agents
                    (ai_id, name, agent_type, capabilities, contract, status,
                     endpoint, metadata, registered_at, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.ai_id,
                    entry.name,
                    entry.agent_type.value,
                    json.dumps([c.value for c in entry.capabilities]),
                    entry.contract.value,
                    entry.status.value,
                    entry.endpoint,
                    json.dumps(entry.metadata),
                    entry.registered_at,
                    entry.version
                ))
                return True
            except sqlite3.IntegrityError:
                return False

    def unregister(self, ai_id: str) -> bool:
        """注销 AI"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM ai_agents WHERE ai_id = ?",
                (ai_id,)
            )
            return cursor.rowcount > 0

    def update_status(self, ai_id: str, status: AIAgentStatus) -> bool:
        """更新 AI 状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE ai_agents
                SET status = ?, last_seen = ?
                WHERE ai_id = ?
            """, (status.value, datetime.now().isoformat(), ai_id))
            return cursor.rowcount > 0

    def update_last_seen(self, ai_id: str) -> bool:
        """更新最后活跃时间"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE ai_agents
                SET last_seen = ?
                WHERE ai_id = ?
            """, (datetime.now().isoformat(), ai_id))
            return cursor.rowcount > 0

    def get(self, ai_id: str) -> Optional[AIRegistryEntry]:
        """获取 AI 信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM ai_agents WHERE ai_id = ?",
                (ai_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_entry(row)
        return None

    def get_by_type(self, agent_type: AIAgentType) -> List[AIRegistryEntry]:
        """按类型获取 AI"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM ai_agents WHERE agent_type = ?",
                (agent_type.value,)
            )
            return [self._row_to_entry(row) for row in cursor]

    def get_by_capability(self, capability: AIAgentCapability) -> List[AIRegistryEntry]:
        """按能力获取 AI"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM ai_agents")
            results = []
            for row in cursor:
                entry = self._row_to_entry(row)
                if capability in entry.capabilities:
                    results.append(entry)
            return results

    def get_active(self) -> List[AIRegistryEntry]:
        """获取所有活跃 AI"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM ai_agents WHERE status != ?",
                (AIAgentStatus.OFFLINE.value,)
            )
            return [self._row_to_entry(row) for row in cursor]

    def get_all(self) -> List[AIRegistryEntry]:
        """获取所有 AI"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM ai_agents")
            return [self._row_to_entry(row) for row in cursor]

    def bootstrap(self):
        """初始化默认 AI 注册"""
        defaults = [
            AIAgentRegistration.CONVERSATION_AI,
            AIAgentRegistration.TRAE_AI,
            AIAgentRegistration.SUBAGENT_AI
        ]
        for entry in defaults:
            self.register(entry)

    def _row_to_entry(self, row: tuple) -> AIRegistryEntry:
        """行转模型"""
        return AIRegistryEntry(
            ai_id=row[0],
            name=row[1],
            agent_type=AIAgentType(row[2]),
            capabilities=[AIAgentCapability(c) for c in json.loads(row[3])],
            contract=AIAgentContract(row[4]),
            status=AIAgentStatus(row[5]),
            endpoint=row[6],
            metadata=json.loads(row[7]) if row[7] else {},
            registered_at=row[8],
            last_seen=row[9],
            version=row[10]
        )


class AIAgentRegistration:
    """AI 注册助手"""

    CONVERSATION_AI = AIRegistryEntry(
        ai_id="hermes_conversation",
        name="Hermes (对话端)",
        agent_type=AIAgentType.CONVERSATION,
        capabilities=[
            AIAgentCapability.REASONING,
            AIAgentCapability.KNOWLEDGE_QUERY,
            AIAgentCapability.ORCHESTRATION
        ],
        contract=AIAgentContract.READ_WRITE,
        status=AIAgentStatus.ACTIVE,
        endpoint="http://localhost:8000",
        metadata={"role": "coordinator", "description": "主协调对话端"},
        registered_at=datetime.now().isoformat(),
        version="1.0.0"
    )

    TRAE_AI = AIRegistryEntry(
        ai_id="trae_editor",
        name="Trae Editor",
        agent_type=AIAgentType.TRAE,
        capabilities=[
            AIAgentCapability.CODE_GENERATION,
            AIAgentCapability.CODE_REVIEW,
            AIAgentCapability.FILE_WATCH
        ],
        contract=AIAgentContract.READ_ONLY,
        status=AIAgentStatus.IDLE,
        endpoint="trae://editor",
        metadata={"role": "editor", "description": "代码编辑器"},
        registered_at=datetime.now().isoformat(),
        version="1.0.0"
    )

    SUBAGENT_AI = AIRegistryEntry(
        ai_id="subagent_executor",
        name="SubAgent Executor",
        agent_type=AIAgentType.SUBAGENT,
        capabilities=[
            AIAgentCapability.CODE_GENERATION,
            AIAgentCapability.CODE_REVIEW,
            AIAgentCapability.ARCHITECTURE_DESIGN,
            AIAgentCapability.REASONING
        ],
        contract=AIAgentContract.READ_WRITE,
        status=AIAgentStatus.IDLE,
        endpoint="http://localhost:8001",
        metadata={"role": "executor", "description": "代码生成执行器"},
        registered_at=datetime.now().isoformat(),
        version="1.0.0"
    )


def bootstrap_registry() -> AIRegistry:
    """初始化注册表"""
    registry = AIRegistry()

    for entry in [
        AIAgentRegistration.CONVERSATION_AI,
        AIAgentRegistration.TRAE_AI,
        AIAgentRegistration.SUBAGENT_AI
    ]:
        registry.register(entry)

    return registry


if __name__ == "__main__":
    print("=" * 60)
    print("  AI Registry 初始化")
    print("=" * 60)

    registry = bootstrap_registry()

    print("\n已注册的 AI：")
    for ai in registry.get_all():
        print(f"  {ai.ai_id} ({ai.agent_type.value}) - {ai.status.value}")
        print(f"    能力: {[c.value for c in ai.capabilities]}")
        print(f"    契约: {ai.contract.value}")
