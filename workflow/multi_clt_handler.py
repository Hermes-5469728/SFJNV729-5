"""workflow/multi_clt_handler.py
多 CLT 并发处理器
支持多个终端同时接入，session 隔离，并发控制，队列缓冲。
"""

import asyncio, uuid, json
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any

from .stream_router import route


@dataclass
class CLTRequest:
    """单个 CLT 请求"""
    clt_id: str
    query: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    result: dict | None = None
    status: str = "queued"


class MultiCLTHandler:
    """多 CLT 并发处理器"""

    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.queue: asyncio.Queue = asyncio.Queue()
        self.active: dict[str, CLTRequest] = {}
        self.semaphore = asyncio.Semaphore(max_workers)

    async def submit(self, clt_id: str, query: str) -> str:
        """提交请求，返回 session_id"""
        req = CLTRequest(clt_id=clt_id, query=query)
        await self.queue.put(req)
        self.active[req.session_id] = req
        return req.session_id

    async def _worker(self):
        """后台工作协程"""
        while True:
            req: CLTRequest = await self.queue.get()
            async with self.semaphore:
                req.status = "processing"
                try:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, route, req.query, req.session_id)
                    req.result = result
                    req.status = "done"
                except Exception as e:
                    req.result = {"error": str(e)}
                    req.status = "failed"

    async def start(self):
        """启动工作协程"""
        self._tasks = [asyncio.create_task(self._worker()) for _ in range(self.max_workers)]

    async def stop(self):
        for t in self._tasks:
            t.cancel()

    def get_result(self, session_id: str) -> dict | None:
        req = self.active.get(session_id)
        if req and req.result:
            return {"status": req.status, "session_id": session_id, "result": req.result}
        return None

    def status_summary(self) -> dict:
        total = len(self.active)
        done = sum(1 for r in self.active.values() if r.status == "done")
        failed = sum(1 for r in self.active.values() if r.status == "failed")
        return {"total": total, "done": done, "failed": failed, "active": total - done - failed}
