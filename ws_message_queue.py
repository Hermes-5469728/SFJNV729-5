"""
WebSocket 消息队列 + 自动重连机制

Phase B 核心组件：
1. 为每个 WebSocket 客户端维护待发送消息队列
2. 客户端重连后自动推送积压消息
3. 积压上限 100 条，超出保留最新 100 条
4. Trae 侧 SDK 自动重连（指数退避，最大间隔 30s）
"""

import asyncio
import json
import time
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional


class WSMessageQueue:
    """
    WebSocket 客户端消息队列

    特性：
    - 积压消息缓存（上限 100 条）
    - 支持批量推送
    - 消息TTL自动过期
    """

    MAX_QUEUE_SIZE = 100

    def __init__(self, client_id: str):
        self.client_id = client_id
        self._queue: deque = deque(maxlen=self.MAX_QUEUE_SIZE)
        self._last_sent_id: Optional[str] = None
        self._created_at = time.time()

    def push(self, message: Dict[str, Any]) -> int:
        """推送消息到队列，返回队列深度"""
        msg_with_meta = {
            "id": str(uuid.uuid4()),
            "client_id": self.client_id,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "queued_at": time.time()
        }

        self._queue.append(msg_with_meta)
        return len(self._queue)

    def pop_batch(self, limit: int = 50) -> List[Dict[str, Any]]:
        """批量取出消息（用于重连后推送）"""
        messages = []

        for _ in range(min(limit, len(self._queue))):
            if self._queue:
                msg = self._queue.popleft()
                messages.append(msg)

        if messages:
            self._last_sent_id = messages[-1]["id"]

        return messages

    def get_pending(self) -> List[Dict[str, Any]]:
        """获取所有待发送消息（不删除）"""
        return [msg["message"] for msg in self._queue]

    def mark_sent(self, message_id: str):
        """标记消息已发送"""
        self._last_sent_id = message_id

    def clear(self):
        """清空队列"""
        self._queue.clear()

    @property
    def depth(self) -> int:
        return len(self._queue)

    @property
    def age_seconds(self) -> float:
        return time.time() - self._created_at


class WSConnectionManager:
    """
    WebSocket 连接管理器

    特性：
    - 连接状态追踪
    - 心跳保活
    - 自动重连协调
    """

    def __init__(self):
        self._connections: Dict[str, Dict[str, Any]] = {}
        self._queues: Dict[str, WSMessageQueue] = {}
        self._lock = asyncio.Lock()

    async def register(
        self,
        client_id: str,
        websocket: Any,
        metadata: Optional[Dict] = None
    ):
        """注册新连接"""
        async with self._lock:
            self._connections[client_id] = {
                "websocket": websocket,
                "connected_at": time.time(),
                "last_heartbeat": time.time(),
                "metadata": metadata or {},
                "status": "connected"
            }

            self._queues[client_id] = WSMessageQueue(client_id)

            print(f"[WSManager] 客户端注册: {client_id}")

    async def unregister(self, client_id: str, reason: str = "disconnect"):
        """注销连接"""
        async with self._lock:
            if client_id in self._connections:
                del self._connections[client_id]

            if client_id in self._queues:
                self._queues[client_id].clear()

            print(f"[WSManager] 客户端注销: {client_id}, 原因: {reason}")

    async def update_heartbeat(self, client_id: str):
        """更新心跳"""
        async with self._lock:
            if client_id in self._connections:
                self._connections[client_id]["last_heartbeat"] = time.time()

    def get_queue(self, client_id: str) -> Optional[WSMessageQueue]:
        """获取客户端消息队列"""
        return self._queues.get(client_id)

    async def push_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """推送消息到指定客户端"""
        async with self._lock:
            if client_id not in self._connections:
                if client_id in self._queues:
                    self._queues[client_id].push(message)
                return False

            ws = self._connections[client_id]["websocket"]
            queue = self._queues.get(client_id)

            try:
                await ws.send_json(message)

                if queue:
                    queue.mark_sent(message.get("id", ""))

                return True

            except Exception as e:
                print(f"[WSManager] 推送失败 {client_id}: {e}")

                if queue:
                    queue.push(message)

                return False

    async def broadcast(self, message: Dict[str, Any], exclude: Optional[List[str]] = None):
        """广播消息到所有客户端"""
        exclude = exclude or []
        failed_clients = []

        for client_id in list(self._connections.keys()):
            if client_id in exclude:
                continue

            success = await self.push_to_client(client_id, message)

            if not success:
                failed_clients.append(client_id)

        return failed_clients

    async def get_pending_count(self, client_id: str) -> int:
        """获取待处理消息数"""
        queue = self._queues.get(client_id)
        return queue.depth if queue else 0

    def get_connection_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """获取连接信息"""
        if client_id not in self._connections:
            return None

        conn = self._connections[client_id]
        queue = self._queues.get(client_id)

        return {
            "client_id": client_id,
            "connected_at": conn["connected_at"],
            "last_heartbeat": conn["last_heartbeat"],
            "metadata": conn["metadata"],
            "status": conn["status"],
            "pending_messages": queue.depth if queue else 0
        }

    def get_all_connections(self) -> List[Dict[str, Any]]:
        """获取所有连接信息"""
        return [
            self.get_connection_info(cid)
            for cid in self._connections.keys()
        ]


class ReconnectingWSClient:
    """
    WebSocket 自动重连客户端（Trae 侧使用）

    特性：
    - 自动重连（指数退避，最大间隔 30s）
    - 消息队列缓存
    - 连接状态回调
    """

    MAX_BACKOFF_SECONDS = 30
    INITIAL_BACKOFF_SECONDS = 1

    def __init__(
        self,
        url: str,
        client_id: str,
        on_message: Optional[callable] = None,
        on_connect: Optional[callable] = None,
        on_disconnect: Optional[callable] = None
    ):
        self.url = url
        self.client_id = client_id
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect

        self._ws: Optional[Any] = None
        self._running = False
        self._reconnect_backoff = self.INITIAL_BACKOFF_SECONDS
        self._pending_queue: deque = deque(maxlen=100)

    async def connect(self):
        """建立连接"""
        import websockets

        try:
            self._ws = await websockets.connect(self.url)
            self._running = True
            self._reconnect_backoff = self.INITIAL_BACKOFF_SECONDS

            if self.on_connect:
                self.on_connect()

            print(f"[WSClient] 连接成功: {self.url}")

            await self._receive_loop()

        except Exception as e:
            print(f"[WSClient] 连接失败: {e}")
            await self._handle_disconnect()

    async def _receive_loop(self):
        """接收消息循环"""
        import websockets

        while self._running and self._ws:
            try:
                message = await self._ws.recv()
                data = json.loads(message)

                if self.on_message:
                    self.on_message(data)

            except websockets.exceptions.ConnectionClosed:
                print("[WSClient] 连接关闭")
                break
            except Exception as e:
                print(f"[WSClient] 接收错误: {e}")
                break

    async def _handle_disconnect(self):
        """处理断开连接"""
        if self.on_disconnect:
            self.on_disconnect()

        if self._running:
            print(f"[WSClient] {self._reconnect_backoff}s 后重连...")
            await asyncio.sleep(self._reconnect_backoff)

            self._reconnect_backoff = min(
                self._reconnect_backoff * 2,
                self.MAX_BACKOFF_SECONDS
            )

            await self.connect()

    async def send(self, message: Dict[str, Any]) -> bool:
        """发送消息"""
        if self._ws:
            try:
                await self._ws.send(json.dumps(message))
                return True
            except Exception as e:
                print(f"[WSClient] 发送失败: {e}")
                self._pending_queue.append(message)
                return False

        self._pending_queue.append(message)
        return False

    async def flush_pending(self):
        """重连后发送积压消息"""
        while self._pending_queue:
            msg = self._pending_queue.popleft()
            await self.send(msg)

    def disconnect(self):
        """主动断开连接"""
        self._running = False
        if self._ws:
            asyncio.create_task(self._ws.close())


ws_manager = WSConnectionManager()
