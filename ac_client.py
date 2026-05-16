"""
AC Client - Trae 侧的 AC 通信客户端

使用方式：
    from ac_client import ACClient

    client = ACClient(
        ai_id="trae_editor",
        name="Trae Editor",
        base_url="http://localhost:8000"
    )

    # 发送消息给对话端
    client.send_message(
        target_ai="hermes_conversation",
        action="code_generated",
        payload={"file": "main.py", "status": "completed"}
    )

    # 监听消息
    client.on_message(lambda msg: print(f"收到: {msg}"))

    # 启动监听
    client.start()
"""

import json
import threading
import time
from typing import Any, Callable, Dict, List, Optional

import requests
import websocket


class ACClient:
    """
    AC 通信客户端

    功能：
    1. 自动注册到 AI Registry
    2. 点对点消息发送
    3. WebSocket 实时消息接收
    4. 心跳保活
    """

    def __init__(
        self,
        ai_id: str,
        name: str,
        base_url: str = "http://localhost:8000",
        ws_url: str = None
    ):
        self.ai_id = ai_id
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.ws_url = (ws_url or base_url.replace("http", "ws")) + f"/ws/{ai_id}"

        self._ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._running = False
        self._message_handlers: List[Callable] = []
        self._connect_handlers: List[Callable] = []
        self._disconnect_handlers: List[Callable] = []

        self._last_heartbeat = time.time()

        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def register(self, agent_type: str = "trae", capabilities: List[str] = None) -> bool:
        """注册到 AI Registry"""
        if capabilities is None:
            capabilities = ["code_generation", "code_review", "file_watch"]

        response = self._session.post(
            f"{self.base_url}/ai/register",
            json={
                "ai_id": self.ai_id,
                "name": self.name,
                "agent_type": agent_type,
                "capabilities": capabilities,
                "contract": "read_only"
            }
        )

        if response.status_code == 200:
            print(f"[ACClient] {self.ai_id} 注册成功")
            return True
        elif response.status_code == 409:
            print(f"[ACClient] {self.ai_id} 已存在，跳过注册")
            return True
        else:
            print(f"[ACClient] 注册失败: {response.text}")
            return False

    def send_message(
        self,
        target_ai: str,
        action: str,
        payload: Dict[str, Any],
        orchestration_id: Optional[str] = None
    ) -> Optional[str]:
        """发送消息给指定 AI"""
        response = self._session.post(
            f"{self.base_url}/ai/send",
            json={
                "source_ai": self.ai_id,
                "target_ai": target_ai,
                "action": action,
                "payload": payload,
                "orchestration_id": orchestration_id
            }
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("message_id")
        else:
            print(f"[ACClient] 发送失败: {response.text}")
            return None

    def broadcast(
        self,
        action: str,
        payload: Dict[str, Any],
        orchestration_id: Optional[str] = None
    ) -> Optional[str]:
        """广播消息"""
        response = self._session.post(
            f"{self.base_url}/ai/broadcast",
            json={
                "source_ai": self.ai_id,
                "action": action,
                "payload": payload,
                "orchestration_id": orchestration_id
            }
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("message_id")
        else:
            print(f"[ACClient] 广播失败: {response.text}")
            return None

    def on_message(self, handler: Callable):
        """注册消息处理函数"""
        self._message_handlers.append(handler)

    def on_connect(self, handler: Callable):
        """注册连接成功处理函数"""
        self._connect_handlers.append(handler)

    def on_disconnect(self, handler: Callable):
        """注册断开连接处理函数"""
        self._disconnect_handlers.append(handler)

    def _on_ws_message(self, ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "pong":
                self._last_heartbeat = time.time()
                return

            for handler in self._message_handlers:
                try:
                    handler(data)
                except Exception as e:
                    print(f"[ACClient] 消息处理错误: {e}")

        except json.JSONDecodeError:
            print(f"[ACClient] 非 JSON 消息: {message}")

    def _on_ws_open(self, ws):
        print(f"[ACClient] WebSocket 已连接: {self.ws_url}")
        for handler in self._connect_handlers:
            try:
                handler()
            except Exception as e:
                print(f"[ACClient] 连接处理错误: {e}")

        self._send_ping()

    def _on_ws_close(self, ws, close_status_code, close_msg):
        print(f"[ACClient] WebSocket 断开: {close_status_code} {close_msg}")
        for handler in self._disconnect_handlers:
            try:
                handler()
            except Exception as e:
                print(f"[ACClient] 断开处理错误: {e}")

    def _on_ws_error(self, ws, error):
        print(f"[ACClient] WebSocket 错误: {error}")

    def _send_ping(self):
        """发送心跳"""
        try:
            self._ws.send(json.dumps({"type": "ping"}))
            threading.Timer(30, self._send_ping).start()
        except Exception as e:
            print(f"[ACClient] 心跳失败: {e}")

    def _ws_worker(self):
        """WebSocket 工作线程"""
        while self._running:
            try:
                self._ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_message=self._on_ws_message,
                    on_open=self._on_ws_open,
                    on_close=self._on_ws_close,
                    on_error=self._on_ws_error
                )

                self._ws.run_forever(ping_interval=30, ping_timeout=10)

            except Exception as e:
                print(f"[ACClient] WebSocket 异常: {e}")

            if self._running:
                print("[ACClient] 5秒后重连...")
                time.sleep(5)

    def start(self, auto_register: bool = True):
        """启动客户端"""
        if auto_register:
            self.register()

        self._running = True
        self._ws_thread = threading.Thread(target=self._ws_worker, daemon=True)
        self._ws_thread.start()

        print(f"[ACClient] {self.ai_id} 已启动")

    def stop(self):
        """停止客户端"""
        self._running = False
        if self._ws:
            self._ws.close()
        print(f"[ACClient] {self.ai_id} 已停止")

    def get_agents(self) -> List[Dict]:
        """获取所有注册的 AI"""
        response = self._session.get(f"{self.base_url}/ai/registry")
        if response.status_code == 200:
            return response.json().get("data", {}).get("agents", [])
        return []

    def get_audit(self, orchestration_id: Optional[str] = None) -> List[Dict]:
        """获取审计日志"""
        params = {}
        if orchestration_id:
            params["orchestration_id"] = orchestration_id

        response = self._session.get(f"{self.base_url}/ai/audit", params=params)
        if response.status_code == 200:
            return response.json().get("data", {}).get("entries", [])
        return []


if __name__ == "__main__":
    print("=" * 60)
    print("  AC Client 测试")
    print("=" * 60)

    client = ACClient(
        ai_id="trae_editor",
        name="Trae Editor",
        base_url="http://localhost:8000"
    )

    client.on_message(lambda msg: print(f"[收到消息] {msg}"))
    client.on_connect(lambda: print("[事件] 已连接"))
    client.on_disconnect(lambda: print("[事件] 已断开"))

    client.start()

    time.sleep(2)

    print("\n当前注册的 AI：")
    for agent in client.get_agents():
        print(f"  {agent['ai_id']} ({agent['agent_type']}) - {agent['status']}")

    print("\n发送测试消息...")
    msg_id = client.send_message(
        target_ai="hermes_conversation",
        action="test",
        payload={"content": "Hello from Trae!"}
    )
    print(f"消息ID: {msg_id}")

    time.sleep(2)

    print("\n审计日志：")
    for entry in client.get_audit():
        print(f"  {entry['source_ai']} -> {entry['target_ai']}: {entry['action']}")

    print("\n保持运行中... (Ctrl+C 退出)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client.stop()
