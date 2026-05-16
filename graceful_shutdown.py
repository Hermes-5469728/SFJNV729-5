"""
GracefulShutdown - P0: 优雅关闭机制

问题：Server 模式接收请求期间，如何停止服务而不丢失正在处理的请求？
解决：Queue 层 + Worker 层配合实现优雅关闭
"""

import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass


class ShutdownState(Enum):
    RUNNING = "running"           # 运行中
    DRAINING = "draining"         # 排空中（停止接收新任务）
    STOPPING = "stopping"         # 停止中（等待处理完成）
    STOPPED = "stopped"           # 已停止


@dataclass
class InFlightTask:
    """正在处理的任务"""
    id: str
    worker_id: str
    queue_name: str
    started_at: str
    request_id: Optional[str]
    status: str


class GracefulShutdown:
    """
    优雅关闭控制器

    流程：
    1. RUNNING → DRAINING：停止接收新任务，保留处理中的任务
    2. DRAINING → STOPPING：所有任务处理完成后，开始关闭
    3. STOPPING → STOPPED：超时则强制关闭

    使用方式：
    shutdown = GracefulShutdown(timeout_seconds=30)

    # Server 入口
    if shutdown.should_accept_request():
        queue.enqueue(...)
    else:
        return 503

    # Worker 处理前
    shutdown.track_task(worker_id, task_id)
    try:
        process_task(task)
    finally:
        shutdown.untrack_task(task_id)

    # 关闭信号处理
    shutdown.initiate_shutdown()
    shutdown.wait_for_completion()
    """

    def __init__(self, timeout_seconds: float = 60.0,
                 drain_timeout_seconds: float = 30.0):
        self.timeout_seconds = timeout_seconds
        self.drain_timeout_seconds = drain_timeout_seconds
        self.state = ShutdownState.RUNNING
        self._lock = threading.RLock()
        self._in_flight_tasks: Dict[str, InFlightTask] = {}
        self._state_changed = threading.Condition(self._lock)
        self._shutdown_initiated_at: Optional[str] = None
        self._state_listeners: List[Callable[[ShutdownState], None]] = []

    @property
    def is_running(self) -> bool:
        return self.state == ShutdownState.RUNNING

    @property
    def is_draining(self) -> bool:
        return self.state == ShutdownState.DRAINING

    @property
    def is_stopping(self) -> bool:
        return self.state == ShutdownState.STOPPING

    @property
    def is_stopped(self) -> bool:
        return self.state == ShutdownState.STOPPED

    def should_accept_request(self) -> bool:
        """是否应该接收新请求"""
        with self._lock:
            if self.state == ShutdownState.RUNNING:
                return True
            return False

    def track_task(self, worker_id: str, task_id: str,
                 queue_name: str = "default",
                 request_id: Optional[str] = None) -> bool:
        """
        跟踪正在处理的任务

        Returns:
            bool: 是否成功跟踪（False 表示正在关闭，不应处理新任务）
        """
        with self._lock:
            if self.state == ShutdownState.STOPPING:
                return False

            if self.state == ShutdownState.DRAINING:
                if len(self._in_flight_tasks) > 0:
                    return False

            task = InFlightTask(
                id=task_id,
                worker_id=worker_id,
                queue_name=queue_name,
                started_at=datetime.now().isoformat(),
                request_id=request_id,
                status="running"
            )
            self._in_flight_tasks[task_id] = task
            return True

    def untrack_task(self, task_id: str, status: str = "completed"):
        """取消跟踪已完成的任务"""
        with self._lock:
            if task_id in self._in_flight_tasks:
                self._in_flight_tasks[task_id].status = status
                del self._in_flight_tasks[task_id]
                self._state_changed.notify_all()

    def get_in_flight_tasks(self) -> List[InFlightTask]:
        """获取正在处理的任务"""
        with self._lock:
            return list(self._in_flight_tasks.values())

    def get_in_flight_count(self) -> int:
        """获取正在处理的任务数量"""
        with self._lock:
            return len(self._in_flight_tasks)

    def initiate_shutdown(self):
        """发起关闭（从 RUNNING → DRAINING）"""
        with self._lock:
            if self.state != ShutdownState.RUNNING:
                return

            self._shutdown_initiated_at = datetime.now().isoformat()
            self.state = ShutdownState.DRAINING
            print(f"[GracefulShutdown] 进入 DRAINING 状态")
            self._notify_listeners()

    def _notify_listeners(self):
        """通知状态变更监听器"""
        for listener in self._state_listeners:
            try:
                listener(self.state)
            except Exception as e:
                print(f"[GracefulShutdown] 监听器错误: {e}")

    def add_state_listener(self, listener: Callable[[ShutdownState], None]):
        """添加状态变更监听器"""
        self._state_listeners.append(listener)

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        等待所有任务完成或超时

        Returns:
            bool: True 表示所有任务已完成，False 表示超时
        """
        timeout = timeout or self.timeout_seconds
        start_time = time.time()

        with self._lock:
            if self.state == ShutdownState.DRAINING:
                print(f"[GracefulShutdown] 等待 {len(self._in_flight_tasks)} 个任务完成...")
                self.state = ShutdownState.STOPPING
                self._notify_listeners()

            while len(self._in_flight_tasks) > 0:
                elapsed = time.time() - start_time
                remaining = timeout - elapsed

                if remaining <= 0:
                    print(f"[GracefulShutdown] 超时，强制关闭 ({len(self._in_flight_tasks)} 个任务未完成)")
                    self.state = ShutdownState.STOPPED
                    self._notify_listeners()
                    return False

                print(f"[GracefulShutdown] 剩余 {len(self._in_flight_tasks)} 个任务，等待 {remaining:.1f}s...")
                self._state_changed.wait(timeout=min(remaining, 5.0))

            print(f"[GracefulShutdown] 所有任务已完成")
            self.state = ShutdownState.STOPPED
            self._notify_listeners()
            return True

    def force_stop(self):
        """强制停止（跳过优雅关闭）"""
        with self._lock:
            print(f"[GracefulShutdown] 强制停止 ({len(self._in_flight_tasks)} 个任务被中断)")
            self._in_flight_tasks.clear()
            self.state = ShutdownState.STOPPED
            self._notify_listeners()

    def get_stats(self) -> Dict[str, Any]:
        """获取状态统计"""
        with self._lock:
            return {
                "state": self.state.value,
                "in_flight_count": len(self._in_flight_tasks),
                "in_flight_tasks": [
                    {
                        "id": t.id,
                        "worker_id": t.worker_id,
                        "started_at": t.started_at,
                        "duration_seconds": (datetime.now() - datetime.fromisoformat(t.started_at)).total_seconds()
                    }
                    for t in self._in_flight_tasks.values()
                ],
                "shutdown_initiated_at": self._shutdown_initiated_at
            }


class QueueWithGracefulShutdown:
    """
    支持优雅关闭的消息队列

    将 GracefulShutdown 集成到队列操作中：
    - 入队检查是否应该接收新任务
    - 出队检查是否应该继续处理
    """

    def __init__(self, queue, graceful_shutdown: GracefulShutdown):
        self.queue = queue
        self.shutdown = graceful_shutdown

    def enqueue(self, queue_name: str, payload: Dict[str, Any],
               trace_id: Optional[str] = None) -> Optional[str]:
        """入队（检查是否应该接收新任务）"""
        if not self.shutdown.should_accept_request():
            return None
        return self.queue.enqueue(queue_name, payload, trace_id=trace_id)

    def dequeue(self, queue_name: str, worker_id: str,
               block: bool = True, timeout: Optional[float] = None) -> Optional[Any]:
        """出队（检查是否应该继续处理）"""
        msg = self.queue.dequeue(queue_name, block=block, timeout=timeout)

        if msg:
            tracked = self.shutdown.track_task(
                worker_id=worker_id,
                task_id=msg.id,
                queue_name=queue_name,
                request_id=msg.trace_id
            )
            if not tracked:
                self.queue.nack(msg.id, requeue=True)
                return None

        return msg

    def ack(self, message_id: str):
        """确认消息"""
        self.queue.ack(message_id)
        self.shutdown.untrack_task(message_id)

    def nack(self, message_id: str, requeue: bool = True):
        """拒绝消息"""
        self.queue.nack(message_id, requeue=requeue)
        self.shutdown.untrack_task(message_id, status="failed")


class WorkerWithGracefulShutdown:
    """
    支持优雅关闭的 Worker

    特性：
    - 监听关闭信号，自动停止接收新任务
    - 等待处理中的任务完成后才退出
    """

    def __init__(self, queue_with_graceful: QueueWithGracefulShutdown,
                 queue_name: str,
                 handler: Callable[[Dict], Any],
                 worker_id: str,
                 graceful_shutdown: GracefulShutdown):
        self.queue = queue_with_graceful
        self.queue_name = queue_name
        self.handler = handler
        self.worker_id = worker_id
        self.shutdown = graceful_shutdown
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """启动 Worker"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        print(f"[Worker-{self.worker_id}] 启动")

    def stop(self):
        """停止 Worker（等待处理完成）"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print(f"[Worker-{self.worker_id}] 停止")

    def _worker_loop(self):
        """Worker 循环"""
        while self._running:
            if self.shutdown.is_stopping:
                break

            try:
                msg = self.queue.dequeue(
                    self.queue_name,
                    worker_id=self.worker_id,
                    block=True,
                    timeout=1.0
                )

                if not msg:
                    continue

                try:
                    result = self.handler(msg.payload)
                    self.queue.ack(msg.id)
                except Exception as e:
                    print(f"[Worker-{self.worker_id}] 处理失败: {e}")
                    self.queue.nack(msg.id, requeue=True)

            except Exception as e:
                if self._running:
                    print(f"[Worker-{self.worker_id}] 错误: {e}")


# ============================================================================
# 测试
# ============================================================================

def test_graceful_shutdown():
    print("=" * 60)
    print("  GracefulShutdown P0 测试")
    print("=" * 60)

    import os
    db_path = "test_graceful.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    from persistent_queue import PersistentMessageQueue

    queue = PersistentMessageQueue(db_path)
    queue.start_cleanup_thread(interval_seconds=1.0)

    shutdown = GracefulShutdown(
        timeout_seconds=10.0,
        drain_timeout_seconds=5.0
    )

    queue_with_graceful = QueueWithGracefulShutdown(queue, shutdown)

    def task_handler(payload: Dict) -> str:
        task_type = payload.get("type", "normal")
        duration = payload.get("duration", 0.1)

        print(f"  [处理中] {payload}")
        time.sleep(duration)
        return f"completed: {payload}"

    worker1 = WorkerWithGracefulShutdown(
        queue_with_graceful,
        "test_queue",
        task_handler,
        "worker_1",
        shutdown
    )

    print("\n--- 1. 基本入队/出队测试 ---\n")

    task_id = queue_with_graceful.enqueue("test_queue", {"type": "normal", "duration": 0.1})
    print(f"入队任务: {task_id}")

    tracked = shutdown.track_task("worker_1", task_id, "test_queue")
    print(f"跟踪任务: {tracked}")

    print("等待处理...")
    time.sleep(0.2)

    shutdown.untrack_task(task_id)
    print(f"完成任务: {shutdown.get_in_flight_count()} 个进行中")

    print("\n--- 2. 优雅关闭流程测试 ---\n")

    for i in range(5):
        queue_with_graceful.enqueue("test_queue", {"type": f"task_{i}", "duration": 0.5})

    worker1.start()

    print(f"当前状态: {shutdown.state.value}, 进行中: {shutdown.get_in_flight_count()}")

    print("\n发起关闭...")
    shutdown.initiate_shutdown()

    print(f"关闭后状态: {shutdown.state.value}")
    print(f"是否接收新请求: {shutdown.should_accept_request()}")

    new_task_id = queue_with_graceful.enqueue("test_queue", {"type": "new", "duration": 0.1})
    print(f"尝试入队新任务: {new_task_id}（应该被拒绝）")

    print("\n等待任务完成...")
    completed = shutdown.wait_for_completion(timeout=15.0)

    print(f"关闭完成: {completed}")
    print(f"最终状态: {shutdown.state.value}")

    worker1.stop()

    queue.stop_cleanup_thread()

    print("\n--- 3. 强制关闭测试 ---\n")

    for i in range(3):
        queue.enqueue("test_queue", {"type": f"task_{i}", "duration": 2.0})

    worker2 = WorkerWithGracefulShutdown(
        queue_with_graceful,
        "test_queue",
        task_handler,
        "worker_2",
        shutdown
    )

    worker2.start()

    time.sleep(0.3)

    print(f"进行中任务: {shutdown.get_in_flight_count()}")

    print("强制关闭...")
    shutdown.force_stop()

    print(f"最终状态: {shutdown.state.value}")
    print(f"进行中任务: {shutdown.get_in_flight_count()}")

    worker2.stop()

    print("\n--- 4. 状态变更监听器测试 ---\n")

    state_changes = []

    def state_listener(state: ShutdownState):
        state_changes.append(state.value)
        print(f"  [监听器] 状态变更为: {state.value}")

    shutdown2 = GracefulShutdown(timeout_seconds=5.0)
    shutdown2.add_state_listener(state_listener)

    shutdown2.initiate_shutdown()
    time.sleep(0.1)

    shutdown2.wait_for_completion()

    print(f"状态变更序列: {state_changes}")

    if os.path.exists(db_path):
        os.remove(db_path)

    print("\n" + "=" * 60)
    print("  ✅ GracefulShutdown 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_graceful_shutdown()

