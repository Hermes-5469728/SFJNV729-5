"""
Governance Tasks - P1: 文件写入自动触发 AC 治理
governance_tasks 表 + 守护进程消费机制
"""

import json
import sqlite3
import threading
import time
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass, asdict


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    ANNOTATE = "annotate"
    VERIFY = "verify"
    AUDIT = "audit"
    SYNC = "sync"


@dataclass
class GovernanceTask:
    id: Optional[int]
    task_type: TaskType
    file_path: str
    content: Optional[str]
    priority: int
    status: TaskStatus
    created_at: str
    updated_at: str
    created_by: str
    error_message: Optional[str]
    result: Optional[str]
    metadata: Optional[str]


class GovernanceTaskStore:
    """治理任务存储 - SQLite"""

    def __init__(self, db_path: str = "ac_governance.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS governance_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                content TEXT,
                priority INTEGER DEFAULT 5,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                created_by TEXT DEFAULT 'system',
                error_message TEXT,
                result TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status
            ON governance_tasks(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_priority
            ON governance_tasks(priority DESC, created_at ASC)
        """)

        conn.commit()
        conn.close()

    def create_task(self, task_type: TaskType, file_path: str,
                    content: Optional[str] = None,
                    priority: int = 5,
                    created_by: str = "system",
                    metadata: Optional[Dict] = None) -> int:
        """创建治理任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO governance_tasks
            (task_type, file_path, content, priority, status, created_at, updated_at, created_by, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_type.value,
            file_path,
            content,
            priority,
            TaskStatus.PENDING.value,
            now,
            now,
            created_by,
            json.dumps(metadata) if metadata else None
        ))

        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return task_id

    def get_pending_tasks(self, limit: int = 10) -> List[GovernanceTask]:
        """获取待处理任务（按优先级和时间排序）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM governance_tasks
            WHERE status = ?
            ORDER BY priority DESC, created_at ASC
            LIMIT ?
        """, [TaskStatus.PENDING.value, limit])

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_task(row) for row in rows]

    def claim_task(self, task_id: int) -> Optional[GovernanceTask]:
        """认领任务（原子操作，防止重复消费）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE governance_tasks
            SET status = ?, updated_at = ?
            WHERE id = ? AND status = ?
        """, (
            TaskStatus.PROCESSING.value,
            datetime.now().isoformat(),
            task_id,
            TaskStatus.PENDING.value
        ))

        if cursor.rowcount == 0:
            conn.commit()
            conn.close()
            return None

        cursor.execute("SELECT * FROM governance_tasks WHERE id = ?", [task_id])
        row = cursor.fetchone()
        conn.commit()
        conn.close()

        return self._row_to_task(row) if row else None

    def complete_task(self, task_id: int, result: str):
        """完成任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE governance_tasks
            SET status = ?, result = ?, updated_at = ?
            WHERE id = ?
        """, (
            TaskStatus.COMPLETED.value,
            result,
            datetime.now().isoformat(),
            task_id
        ))

        conn.commit()
        conn.close()

    def fail_task(self, task_id: int, error_message: str):
        """标记任务失败"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE governance_tasks
            SET status = ?, error_message = ?, updated_at = ?
            WHERE id = ?
        """, (
            TaskStatus.FAILED.value,
            error_message,
            datetime.now().isoformat(),
            task_id
        ))

        conn.commit()
        conn.close()

    def get_task_stats(self) -> Dict[str, Any]:
        """获取任务统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT status, COUNT(*) FROM governance_tasks
            GROUP BY status
        """)
        status_counts = dict(cursor.fetchall())

        cursor.execute("SELECT COUNT(*) FROM governance_tasks")
        total = cursor.fetchone()[0]

        conn.close()

        return {
            "total": total,
            "by_status": status_counts
        }

    def _row_to_task(self, row: sqlite3.Row) -> GovernanceTask:
        return GovernanceTask(
            id=row["id"],
            task_type=TaskType(row["task_type"]),
            file_path=row["file_path"],
            content=row["content"],
            priority=row["priority"],
            status=TaskStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=row["created_by"],
            error_message=row["error_message"],
            result=row["result"],
            metadata=row["metadata"]
        )


class GovernanceTaskConsumer:
    """治理任务消费者 - 守护进程"""

    def __init__(self, store: GovernanceTaskStore,
                 handlers: Dict[TaskType, Callable]):
        self.store = store
        self.handlers = handlers
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self, poll_interval: float = 1.0):
        """启动消费守护进程"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._consume_loop,
            args=(poll_interval,),
            daemon=True
        )
        self._thread.start()
        print(f"[GovernanceConsumer] 启动，轮询间隔: {poll_interval}s")

    def stop(self):
        """停止消费"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[GovernanceConsumer] 已停止")

    def _consume_loop(self, poll_interval: float):
        """消费循环"""
        while self._running:
            try:
                tasks = self.store.get_pending_tasks(limit=5)
                for task in tasks:
                    self._process_task(task)
            except Exception as e:
                print(f"[GovernanceConsumer] 处理错误: {e}")

            time.sleep(poll_interval)

    def _process_task(self, task: GovernanceTask):
        """处理单个任务"""
        claimed = self.store.claim_task(task.id)
        if not claimed:
            return

        handler = self.handlers.get(task.task_type)
        if not handler:
            self.store.fail_task(task.id, f"未找到处理器: {task.task_type}")
            return

        try:
            result = handler(task)
            self.store.complete_task(task.id, json.dumps(result, ensure_ascii=False))
            print(f"[GovernanceConsumer] 完成任务 #{task.id}: {task.task_type.value}")
        except Exception as e:
            self.store.fail_task(task.id, str(e))
            print(f"[GovernanceConsumer] 任务 #{task.id} 失败: {e}")


def annotate_handler(task: GovernanceTask) -> Dict[str, Any]:
    """ANNOTATE 任务处理器"""
    if task.content:
        from ac.governance import pipeline
        result = pipeline(task.content, {"command": "annotate"})
        return {"governance_result": result}
    return {"error": "无内容"}


def verify_handler(task: GovernanceTask) -> Dict[str, Any]:
    """VERIFY 任务处理器"""
    if task.content:
        from ac.governance import pipeline
        result = pipeline(task.content, {"command": "verify"})
        return {"governance_result": result}
    return {"error": "无内容"}


class GovernanceTaskClient:
    """对话端客户端 - 写入任务"""

    def __init__(self, store: GovernanceTaskStore):
        self.store = store

    def queue_file_annotation(self, file_path: str, content: str,
                              priority: int = 5,
                              created_by: str = "hermes") -> int:
        """排队文件治理"""
        return self.store.create_task(
            task_type=TaskType.ANNOTATE,
            file_path=file_path,
            content=content,
            priority=priority,
            created_by=created_by,
            metadata={"source": "hermes_session"}
        )

    def queue_file_verification(self, file_path: str, content: str,
                               priority: int = 5,
                               created_by: str = "hermes") -> int:
        """排队文件验证"""
        return self.store.create_task(
            task_type=TaskType.VERIFY,
            file_path=file_path,
            content=content,
            priority=priority,
            created_by=created_by
        )

    def check_task_status(self, task_id: int) -> Optional[GovernanceTask]:
        """检查任务状态"""
        conn = sqlite3.connect(self.store.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM governance_tasks WHERE id = ?", [task_id])
        row = cursor.fetchone()
        conn.close()
        return self.store._row_to_task(row) if row else None


# ============================================================================
# 测试
# ============================================================================

def test_governance_tasks():
    print("=" * 60)
    print("  Governance Tasks P1 测试")
    print("=" * 60)

    import os
    db_path = "test_governance.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    store = GovernanceTaskStore(db_path)
    client = GovernanceTaskClient(store)

    print("\n--- 1. 创建任务测试 ---\n")
    task_id = client.queue_file_annotation(
        file_path="src/medical/model.py",
        content='{"diagnosis": "高血压", "confidence": 0.95}',
        priority=8,
        created_by="hermes_session_001"
    )
    print(f"✅ 创建 ANNOTATE 任务: #{task_id}")

    task_id2 = client.queue_file_annotation(
        file_path="src/medical/protocol.py",
        content='{"treatment": "用药方案"}',
        priority=5
    )
    print(f"✅ 创建 ANNOTATE 任务: #{task_id2}")

    print("\n--- 2. 任务统计 ---\n")
    stats = store.get_task_stats()
    print(f"统计: {stats}")

    print("\n--- 3. 启动消费者测试 ---\n")
    handlers = {
        TaskType.ANNOTATE: annotate_handler,
        TaskType.VERIFY: verify_handler,
    }
    consumer = GovernanceTaskConsumer(store, handlers)
    consumer.start(poll_interval=0.5)

    time.sleep(2)

    consumer.stop()

    print("\n--- 4. 最终统计 ---\n")
    stats = store.get_task_stats()
    print(f"统计: {stats}")

    if os.path.exists(db_path):
        os.remove(db_path)

    print("\n" + "=" * 60)
    print("  ✅ Governance Tasks 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_governance_tasks()

