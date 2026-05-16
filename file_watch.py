"""
File Watch 服务 - 监听 Trae 工作目录

Phase B 核心组件：
1. 使用 watchdog 监听文件变更
2. 防抖（debounce）：2秒内的重复变更合并为一次
3. 变更指纹（文件内容哈希）：哈希未变则不触发治理
4. 自动跳过 __pycache__、.git 等目录
"""

import asyncio
import hashlib
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object


class FileChangeEvent:
    """文件变更事件"""

    def __init__(
        self,
        path: str,
        event_type: str,
        content_hash: Optional[str] = None,
        size: int = 0,
        timestamp: Optional[str] = None
    ):
        self.path = path
        self.event_type = event_type
        self.content_hash = content_hash
        self.size = size
        self.timestamp = timestamp or time.time()

    def __repr__(self):
        return f"FileChangeEvent({self.event_type}, {self.path})"


class ContentHasher:
    """文件内容哈希计算器"""

    @staticmethod
    def compute_hash(file_path: str) -> Optional[str]:
        """计算文件内容的 MD5 哈希"""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception:
            return None

    @staticmethod
    def compute_hash_incremental(file_path: str, chunk_size: int = 8192) -> Optional[str]:
        """增量计算哈希（大文件优化）"""
        try:
            md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                while chunk := f.read(chunk_size):
                    md5.update(chunk)
            return md5.hexdigest()
        except Exception:
            return None


class Debouncer:
    """
    防抖器

    特性：
    - 2秒内同一文件的重复变更合并为一次
    - 只有哈希真的变了才触发
    """

    DEBOUNCE_SECONDS = 2.0

    def __init__(self):
        self._pending: Dict[str, float] = {}
        self._last_hash: Dict[str, str] = {}

    def should_process(self, file_path: str, content_hash: str) -> bool:
        """
        判断是否应该处理这个变更

        返回 True 如果：
        1. 距离上次触发已经超过 DEBOUNCE_SECONDS
        2. 文件内容哈希确实变了
        """
        now = time.time()

        if file_path in self._pending:
            last_time = self._pending[file_path]
            if now - last_time < self.DEBOUNCE_SECONDS:
                return False

        last_hash = self._last_hash.get(file_path)
        if last_hash == content_hash:
            return False

        self._pending[file_path] = now
        self._last_hash[file_path] = content_hash

        return True

    def cleanup(self, max_age_seconds: float = 60.0):
        """清理过期的记录"""
        now = time.time()
        expired = [
            path for path, last_time in self._pending.items()
            if now - last_time > max_age_seconds
        ]

        for path in expired:
            self._pending.pop(path, None)


class FileWatchHandler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """文件系统事件处理器"""

    def __init__(
        self,
        callback: Callable[[FileChangeEvent], None],
        watch_extensions: Optional[list] = None,
        ignore_dirs: Optional[list] = None
    ):
        super().__init__()

        self.callback = callback
        self.watch_extensions = watch_extensions or [".py", ".js", ".ts", ".md", ".yaml", ".yml", ".json"]
        self.ignore_dirs = ignore_dirs or [
            "__pycache__",
            ".git",
            ".venv",
            "node_modules",
            ".idea",
            ".vscode",
            "dist",
            "build",
            ".pytest_cache"
        ]

        self.debouncer = Debouncer()
        self.content_hasher = ContentHasher()

    def _should_ignore(self, path: str) -> bool:
        """检查是否应该忽略这个路径"""
        path_obj = Path(path)

        for ignore_dir in self.ignore_dirs:
            if ignore_dir in path_obj.parts:
                return True

        if path_obj.suffix not in self.watch_extensions:
            return True

        return False

    def _create_event(self, path: str, event_type: str) -> Optional[FileChangeEvent]:
        """创建文件变更事件"""
        if self._should_ignore(path):
            return None

        content_hash = self.content_hasher.compute_hash_incremental(path)

        if not self.debouncer.should_process(path, content_hash or ""):
            return None

        size = os.path.getsize(path) if os.path.exists(path) else 0

        return FileChangeEvent(
            path=path,
            event_type=event_type,
            content_hash=content_hash,
            size=size
        )

    def on_modified(self, event: FileSystemEvent):
        if event.is_directory:
            return

        file_event = self._create_event(event.src_path, "modified")
        if file_event:
            self.callback(file_event)

    def on_created(self, event: FileSystemEvent):
        if event.is_directory:
            return

        file_event = self._create_event(event.src_path, "created")
        if file_event:
            self.callback(file_event)

    def on_deleted(self, event: FileSystemEvent):
        if event.is_directory:
            return

        file_event = FileChangeEvent(
            path=event.src_path,
            event_type="deleted"
        )
        self.callback(file_event)


class FileWatchService:
    """
    文件监控服务

    使用方式：
    service = FileWatchService("/path/to/watch")
    service.start()

    async def on_change(event):
        print(f"文件变更: {event}")

    service = FileWatchService("/path/to/watch", callback=on_change)
    service.start()
    """

    def __init__(
        self,
        watch_path: str,
        callback: Optional[Callable[[FileChangeEvent], None]] = None,
        recursive: bool = True
    ):
        if not WATCHDOG_AVAILABLE:
            raise RuntimeError("watchdog 库未安装: pip install watchdog")

        self.watch_path = Path(watch_path)
        self.callback = callback
        self.recursive = recursive

        self._observer: Optional[Observer] = None
        self._running = False
        self._handler: Optional[FileWatchHandler] = None

    def start(self):
        """启动文件监控"""
        if self._running:
            return

        if not self.watch_path.exists():
            raise FileNotFoundError(f"监控路径不存在: {self.watch_path}")

        self._handler = FileWatchHandler(
            callback=self._handle_change,
            watch_extensions=[".py", ".js", ".ts", ".jsx", ".tsx", ".md", ".yaml", ".yml", ".json"]
        )

        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            str(self.watch_path),
            recursive=self.recursive
        )

        self._observer.start()
        self._running = True

        print(f"[FileWatch] 启动监控: {self.watch_path}")

    def stop(self):
        """停止文件监控"""
        if not self._running:
            return

        if self._observer:
            self._observer.stop()
            self._observer.join()

        self._running = False

        print("[FileWatch] 停止监控")

    def _handle_change(self, event: FileChangeEvent):
        """处理文件变更事件"""
        print(f"[FileWatch] 变更: {event.event_type} - {event.path}")

        if event.content_hash:
            print(f"[FileWatch]   哈希: {event.content_hash}")

        if self.callback:
            try:
                self.callback(event)
            except Exception as e:
                print(f"[FileWatch] 回调错误: {e}")

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._running


async def watch_and_govern(
    watch_path: str,
    governance_check_func: Callable[[str], Dict[str, Any]]
):
    """
    监听文件变更并执行治理检查

    使用方式：
    async def check_governance(file_path: str) -> dict:
        # 调用 AC Server 的治理 API
        return await ac_client.governance_check(content)

    await watch_and_govern("/path/to/watch", check_governance)
    """
    if not WATCHDOG_AVAILABLE:
        print("[FileWatch] watchdog 未安装，使用模拟模式")
        print("[FileWatch] 安装命令: pip install watchdog")
        return

    governance_queue: asyncio.Queue = asyncio.Queue()

    async def process_changes():
        while True:
            event = await governance_queue.get()
            try:
                result = await governance_check_func(event.path)
                print(f"[FileWatch] 治理结果: {result}")
            except Exception as e:
                print(f"[FileWatch] 治理错误: {e}")

    async def on_change(event: FileChangeEvent):
        if event.event_type in ["created", "modified"]:
            await governance_queue.put(event)

    service = FileWatchService(watch_path, callback=on_change)
    service.start()

    try:
        await asyncio.gather(process_changes())
    except asyncio.CancelledError:
        service.stop()
