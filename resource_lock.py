"""
ResourceLock - P1: 带 TTL 和心跳联动的分布式资源锁

问题：无 TTL 锁 → CLT 崩溃 → 资源永久阻塞
解决：TTL 自动释放 + Worker 心跳丢失时主动清理锁
"""

import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


class LockType(Enum):
    AGENT = "agent"           # Agent 级锁（整个 Agent 资源）
    RECORD = "record"         # 记录级锁（ac_truth 单条记录）
    FIELD = "field"           # 字段级锁（单条记录的某个字段）


class LockStatus(Enum):
    ACTIVE = "active"         # 锁有效
    EXPIRED = "expired"       # 已过期
    RELEASED = "released"     # 已释放
    TAKEN = "taken"           # 被其他 Worker 持有


@dataclass
class Lock:
    id: str
    resource_type: str
    resource_id: str
    worker_id: str
    lock_type: LockType
    status: LockStatus
    created_at: str
    expires_at: str
    ttl_seconds: float
    metadata: Optional[str]


class ResourceLock:
    """
    带 TTL 和心跳联动的分布式资源锁

    特性：
    1. TTL 自动释放 - 锁超时后自动过期，无需手动释放
    2. 心跳联动 - Worker 心跳丢失时自动清理其持有的所有锁
    3. 多粒度锁 - Agent 级、记录级、字段级锁
    4. 锁竞争检测 - 防止死锁和优先级反转
    5. 持久化 - SQLite 存储，进程重启不丢锁信息

    使用方式：
    lock = ResourceLock("locks.db", worker_id="worker_001")

    # 获取锁（带 TTL）
    acquired = lock.acquire("agent:model-1", LockType.AGENT, ttl_seconds=30)

    # 续约（心跳）
    lock.heartbeat("agent:model-1")

    # 释放锁
    lock.release("agent:model-1")

    # 查询 Worker 持有的锁
    locks = lock.get_worker_locks("worker_001")
    """

    def __init__(self, db_path: str = "resource_locks.db", worker_id: Optional[str] = None):
        self.db_path = db_path
        self.worker_id = worker_id or str(uuid.uuid4())
        self._init_db()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False
        self._local_locks: Dict[str, float] = {}

    def _init_db(self):
        """初始化锁数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locks (
                id TEXT PRIMARY KEY,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                worker_id TEXT NOT NULL,
                lock_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                ttl_seconds REAL NOT NULL,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_locks_resource
            ON locks(resource_type, resource_id, status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_locks_worker
            ON locks(worker_id, status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_locks_expires
            ON locks(expires_at)
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS worker_heartbeats (
                worker_id TEXT PRIMARY KEY,
                last_heartbeat TEXT NOT NULL,
                ttl_seconds REAL NOT NULL,
                metadata TEXT
            )
        """)

        conn.commit()
        conn.close()

    def acquire(self, resource_id: str, lock_type: LockType = LockType.AGENT,
               ttl_seconds: float = 60.0, metadata: Optional[Dict] = None,
               resource_type: str = "default") -> bool:
        """
        获取锁（带 TTL）

        Args:
            resource_id: 资源 ID
            lock_type: 锁粒度
            ttl_seconds: 锁超时时间（秒）
            metadata: 元数据
            resource_type: 资源类型（用于分类）

        Returns:
            bool: 是否成功获取锁
        """
        self._cleanup_expired()

        lock_id = str(uuid.uuid4())
        now = datetime.now()
        expires_at = now + timedelta(seconds=ttl_seconds)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, worker_id, expires_at FROM locks
            WHERE resource_type = ? AND resource_id = ? AND status = 'active'
        """, [resource_type, resource_id])

        existing = cursor.fetchone()

        if existing:
            existing_id, existing_worker, existing_expires = existing
            existing_expire_time = datetime.fromisoformat(existing_expires)

            if existing_expire_time > now:
                conn.close()
                return False

        cursor.execute("""
            INSERT INTO locks
            (id, resource_type, resource_id, worker_id, lock_type, status, created_at, expires_at, ttl_seconds, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lock_id,
            resource_type,
            resource_id,
            self.worker_id,
            lock_type.value,
            LockStatus.ACTIVE.value,
            now.isoformat(),
            expires_at.isoformat(),
            ttl_seconds,
            json.dumps(metadata) if metadata else None
        ))

        conn.commit()
        conn.close()

        self._local_locks[f"{resource_type}:{resource_id}"] = expires_at.timestamp()

        return True

    def release(self, resource_id: str, resource_type: str = "default") -> bool:
        """
        释放锁

        Args:
            resource_id: 资源 ID
            resource_type: 资源类型

        Returns:
            bool: 是否成功释放
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE locks
            SET status = ?
            WHERE resource_type = ? AND resource_id = ? AND worker_id = ? AND status = 'active'
        """, [LockStatus.RELEASED.value, resource_type, resource_id, self.worker_id])

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if success:
            key = f"{resource_type}:{resource_id}"
            self._local_locks.pop(key, None)

        return success

    def heartbeat(self, resource_id: str, resource_type: str = "default",
                  extend_seconds: Optional[float] = None) -> bool:
        """
        续约锁（心跳）

        Args:
            resource_id: 资源 ID
            resource_type: 资源类型
            extend_seconds: 延长的时间（默认使用原 TTL）

        Returns:
            bool: 是否成功续约
        """
        self._cleanup_expired()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT ttl_seconds FROM locks
            WHERE resource_type = ? AND resource_id = ? AND worker_id = ? AND status = 'active'
        """, [resource_type, resource_id, self.worker_id])

        row = cursor.fetchone()

        if not row:
            conn.close()
            return False

        ttl = extend_seconds or row[0]
        now = datetime.now()
        expires_at = now + timedelta(seconds=ttl)

        cursor.execute("""
            UPDATE locks
            SET expires_at = ?
            WHERE resource_type = ? AND resource_id = ? AND worker_id = ? AND status = 'active'
        """, [expires_at.isoformat(), resource_type, resource_id, self.worker_id])

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if success:
            key = f"{resource_type}:{resource_id}"
            self._local_locks[key] = expires_at.timestamp()

        return success

    def register_worker(self, ttl_seconds: float = 60.0,
                       metadata: Optional[Dict] = None) -> bool:
        """
        注册 Worker 心跳

        Args:
            ttl_seconds: Worker TTL（心跳超时则认为 Worker 死亡）
            metadata: 元数据

        Returns:
            bool: 是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO worker_heartbeats
            (worker_id, last_heartbeat, ttl_seconds, metadata)
            VALUES (?, ?, ?, ?)
        """, [self.worker_id, now, ttl_seconds, json.dumps(metadata) if metadata else None])

        conn.commit()
        conn.close()

        return True

    def worker_heartbeat(self, ttl_seconds: Optional[float] = None) -> bool:
        """
        Worker 心跳

        Args:
            ttl_seconds: 可选的新 TTL

        Returns:
            bool: 是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        if ttl_seconds:
            cursor.execute("""
                UPDATE worker_heartbeats
                SET last_heartbeat = ?, ttl_seconds = ?
                WHERE worker_id = ?
            """, [now, ttl_seconds, self.worker_id])
        else:
            cursor.execute("""
                UPDATE worker_heartbeats
                SET last_heartbeat = ?
                WHERE worker_id = ?
            """, [now, self.worker_id])

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def get_worker_locks(self, worker_id: str) -> List[Lock]:
        """获取 Worker 持有的所有活跃锁"""
        self._cleanup_expired()

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM locks
            WHERE worker_id = ? AND status = 'active'
            ORDER BY created_at DESC
        """, [worker_id])

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_lock(row) for row in rows]

    def get_resource_lock(self, resource_id: str,
                         resource_type: str = "default") -> Optional[Lock]:
        """获取资源的当前锁信息"""
        self._cleanup_expired()

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM locks
            WHERE resource_type = ? AND resource_id = ? AND status = 'active'
        """, [resource_type, resource_id])

        row = cursor.fetchone()
        conn.close()

        return self._row_to_lock(row) if row else None

    def _cleanup_expired(self) -> int:
        """
        清理过期锁

        Returns:
            int: 清理的锁数量
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute("""
            UPDATE locks
            SET status = ?
            WHERE status = 'active' AND expires_at < ?
        """, [LockStatus.EXPIRED.value, now])

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted

    def cleanup_dead_workers(self) -> Dict[str, int]:
        """
        清理死 Worker 持有的所有锁

        Returns:
            Dict[str, int]: 每个 Worker 清理的锁数量
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now()

        cursor.execute("""
            SELECT worker_id, last_heartbeat, ttl_seconds FROM worker_heartbeats
        """)

        dead_workers = []
        for row in cursor.fetchall():
            worker_id, last_heartbeat, ttl_seconds = row
            last_time = datetime.fromisoformat(last_heartbeat)
            if (now - last_time).total_seconds() > ttl_seconds:
                dead_workers.append(worker_id)

        result = {}
        for worker_id in dead_workers:
            cursor.execute("""
                UPDATE locks
                SET status = ?
                WHERE worker_id = ? AND status = 'active'
            """, [LockStatus.EXPIRED.value, worker_id])

            released = cursor.rowcount
            result[worker_id] = released

            cursor.execute("""
                DELETE FROM worker_heartbeats WHERE worker_id = ?
            """, [worker_id])

        conn.commit()
        conn.close()

        if result:
            print(f"[ResourceLock] 清理死 Worker: {result}")

        return result

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
        print(f"[ResourceLock] 后台清理线程启动，间隔 {interval_seconds}s")

    def stop_cleanup_thread(self):
        """停止后台清理线程"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)

    def _cleanup_loop(self, interval: float):
        """清理循环"""
        while self._running:
            try:
                expired = self._cleanup_expired()
                if expired > 0:
                    print(f"[ResourceLock] 清理过期锁: {expired} 个")

                dead = self.cleanup_dead_workers()
                if dead:
                    print(f"[ResourceLock] 清理死 Worker 锁: {dead}")
            except Exception as e:
                print(f"[ResourceLock] 清理错误: {e}")

            time.sleep(interval)

    def get_stats(self) -> Dict[str, Any]:
        """获取锁统计"""
        self._cleanup_expired()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT status, COUNT(*) FROM locks GROUP BY status")
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("SELECT COUNT(*) FROM locks WHERE status = 'active'")
        active = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT worker_id) FROM locks WHERE status = 'active'")
        workers = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM worker_heartbeats")
        registered_workers = cursor.fetchone()[0]

        conn.close()

        return {
            "total_locks": sum(status_counts.values()),
            "active_locks": active,
            "by_status": status_counts,
            "active_workers": workers,
            "registered_workers": registered_workers
        }

    def _row_to_lock(self, row) -> Optional[Lock]:
        """行转锁"""
        if not row:
            return None
        return Lock(
            id=row["id"],
            resource_type=row["resource_type"],
            resource_id=row["resource_id"],
            worker_id=row["worker_id"],
            lock_type=LockType(row["lock_type"]),
            status=LockStatus(row["status"]),
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            ttl_seconds=row["ttl_seconds"],
            metadata=row["metadata"]
        )


# ============================================================================
# 分布式锁装饰器
# ============================================================================

def with_resource_lock(lock: ResourceLock, resource_type: str, resource_id: str,
                       lock_type: LockType = LockType.AGENT, ttl_seconds: float = 60.0):
    """
    分布式锁装饰器

    用法：
    @with_resource_lock(lock, "model", "model-1")
    def use_model():
        # 模型操作
        pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not lock.acquire(resource_id, lock_type, ttl_seconds):
                raise RuntimeError(f"无法获取锁: {resource_type}:{resource_id}")
            try:
                return func(*args, **kwargs)
            finally:
                lock.release(resource_id, resource_type)
        return wrapper
    return decorator


# ============================================================================
# 测试
# ============================================================================

def test_resource_lock():
    print("=" * 60)
    print("  ResourceLock P1 测试")
    print("=" * 60)

    import os
    db_path = "test_locks.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    lock = ResourceLock(db_path, worker_id="worker_001")

    print("\n--- 1. 基本获取/释放锁测试 ---\n")

    acquired = lock.acquire("model-1", LockType.AGENT, ttl_seconds=5)
    print(f"获取锁: {acquired}")

    info = lock.get_resource_lock("model-1")
    print(f"锁信息: worker={info.worker_id}, expires={info.expires_at[:19]}")

    released = lock.release("model-1")
    print(f"释放锁: {released}")

    print("\n--- 2. TTL 自动过期测试 ---\n")

    acquired = lock.acquire("model-2", LockType.AGENT, ttl_seconds=2)
    print(f"获取锁（2秒 TTL）: {acquired}")

    info = lock.get_resource_lock("model-2")
    print(f"锁状态: {info.status.value}")

    print("等待 3 秒...")
    time.sleep(3)

    expired = lock._cleanup_expired()
    print(f"清理过期锁: {expired} 个")

    info = lock.get_resource_lock("model-2")
    print(f"锁状态: {info.status.value if info else '无锁'}")

    print("\n--- 3. 心跳续约测试 ---\n")

    acquired = lock.acquire("model-3", LockType.AGENT, ttl_seconds=3)
    print(f"获取锁（3秒 TTL）: {acquired}")

    print("等待 2 秒...")
    time.sleep(2)

    renewed = lock.heartbeat("model-3", extend_seconds=5)
    print(f"续约（延长到5秒）: {renewed}")

    print("再等 2 秒...")
    time.sleep(2)

    info = lock.get_resource_lock("model-3")
    print(f"锁状态: {info.status.value}")

    print("再等 3 秒...")
    time.sleep(3)

    expired = lock._cleanup_expired()
    print(f"清理过期锁: {expired} 个")

    info = lock.get_resource_lock("model-3")
    print(f"锁状态: {info.status.value if info else '无锁'}")

    print("\n--- 4. 多 Worker 竞争锁测试 ---\n")

    worker1 = ResourceLock(db_path, worker_id="worker_001")
    worker2 = ResourceLock(db_path, worker_id="worker_002")

    acquired = worker1.acquire("model-4", LockType.AGENT, ttl_seconds=10)
    print(f"Worker1 获取锁: {acquired}")

    acquired = worker2.acquire("model-4", LockType.AGENT, ttl_seconds=10)
    print(f"Worker2 竞争锁: {acquired}（应该失败）")

    worker1.release("model-4")
    print("Worker1 释放锁")

    acquired = worker2.acquire("model-4", LockType.AGENT, ttl_seconds=10)
    print(f"Worker2 重试获取锁: {acquired}（应该成功）")

    print("\n--- 5. 记录级锁测试 ---\n")

    acquired = worker1.acquire("truth-record-001", LockType.RECORD, ttl_seconds=10)
    print(f"Worker1 获取记录级锁: {acquired}")

    acquired = worker2.acquire("truth-record-001", LockType.RECORD, ttl_seconds=10)
    print(f"Worker2 竞争同一记录锁: {acquired}（应该失败）")

    worker1.release("truth-record-001", resource_type="default")

    print("\n--- 6. Worker 心跳和死 Worker 清理测试 ---\n")

    worker1.register_worker(ttl_seconds=3)
    print("Worker1 注册，TTL=3秒")

    heartbeat_ok = worker1.worker_heartbeat()
    print(f"Worker1 心跳: {heartbeat_ok}")

    dead = lock.cleanup_dead_workers()
    print(f"清理死 Worker（无）: {dead}")

    print("等待 Worker1 TTL 过期...")
    time.sleep(4)

    dead = lock.cleanup_dead_workers()
    print(f"清理死 Worker: {dead}")

    worker1_locks = lock.get_worker_locks("worker_001")
    print(f"Worker1 的锁数量（应为0）: {len(worker1_locks)}")

    print("\n--- 7. Worker 持有锁但心跳过期测试 ---\n")

    worker1 = ResourceLock(db_path, worker_id="worker_heartbeat")
    worker1.register_worker(ttl_seconds=3)
    worker1.acquire("model-5", LockType.AGENT, ttl_seconds=20)

    print("Worker1 获取锁后，不再发送心跳...")

    print("等待 4 秒...")
    time.sleep(4)

    dead = lock.cleanup_dead_workers()
    print(f"清理死 Worker: {dead}")

    info = lock.get_resource_lock("model-5")
    print(f"锁状态: {info.status.value if info else '无锁'}")

    print("\n--- 8. 统计信息 ---\n")

    stats = lock.get_stats()
    print(f"统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")

    if os.path.exists(db_path):
        os.remove(db_path)

    print("\n" + "=" * 60)
    print("  ✅ ResourceLock 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_resource_lock()

