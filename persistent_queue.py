"""
PersistentMessageQueue - P1: 持久化消息队列 + ACK 机制
从 asyncio.Queue（内存）升级到 SQLite（持久化）+ ACK 确认

问题：进程重启丢消息 → SQLite 持久化 + 超时重入队
"""

import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
import asyncio


class MessageStatus(Enum):
    PENDING = "pending"          # 等待处理
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"     # 已完成（ACK）
    FAILED = "failed"           # 失败（已达最大重试）
    TIMEOUT = "timeout"         # 处理超时，需重试


@dataclass
class Message:
    id: str
    queue_name: str
    payload: Dict[str, Any]
    status: MessageStatus
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    retry_count: int
    max_retries: int
    timeout_seconds: float
    trace_id: Optional[str]
    metadata: Optional[str]


class PersistentMessageQueue:
    """
    持久化消息队列

    特性：
    1. SQLite 持久化 - 进程重启不丢消息
    2. ACK 机制 - Worker 处理完成后确认
    3. 超时重试 - 处理超时自动重新入队
    4. 多队列支持 - 不同类型消息隔离
    5. 追踪 ID - 关联同一请求的所有消息
    """

    def __init__(self, db_path: str = "message_queue.db"):
        self.db_path = db_path
        self._init_db()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False

    def _init_db(self):
        """初始化队列数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                queue_name TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                timeout_seconds REAL DEFAULT 60.0,
                trace_id TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_status_queue
            ON messages(queue_name, status, created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_trace
            ON messages(trace_id)
        """)

        conn.commit()
        conn.close()

    def enqueue(self, queue_name: str, payload: Dict[str, Any],
               trace_id: Optional[str] = None,
               max_retries: int = 3,
               timeout_seconds: float = 60.0,
               metadata: Optional[Dict] = None) -> str:
        """
        入队消息

        Args:
            queue_name: 队列名称
            payload: 消息内容
            trace_id: 追踪 ID（关联同一请求的所有消息）
            max_retries: 最大重试次数
            timeout_seconds: 处理超时时间
            metadata: 元数据

        Returns:
            str: 消息 ID
        """
        msg_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO messages
            (id, queue_name, payload, status, created_at, retry_count, max_retries, timeout_seconds, trace_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            msg_id,
            queue_name,
            json.dumps(payload, ensure_ascii=False),
            MessageStatus.PENDING.value,
            now,
            0,
            max_retries,
            timeout_seconds,
            trace_id,
            json.dumps(metadata) if metadata else None
        ))

        conn.commit()
        conn.close()

        return msg_id

    def dequeue(self, queue_name: str, block: bool = True,
               timeout: Optional[float] = None) -> Optional[Message]:
        """
        出队消息（获取并标记为 PROCESSING）

        Args:
            queue_name: 队列名称
            block: 是否阻塞等待
            timeout: 阻塞超时时间

        Returns:
            Optional[Message]: 消息对象，无消息时返回 None
        """
        start_time = time.time()

        while True:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM messages
                WHERE queue_name = ? AND status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
            """, [queue_name])

            row = cursor.fetchone()

            if not row:
                conn.close()
                if block:
                    if timeout and (time.time() - start_time) >= timeout:
                        return None
                    time.sleep(0.1)
                    continue
                return None

            now = datetime.now().isoformat()
            cursor.execute("""
                UPDATE messages
                SET status = ?, started_at = ?
                WHERE id = ? AND status = 'pending'
            """, [MessageStatus.PROCESSING.value, now, row["id"]])

            if cursor.rowcount == 0:
                conn.commit()
                conn.close()
                continue

            conn.commit()
            conn.close()

            return self._row_to_message(row)

    def ack(self, message_id: str) -> bool:
        """
        确认消息处理完成

        Args:
            message_id: 消息 ID

        Returns:
            bool: 是否成功确认
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE messages
            SET status = ?, completed_at = ?
            WHERE id = ? AND status = 'processing'
        """, [MessageStatus.COMPLETED.value, now, message_id])

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def nack(self, message_id: str, requeue: bool = True) -> bool:
        """
        拒绝消息（处理失败或需重试）

        Args:
            message_id: 消息 ID
            requeue: 是否重新入队

        Returns:
            bool: 是否成功处理
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT retry_count, max_retries FROM messages WHERE id = ?", [message_id])
        row = cursor.fetchone()

        if not row:
            conn.close()
            return False

        retry_count = row[0] + 1
        max_retries = row[1]

        if requeue and retry_count < max_retries:
            cursor.execute("""
                UPDATE messages
                SET status = ?, retry_count = ?
                WHERE id = ?
            """, [MessageStatus.PENDING.value, retry_count, message_id])
            conn.commit()
            conn.close()
            return True
        else:
            cursor.execute("""
                UPDATE messages
                SET status = ?
                WHERE id = ?
            """, [MessageStatus.FAILED.value, message_id])
            conn.commit()
            conn.close()
            return True

    def timeout_recover(self) -> int:
        """
        超时恢复 - 将处理中超时的消息重新入队

        Returns:
            int: 恢复的消息数量
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now()
        timeout_threshold = now - timedelta(seconds=60)

        cursor.execute("""
            SELECT id, started_at, timeout_seconds FROM messages
            WHERE status = 'processing'
        """)

        recovered = 0
        for row in cursor.fetchall():
            msg_id, started_at, timeout_seconds = row
            if started_at:
                started_dt = datetime.fromisoformat(started_at)
                elapsed = (now - started_dt).total_seconds()
                if elapsed > timeout_seconds:
                    cursor.execute("""
                        UPDATE messages
                        SET status = ?, retry_count = retry_count + 1
                        WHERE id = ?
                    """, [MessageStatus.PENDING.value, msg_id])
                    recovered += 1

        conn.commit()
        conn.close()

        return recovered

    def get_stats(self, queue_name: Optional[str] = None) -> Dict[str, Any]:
        """获取队列统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if queue_name:
            cursor.execute("""
                SELECT status, COUNT(*) FROM messages
                WHERE queue_name = ?
                GROUP BY status
            """, [queue_name])
        else:
            cursor.execute("SELECT status, COUNT(*) FROM messages GROUP BY status")

        rows = cursor.fetchall()
        status_counts = {status: count for status, count in rows}

        cursor.execute("SELECT COUNT(*) FROM messages")
        total = cursor.fetchone()[0]

        conn.close()

        return {
            "total": total,
            "by_status": status_counts,
            "pending": status_counts.get("pending", 0),
            "processing": status_counts.get("processing", 0),
            "completed": status_counts.get("completed", 0),
            "failed": status_counts.get("failed", 0)
        }

    def get_by_trace(self, trace_id: str) -> List[Message]:
        """获取同一追踪 ID 的所有消息"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM messages
            WHERE trace_id = ?
            ORDER BY created_at ASC
        """, [trace_id])

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_message(row) for row in rows]

    def purge_completed(self, older_than_hours: int = 24) -> int:
        """清理已完成消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = datetime.now() - timedelta(hours=older_than_hours)

        cursor.execute("""
            DELETE FROM messages
            WHERE status = 'completed' AND completed_at < ?
        """, [cutoff.isoformat()])

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted

    def start_cleanup_thread(self, interval_seconds: float = 10.0):
        """启动后台清理线程"""
        if self._running:
            return

        self._running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._cleanup_thread.start()
        print(f"[PersistentQueue] 后台清理线程启动，间隔 {interval_seconds}s")

    def stop_cleanup_thread(self):
        """停止后台清理线程"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)

    def _cleanup_loop(self, interval: float):
        """清理循环"""
        while self._running:
            try:
                recovered = self.timeout_recover()
                if recovered > 0:
                    print(f"[PersistentQueue] 超时恢复: {recovered} 条")
            except Exception as e:
                print(f"[PersistentQueue] 清理错误: {e}")

            time.sleep(interval)

    def _row_to_message(self, row: sqlite3.Row) -> Message:
        """行转消息"""
        return Message(
            id=row["id"],
            queue_name=row["queue_name"],
            payload=json.loads(row["payload"]),
            status=MessageStatus(row["status"]),
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            retry_count=row["retry_count"],
            max_retries=row["max_retries"],
            timeout_seconds=row["timeout_seconds"],
            trace_id=row["trace_id"],
            metadata=row["metadata"]
        )


class QueueWorker:
    """
    队列 Worker - 处理消息的消费者
    """

    def __init__(self, queue: PersistentMessageQueue,
                 queue_name: str,
                 handler: Callable[[Dict], Any],
                 concurrency: int = 5):
        self.queue = queue
        self.queue_name = queue_name
        self.handler = handler
        self.concurrency = concurrency
        self._running = False
        self._workers: List[threading.Thread] = []

    def start(self):
        """启动 Worker"""
        if self._running:
            return

        self._running = True
        for i in range(self.concurrency):
            t = threading.Thread(target=self._worker_loop, args=(i,), daemon=True)
            t.start()
            self._workers.append(t)

        print(f"[QueueWorker] 启动 {self.concurrency} 个 Worker 处理队列: {self.queue_name}")

    def stop(self):
        """停止 Worker"""
        self._running = False
        for t in self._workers:
            t.join(timeout=5)
        print("[QueueWorker] 已停止")

    def _worker_loop(self, worker_id: int):
        """Worker 循环"""
        while self._running:
            try:
                msg = self.queue.dequeue(self.queue_name, block=True, timeout=1.0)
                if not msg:
                    continue

                print(f"[Worker-{worker_id}] 处理消息: {msg.id[:8]}...")

                try:
                    result = self.handler(msg.payload)
                    self.queue.ack(msg.id)
                    print(f"[Worker-{worker_id}] 完成: {msg.id[:8]}")
                except Exception as e:
                    print(f"[Worker-{worker_id}] 失败: {msg.id[:8]} - {e}")
                    self.queue.nack(msg.id, requeue=True)

            except Exception as e:
                print(f"[Worker-{worker_id}] 错误: {e}")


# ============================================================================
# 测试
# ============================================================================

def test_persistent_queue():
    print("=" * 60)
    print("  PersistentMessageQueue P1 测试")
    print("=" * 60)

    import os
    db_path = "test_queue.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    queue = PersistentMessageQueue(db_path)

    print("\n--- 1. 基本入队/出队测试 ---\n")

    msg_id = queue.enqueue(
        "test_queue",
        {"task": "process_file", "path": "src/model.py"},
        trace_id="trace_001"
    )
    print(f"✅ 入队: {msg_id}")

    msg = queue.dequeue("test_queue")
    print(f"✅ 出队: {msg.id} - {msg.payload}")

    queue.ack(msg.id)
    print("✅ ACK 确认")

    stats = queue.get_stats()
    print(f"统计: {stats}")

    print("\n--- 2. 批量入队/消费测试 ---\n")

    for i in range(5):
        queue.enqueue("batch_queue", {"task": f"task_{i}", "index": i})

    print(f"已入队 5 条消息")

    consumed = 0
    while True:
        msg = queue.dequeue("batch_queue", block=False)
        if not msg:
            break
        print(f"  消费: {msg.payload}")
        queue.ack(msg.id)
        consumed += 1

    print(f"✅ 共消费: {consumed} 条")

    print("\n--- 3. 重试机制测试 ---\n")

    msg_id = queue.enqueue(
        "retry_queue",
        {"task": "will_fail"},
        max_retries=3
    )

    msg = queue.dequeue("retry_queue")
    print(f"出队: {msg.id}, 重试次数: {msg.retry_count}")

    queue.nack(msg.id, requeue=True)
    print("NACK 拒绝，要求重试")

    msg = queue.dequeue("retry_queue")
    print(f"重新出队: {msg.id}, 重试次数: {msg.retry_count}")

    queue.nack(msg.id, requeue=False)
    print("NACK 拒绝，不重试（已达上限）")

    stats = queue.get_stats("retry_queue")
    print(f"队列状态: {stats}")

    print("\n--- 4. 超时恢复测试 ---\n")

    queue.start_cleanup_thread(interval_seconds=1.0)

    msg_id = queue.enqueue(
        "timeout_queue",
        {"task": "slow_task"},
        timeout_seconds=0.5
    )

    msg = queue.dequeue("timeout_queue")
    print(f"出队: {msg.id}, 超时时间: {msg.timeout_seconds}s")

    print("等待超时...")
    time.sleep(2)

    recovered = queue.timeout_recover()
    print(f"超时恢复: {recovered} 条")

    stats = queue.get_stats("timeout_queue")
    print(f"恢复后状态: {stats}")

    queue.stop_cleanup_thread()

    print("\n--- 5. 追踪 ID 查询测试 ---\n")

    trace_id = "trace_batch_001"
    for i in range(3):
        queue.enqueue("trace_queue", {"task": i}, trace_id=trace_id)

    messages = queue.get_by_trace(trace_id)
    print(f"追踪 {trace_id} 的消息数: {len(messages)}")

    print("\n--- 6. 统计信息 ---\n")

    stats = queue.get_stats()
    print(f"全局统计: {stats}")

    if os.path.exists(db_path):
        os.remove(db_path)

    print("\n" + "=" * 60)
    print("  ✅ PersistentMessageQueue 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_persistent_queue()

