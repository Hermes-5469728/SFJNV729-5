"""
AC Bus - 统一事件总线
P0: 覆盖治理真空 (#1 文件绕过G3, #4 auditor未集成)

核心思想：
- 所有模块的状态变更、治理事件、知识更新都通过 Bus 发布/订阅
- 从"模块间隐式依赖"变成"AC Bus 显式事件契约"
"""

import json
import threading
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import uuid


class EventType(Enum):
    # 文件事件
    FILE_WRITTEN = "file.written"
    FILE_MODIFIED = "file.modified"
    FILE_DELETED = "file.deleted"

    # 治理事件
    GOVERNANCE_STARTED = "governance.started"
    GOVERNANCE_COMPLETED = "governance.completed"
    GOVERNANCE_FAILED = "governance.failed"
    GOVERNANCE_STEP = "governance.step"

    # 知识库事件
    TRUTH_STORED = "truth.stored"
    TRUTH_UPDATED = "truth.updated"
    TRUTH_DECAYED = "truth.decayed"
    TRUTH_DELETED = "truth.deleted"

    # 任务事件
    TASK_CREATED = "task.created"
    TASK_ASSIGNED = "task.assigned"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_ESCALATED = "task.escalated"

    # 对话事件
    SESSION_STARTED = "session.started"
    SESSION_ENDED = "session.ended"
    SESSION_MESSAGE = "session.message"

    # 调度事件
    SCHEDULER_ROUTED = "scheduler.routed"
    SUBAGENT_INVOKED = "subagent.invoked"
    SUBAGENT_COMPLETED = "subagent.completed"


@dataclass
class BusEvent:
    id: str
    event_type: EventType
    timestamp: str
    source: str
    payload: Dict[str, Any]
    trace_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "payload": self.payload,
            "trace_id": self.trace_id
        }


class ACBus:
    """
    AC 统一事件总线

    使用方式：
    1. 发布事件：bus.publish(EventType.FILE_WRITTEN, {"path": "...", "content": "..."})
    2. 订阅事件：bus.subscribe(EventType.FILE_WRITTEN, handler_function)
    3. 取消订阅：bus.unsubscribe(EventType.FILE_WRITTEN, handler_function)

    事件流程：
    - 对话端写文件 → 发布 FILE_WRITTEN → HallucinationAuditor 订阅 → 自动审计
    - G3 治理完成 → 发布 GOVERNANCE_COMPLETED → case_center 订阅 → 自动捕获
    - guard.store_truth() → 发布 TRUTH_STORED → KnowledgeService 订阅 → 刷新缓存
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        if self._initialized:
            return

        self._initialized = True
        self.db_path = db_path

        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._event_log: List[BusEvent] = []
        self._log_lock = threading.Lock()
        self._max_log_size = 10000

        self._trace_id: Optional[str] = None

        if self.db_path:
            self._init_db()

        print("[AC Bus] 初始化完成")

    def _init_db(self):
        """初始化事件日志数据库"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bus_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                payload TEXT,
                trace_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type
            ON bus_events(event_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_trace
            ON bus_events(trace_id)
        """)

        conn.commit()
        conn.close()

    def set_trace_id(self, trace_id: str):
        """设置当前追踪 ID（用于关联同一请求的所有事件）"""
        self._trace_id = trace_id

    def get_trace_id(self) -> str:
        """获取或生成追踪 ID"""
        if not self._trace_id:
            self._trace_id = str(uuid.uuid4())
        return self._trace_id

    def clear_trace_id(self):
        """清除追踪 ID（新请求开始时调用）"""
        self._trace_id = None

    def publish(self, event_type: EventType, payload: Dict[str, Any],
                source: str = "system") -> BusEvent:
        """
        发布事件

        Args:
            event_type: 事件类型
            payload: 事件数据
            source: 事件来源模块

        Returns:
            BusEvent: 发布的事件对象
        """
        event = BusEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            source=source,
            payload=payload,
            trace_id=self.get_trace_id()
        )

        self._log_event(event)

        for subscriber in self._subscribers.get(event_type, []):
            try:
                subscriber(event)
            except Exception as e:
                print(f"[AC Bus] 事件处理错误 {event_type.value}: {e}")

        return event

    def subscribe(self, event_type: EventType, handler: Callable[[BusEvent], None]):
        """
        订阅事件

        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
            print(f"[AC Bus] 订阅: {event_type.value}")

    def unsubscribe(self, event_type: EventType, handler: Callable[[BusEvent], None]):
        """
        取消订阅

        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            print(f"[AC Bus] 取消订阅: {event_type.value}")

    def subscribe_pattern(self, pattern: str, handler: Callable[[BusEvent], None]):
        """
        订阅匹配模式的事件（如 "governance.*"）

        Args:
            pattern: 事件类型模式（支持 * 通配符）
            handler: 处理函数
        """
        def pattern_matcher(event: BusEvent):
            import fnmatch
            if fnmatch.fnmatch(event.event_type.value, pattern):
                handler(event)

        pattern_key = f"pattern:{pattern}"
        self._subscribers[pattern_key].append(pattern_matcher)
        print(f"[AC Bus] 订阅模式: {pattern}")

    def _log_event(self, event: BusEvent):
        """记录事件到日志"""
        with self._log_lock:
            self._event_log.append(event)
            if len(self._event_log) > self._max_log_size:
                self._event_log = self._event_log[-self._max_log_size:]

        if self.db_path:
            self._persist_event(event)

    def _persist_event(self, event: BusEvent):
        """持久化事件到数据库"""
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bus_events
                (id, event_type, timestamp, source, payload, trace_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event.id,
                event.event_type.value,
                event.timestamp,
                event.source,
                json.dumps(event.payload, ensure_ascii=False),
                event.trace_id
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[AC Bus] 持久化错误: {e}")

    def get_events(self, event_type: Optional[EventType] = None,
                   trace_id: Optional[str] = None,
                   limit: int = 100) -> List[BusEvent]:
        """
        查询事件日志

        Args:
            event_type: 按事件类型过滤
            trace_id: 按追踪 ID 过滤
            limit: 返回数量限制

        Returns:
            List[BusEvent]: 事件列表
        """
        if self.db_path:
            return self._query_events(event_type, trace_id, limit)

        result = self._event_log
        if event_type:
            result = [e for e in result if e.event_type == event_type]
        if trace_id:
            result = [e for e in result if e.trace_id == trace_id]
        return result[-limit:]

    def _query_events(self, event_type: Optional[EventType],
                     trace_id: Optional[str], limit: int) -> List[BusEvent]:
        """从数据库查询事件"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        sql = "SELECT * FROM bus_events WHERE 1=1"
        params = []

        if event_type:
            sql += " AND event_type = ?"
            params.append(event_type.value)

        if trace_id:
            sql += " AND trace_id = ?"
            params.append(trace_id)

        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_event(row) for row in rows]

    def _row_to_event(self, row) -> BusEvent:
        """行转事件"""
        return BusEvent(
            id=row["id"],
            event_type=EventType(row["event_type"]),
            timestamp=row["timestamp"],
            source=row["source"],
            payload=json.loads(row["payload"]) if row["payload"] else {},
            trace_id=row["trace_id"]
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        type_counts = defaultdict(int)
        for event in self._event_log:
            type_counts[event.event_type.value] += 1

        return {
            "total_events": len(self._event_log),
            "subscriber_count": sum(len(s) for s in self._subscribers.values()),
            "event_types": dict(type_counts),
            "active_trace_id": self._trace_id
        }


# ============================================================================
# 预设订阅处理器
# ============================================================================

class HallucinationAuditorHandler:
    """
    HallucinationAuditor 事件处理器
    订阅 FILE_WRITTEN 事件，自动审计文件内容
    """

    def __init__(self, auditor=None):
        self.auditor = auditor
        self.audit_results: List[Dict] = []

    def handle(self, event: BusEvent):
        """处理文件写入事件"""
        if event.event_type != EventType.FILE_WRITTEN:
            return

        path = event.payload.get("path", "")
        content = event.payload.get("content", "")

        if not path or not content:
            return

        if not self._should_audit(path):
            return

        try:
            from ac.governance.hallucination_auditor import HallucinationAuditor
            if not self.auditor:
                self.auditor = HallucinationAuditor()

            result = self.auditor.audit(content)

            self.audit_results.append({
                "event_id": event.id,
                "file": path,
                "result": result,
                "timestamp": event.timestamp
            })

            if not result["passed"]:
                print(f"[HallucinationAuditor] 检测到幻觉: {path}")
                bus = ACBus()
                bus.publish(
                    EventType.GOVERNANCE_FAILED,
                    {
                        "source": "hallucination_auditor",
                        "file": path,
                        "check_type": "hallucination",
                        "details": result
                    },
                    source="hallucination_auditor"
                )

        except Exception as e:
            print(f"[HallucinationAuditor] 审计错误: {e}")

    def _should_audit(self, path: str) -> bool:
        """判断是否应该审计"""
        code_exts = [".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp"]
        return any(path.endswith(ext) for ext in code_exts)


class CaseCenterHandler:
    """
    Case Center 事件处理器
    订阅 GOVERNANCE_FAILED 事件，自动捕获问题
    """

    def __init__(self):
        self.captured_cases: List[Dict] = []

    def handle(self, event: BusEvent):
        """处理治理失败事件"""
        if event.event_type != EventType.GOVERNANCE_FAILED:
            return

        case = {
            "event_id": event.id,
            "trace_id": event.trace_id,
            "timestamp": event.timestamp,
            "source": event.payload.get("source"),
            "check_type": event.payload.get("check_type"),
            "details": event.payload.get("details", {}),
            "status": "captured"
        }

        self.captured_cases.append(case)
        print(f"[CaseCenter] 捕获问题: {case['source']} - {case['check_type']}")


class KnowledgeServiceRefreshHandler:
    """
    KnowledgeService 刷新处理器
    订阅 TRUTH_STORED 事件，刷新知识缓存
    """

    def __init__(self, knowledge_service=None):
        self.knowledge_service = knowledge_service
        self.refresh_count = 0

    def handle(self, event: BusEvent):
        """处理知识入库事件"""
        if event.event_type not in [EventType.TRUTH_STORED, EventType.TRUTH_UPDATED]:
            return

        if not self.knowledge_service:
            return

        try:
            self.knowledge_service._clear_cache()
            self.refresh_count += 1
            print(f"[KnowledgeService] 缓存已刷新 (count: {self.refresh_count})")
        except Exception as e:
            print(f"[KnowledgeService] 刷新错误: {e}")


# ============================================================================
# 全局总线实例（便于使用）
# ============================================================================

bus = ACBus()


def get_bus() -> ACBus:
    """获取全局总线实例"""
    return bus


# ============================================================================
# 测试
# ============================================================================

def test_ac_bus():
    print("=" * 60)
    print("  AC Bus P0 测试")
    print("=" * 60)

    import os
    db_path = "test_ac_bus.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    test_bus = ACBus(db_path)

    print("\n--- 1. 基础发布/订阅测试 ---\n")

    received_events = []

    def handler(event: BusEvent):
        received_events.append(event)
        print(f"  收到事件: {event.event_type.value} from {event.source}")

    test_bus.subscribe(EventType.FILE_WRITTEN, handler)

    test_bus.publish(
        EventType.FILE_WRITTEN,
        {"path": "src/model.py", "content": "def train(): pass"},
        source="hermes"
    )
    print(f"  已发布 FILE_WRITTEN 事件")
    print(f"  收到事件数: {len(received_events)}")

    print("\n--- 2. HallucinationAuditor 自动审计测试 ---\n")

    hall_auditor_handler = HallucinationAuditorHandler()
    test_bus.subscribe(EventType.FILE_WRITTEN, hall_auditor_handler.handle)

    test_bus.publish(
        EventType.FILE_WRITTEN,
        {"path": "src/hallucination_test.py", "content": "研究表明某些药物可以安全联合使用，没有任何副作用。"},
        source="hermes"
    )
    print(f"  审计结果数: {len(hall_auditor_handler.audit_results)}")

    print("\n--- 3. Case Center 自动捕获测试 ---\n")

    case_handler = CaseCenterHandler()
    test_bus.subscribe(EventType.GOVERNANCE_FAILED, case_handler.handle)

    test_bus.publish(
        EventType.GOVERNANCE_FAILED,
        {"source": "g3_pipeline", "check_type": "hallucination", "details": {}},
        source="governance"
    )
    print(f"  捕获案例数: {len(case_handler.captured_cases)}")

    print("\n--- 4. 追踪 ID 测试 ---\n")

    test_bus.set_trace_id("trace_001")
    test_bus.publish(EventType.TASK_CREATED, {"task_id": "123"}, source="test")
    test_bus.publish(EventType.TASK_COMPLETED, {"task_id": "123"}, source="test")

    events = test_bus.get_events(trace_id="trace_001")
    print(f"  追踪 trace_001 的事件数: {len(events)}")

    print("\n--- 5. 统计信息 ---\n")

    stats = test_bus.get_stats()
    print(f"  统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")

    print("\n--- 6. 事件查询 ---\n")

    recent = test_bus.get_events(limit=5)
    print(f"  最近事件: {len(recent)} 个")
    for e in recent:
        print(f"    - {e.event_type.value} @ {e.timestamp[:19]}")

    if os.path.exists(db_path):
        os.remove(db_path)

    print("\n" + "=" * 60)
    print("  ✅ AC Bus 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_ac_bus()

