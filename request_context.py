"""
RequestContext - 全局请求追踪上下文

问题：请求经过 Queue → Worker → Stream Router → Orchestrator → Agent → G3，
      如何关联结果与原始请求？
解决：request_id 在 Queue 层生成，贯穿所有下游模块
"""

import json
import sqlite3
import threading
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict


request_context: ContextVar[Optional["RequestContext"]] = ContextVar(
    "request_context",
    default=None
)


class RequestStatus(Enum):
    CREATED = "created"           # 已创建
    QUEUED = "queued"            # 已入队
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败


@dataclass
class RequestSpan:
    """请求追踪Span"""
    module: str              # 模块名
    operation: str           # 操作名
    request_id: str          # 请求ID
    parent_span_id: Optional[str]  # 父SpanID
    span_id: str             # SpanID
    status: str              # 状态
    created_at: str          # 创建时间
    completed_at: Optional[str] = None  # 完成时间
    duration_ms: Optional[float] = None  # 耗时
    metadata: Optional[Dict] = None     # 元数据


@dataclass
class RequestContext:
    """
    全局请求上下文

    在 Queue 层生成 request_id，贯穿所有下游模块。
    所有模块的日志输出和数据库写入都携带此 request_id。

    使用方式：
    1. Queue 入队时生成 context
    2. Worker 出队时获取 context 并设置到线程本地
    3. 所有模块通过 get_context() 获取当前请求的上下文
    4. 日志、数据库写入都携带 request_id
    """

    request_id: str                    # 全局唯一请求ID
    trace_id: str                      # 追踪ID（关联同一次用户会话）
    parent_request_id: Optional[str]   # 父请求ID（子任务）
    user_id: Optional[str]             # 用户ID
    session_id: Optional[str]          # 会话ID
    status: RequestStatus              # 请求状态
    created_at: str                   # 创建时间
    started_at: Optional[str]          # 开始处理时间
    completed_at: Optional[str]        # 完成时间
    metadata: Dict[str, Any]          # 元数据
    spans: List[RequestSpan] = field(default_factory=list)  # 追踪Span

    _local = threading.local()

    @classmethod
    def create(cls, trace_id: Optional[str] = None,
              parent_request_id: Optional[str] = None,
              user_id: Optional[str] = None,
              session_id: Optional[str] = None,
              metadata: Optional[Dict] = None) -> "RequestContext":
        """创建新的请求上下文"""
        request_id = str(uuid.uuid4())
        return cls(
            request_id=request_id,
            trace_id=trace_id or str(uuid.uuid4()),
            parent_request_id=parent_request_id,
            user_id=user_id,
            session_id=session_id,
            status=RequestStatus.CREATED,
            created_at=datetime.now().isoformat(),
            started_at=None,
            completed_at=None,
            metadata=metadata or {}
        )

    @classmethod
    def get_current(cls) -> Optional["RequestContext"]:
        """获取当前线程的请求上下文"""
        return request_context.get()

    @classmethod
    def set_current(cls, ctx: Optional["RequestContext"]):
        """设置当前线程的请求上下文"""
        request_context.set(ctx)

    def start_span(self, module: str, operation: str,
                  parent_span_id: Optional[str] = None,
                  metadata: Optional[Dict] = None) -> RequestSpan:
        """开始一个Span"""
        span_id = str(uuid.uuid4())
        span = RequestSpan(
            module=module,
            operation=operation,
            request_id=self.request_id,
            parent_span_id=parent_span_id,
            span_id=span_id,
            status="started",
            created_at=datetime.now().isoformat(),
            metadata=metadata
        )
        self.spans.append(span)
        return span

    def end_span(self, span: RequestSpan, status: str = "completed",
                metadata: Optional[Dict] = None):
        """结束一个Span"""
        span.status = status
        span.completed_at = datetime.now().isoformat()
        if span.created_at and span.completed_at:
            start = datetime.fromisoformat(span.created_at)
            end = datetime.fromisoformat(span.completed_at)
            span.duration_ms = (end - start).total_seconds() * 1000
        if metadata:
            span.metadata = {**(span.metadata or {}), **metadata}

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "parent_request_id": self.parent_request_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
            "span_count": len(self.spans)
        }


class RequestTracker:
    """
    请求追踪器 - 持久化 request_id 和 spans

    将 request_id 贯穿到所有数据库写入：
    - task_execution_trace
    - governance_events
    - bus_events
    """

    def __init__(self, db_path: str = "request_tracking.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化追踪数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                request_id TEXT PRIMARY KEY,
                trace_id TEXT,
                parent_request_id TEXT,
                user_id TEXT,
                session_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_requests_trace
            ON requests(trace_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_requests_session
            ON requests(session_id)
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_spans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                module TEXT NOT NULL,
                operation TEXT NOT NULL,
                parent_span_id TEXT,
                span_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                duration_ms REAL,
                metadata TEXT,
                FOREIGN KEY (request_id) REFERENCES requests(request_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_spans_request
            ON request_spans(request_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_spans_span
            ON request_spans(span_id)
        """)

        conn.commit()
        conn.close()

    def start_request(self, ctx: RequestContext) -> bool:
        """记录请求开始"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO requests
                (request_id, trace_id, parent_request_id, user_id, session_id, status, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ctx.request_id,
                ctx.trace_id,
                ctx.parent_request_id,
                ctx.user_id,
                ctx.session_id,
                ctx.status.value,
                ctx.created_at,
                json.dumps(ctx.metadata)
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"[RequestTracker] 记录请求失败: {e}")
            return False
        finally:
            conn.close()

    def update_request_status(self, request_id: str, status: RequestStatus,
                           started_at: Optional[str] = None,
                           completed_at: Optional[str] = None):
        """更新请求状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if started_at:
            cursor.execute("""
                UPDATE requests SET status = ?, started_at = ?
                WHERE request_id = ?
            """, [status.value, started_at, request_id])
        elif completed_at:
            cursor.execute("""
                UPDATE requests SET status = ?, completed_at = ?
                WHERE request_id = ?
            """, [status.value, completed_at, request_id])
        else:
            cursor.execute("""
                UPDATE requests SET status = ?
                WHERE request_id = ?
            """, [status.value, request_id])

        conn.commit()
        conn.close()

    def record_span(self, request_id: str, span: RequestSpan):
        """记录Span"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO request_spans
            (request_id, module, operation, parent_span_id, span_id, status, created_at, completed_at, duration_ms, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            span.module,
            span.operation,
            span.parent_span_id,
            span.span_id,
            span.status,
            span.created_at,
            span.completed_at,
            span.duration_ms,
            json.dumps(span.metadata) if span.metadata else None
        ))

        conn.commit()
        conn.close()

    def get_request_chain(self, request_id: str) -> List[Dict[str, Any]]:
        """获取请求的完整链路（包括子请求）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            WITH RECURSIVE chain AS (
                SELECT request_id, trace_id, parent_request_id, status, created_at
                FROM requests
                WHERE request_id = ?

                UNION ALL

                SELECT r.request_id, r.trace_id, r.parent_request_id, r.status, r.created_at
                FROM requests r
                INNER JOIN chain c ON r.parent_request_id = c.request_id
            )
            SELECT * FROM chain ORDER BY created_at
        """, [request_id])

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_request_spans(self, request_id: str) -> List[Dict[str, Any]]:
        """获取请求的所有Span"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM request_spans
            WHERE request_id = ?
            ORDER BY created_at
        """, [request_id])

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_trace_requests(self, trace_id: str) -> List[Dict[str, Any]]:
        """获取追踪的所有请求"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM requests
            WHERE trace_id = ?
            ORDER BY created_at
        """, [trace_id])

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]


class RequestContextMiddleware:
    """
    请求上下文中间件 - 自动管理 Context 的创建和销毁

    使用方式：
    middleware = RequestContextMiddleware(tracker)

    # 在入口处（如 Server 的 API handler）
    with middleware.request_context(request_id=None):
        ctx = RequestContext.get_current()
        # 业务逻辑
    """

    def __init__(self, tracker: RequestTracker):
        self.tracker = tracker

    def request_context(self, request_id: Optional[str] = None,
                      trace_id: Optional[str] = None,
                      parent_request_id: Optional[str] = None,
                      user_id: Optional[str] = None,
                      session_id: Optional[str] = None,
                      metadata: Optional[Dict] = None):
        """创建请求上下文的上下文管理器"""
        return _RequestContextManager(
            self.tracker,
            request_id,
            trace_id,
            parent_request_id,
            user_id,
            session_id,
            metadata
        )


class _RequestContextManager:
    """请求上下文管理器"""

    def __init__(self, tracker: RequestTracker,
                 request_id: Optional[str],
                 trace_id: Optional[str],
                 parent_request_id: Optional[str],
                 user_id: Optional[str],
                 session_id: Optional[str],
                 metadata: Optional[Dict]):
        self.tracker = tracker
        self.request_id = request_id
        self.trace_id = trace_id
        self.parent_request_id = parent_request_id
        self.user_id = user_id
        self.session_id = session_id
        self.metadata = metadata
        self.ctx: Optional[RequestContext] = None

    def __enter__(self) -> RequestContext:
        self.ctx = RequestContext.create(
            trace_id=self.trace_id,
            parent_request_id=self.parent_request_id,
            user_id=self.user_id,
            session_id=self.session_id,
            metadata=self.metadata
        )
        self.ctx.status = RequestStatus.QUEUED
        self.tracker.start_request(self.ctx)
        RequestContext.set_current(self.ctx)
        return self.ctx

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.ctx:
            if exc_type:
                self.ctx.status = RequestStatus.FAILED
                self.ctx.metadata["error"] = str(exc_val)
            else:
                self.ctx.status = RequestStatus.COMPLETED

            self.ctx.completed_at = datetime.now().isoformat()
            self.tracker.update_request_status(
                self.ctx.request_id,
                self.ctx.status,
                completed_at=self.ctx.completed_at
            )

            for span in self.ctx.spans:
                self.tracker.record_span(self.ctx.request_id, span)

        RequestContext.set_current(None)
        return False


def get_request_id() -> Optional[str]:
    """获取当前请求的 request_id"""
    ctx = RequestContext.get_current()
    return ctx.request_id if ctx else None


def get_trace_id() -> Optional[str]:
    """获取当前请求的 trace_id"""
    ctx = RequestContext.get_current()
    return ctx.trace_id if ctx else None


def create_span(module: str, operation: str,
               metadata: Optional[Dict] = None) -> Optional[RequestSpan]:
    """创建Span的便捷函数"""
    ctx = RequestContext.get_current()
    if ctx:
        return ctx.start_span(module, operation, metadata=metadata)
    return None


def end_span(span: RequestSpan, status: str = "completed",
            metadata: Optional[Dict] = None):
    """结束Span的便捷函数"""
    ctx = RequestContext.get_current()
    if ctx:
        ctx.end_span(span, status, metadata)


# ============================================================================
# 测试
# ============================================================================

def test_request_context():
    print("=" * 60)
    print("  RequestContext 全局追踪测试")
    print("=" * 60)

    import os
    db_path = "test_tracking.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    tracker = RequestTracker(db_path)
    middleware = RequestContextMiddleware(tracker)

    print("\n--- 1. 基本请求追踪 ---\n")

    with middleware.request_context(user_id="user_001", session_id="session_001"):
        ctx = RequestContext.get_current()
        print(f"请求ID: {ctx.request_id[:16]}...")
        print(f"追踪ID: {ctx.trace_id[:16]}...")

        span1 = create_span("Queue", "enqueue")
        time.sleep(0.01)
        end_span(span1)

        span2 = create_span("Worker", "process")
        time.sleep(0.01)
        end_span(span2)

        span3 = create_span("Orchestrator", "execute")
        time.sleep(0.01)
        end_span(span3)

    print("请求处理完成")

    print("\n--- 2. 验证持久化 ---\n")

    requests = tracker.get_trace_requests(ctx.trace_id)
    print(f"追踪 {ctx.trace_id[:16]}... 的请求数: {len(requests)}")

    spans = tracker.get_request_spans(ctx.request_id)
    print(f"请求 {ctx.request_id[:16]}... 的Span数: {len(spans)}")
    for span in spans:
        print(f"  - {span['module']}/{span['operation']} ({span['duration_ms']:.2f}ms)")

    print("\n--- 3. 子请求追踪 ---\n")

    parent_request_id = ctx.request_id

    with middleware.request_context(
            parent_request_id=parent_request_id,
            user_id="user_001",
            metadata={"subtask": "code_generation"}
    ):
        sub_ctx = RequestContext.get_current()
        print(f"子请求ID: {sub_ctx.request_id[:16]}...")
        print(f"父请求ID: {sub_ctx.parent_request_id[:16]}...")

        span = create_span("SubAgent", "generate")
        time.sleep(0.01)
        end_span(span)

    print("子请求处理完成")

    print("\n--- 4. 验证请求链路 ---\n")

    chain = tracker.get_request_chain(parent_request_id)
    print(f"请求链路长度: {len(chain)}")
    for req in chain:
        print(f"  - {req['request_id'][:16]}... (parent: {str(req['parent_request_id'] or 'None')[:16]})")

    print("\n--- 5. 跨模块获取 Context ---\n")

    def module_a():
        ctx = RequestContext.get_current()
        return ctx.request_id if ctx else None

    def module_b():
        ctx = RequestContext.get_current()
        return ctx.request_id if ctx else None

    with middleware.request_context():
        ctx = RequestContext.get_current()
        rid = ctx.request_id

        id_a = module_a()
        id_b = module_b()

        print(f"主上下文 ID: {rid[:16]}...")
        print(f"module_a 获取 ID: {id_a[:16] if id_a else 'None'}...")
        print(f"module_b 获取 ID: {id_b[:16] if id_b else 'None'}...")
        print(f"一致性: {rid == id_a == id_b}")

    if os.path.exists(db_path):
        os.remove(db_path)

    print("\n" + "=" * 60)
    print("  ✅ RequestContext 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_request_context()

