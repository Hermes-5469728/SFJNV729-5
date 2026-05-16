"""
统一健康检查总线 - 替代 ac_heartbeat

问题：ac_heartbeat 只记录 CLI 调用，不记录模块间通信
解决：
- 每个独立进程（Server、SubAgent、Worker）定期发布 HEARTBEAT 事件
- 监控服务订阅这些事件，超时告警
- CI 状态通过 GitHub API/webhook 写入 AC Bus
- 统一展示所有组件的健康状态

架构：
  ┌─────────────────────────────────────────────────────┐
  │              HealthMonitorService                   │
  │                    │                                │
  │            AC Bus (HEARTBEAT 事件)                  │
  │                    │                                │
  ├─────────────────────────────────────────────────────┤
  │  Server  │  SubAgent  │  Worker  │  CI Runner  │    │
  └─────────────────────────────────────────────────────┘
"""

import asyncio
import json
import sqlite3
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    AC_SERVER = "ac_server"
    SUBAGENT = "subagent"
    WORKER = "worker"
    CI_RUNNER = "ci_runner"
    GITHUB_ACTION = "github_action"
    CLIENT = "client"
    GATEWAY = "gateway"
    DATABASE = "database"


class ComponentStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HeartbeatEvent(BaseModel):
    component_id: str = Field(..., description="组件唯一ID")
    component_type: ComponentType = Field(..., description="组件类型")
    status: ComponentStatus = Field(..., description="组件状态")
    timestamp: str = Field(..., description="时间戳 ISO8601")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    version: Optional[str] = Field(default=None, description="版本")


class ComponentInfo(BaseModel):
    component_id: str
    component_type: ComponentType
    last_heartbeat: str
    status: ComponentStatus
    metadata: Dict[str, Any]
    version: Optional[str]
    uptime_seconds: float = 0.0
    avg_response_ms: float = 0.0


class CIStatusEvent(BaseModel):
    run_id: str
    status: str
    workflow_name: str
    commit_sha: str
    branch: str
    timestamp: str
    metadata: Dict[str, Any]


class HealthMonitor:
    """
    健康监控服务 - 订阅 AC Bus 的 HEARTBEAT 事件
    """

    def __init__(self, db_path: str = "health_monitor.db", timeout_seconds: float = 60.0):
        self.db_path = db_path
        self.timeout_seconds = timeout_seconds
        self._components: Dict[str, ComponentInfo] = {}
        self._alerts: List[Dict[str, Any]] = []
        self._stop_event = asyncio.Event()
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS heartbeats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_id TEXT NOT NULL,
                    component_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    version TEXT,
                    UNIQUE(component_id, timestamp)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_id TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS ci_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    workflow_name TEXT NOT NULL,
                    commit_sha TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_heartbeats_component
                ON heartbeats(component_id)
            """)

    def record_heartbeat(self, event: HeartbeatEvent):
        """记录心跳事件"""
        with sqlite3.connect(self.db_path) as conn:
            metadata_json = json.dumps(event.metadata)
            conn.execute("""
                INSERT OR REPLACE INTO heartbeats
                (component_id, component_type, status, timestamp, metadata, version)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event.component_id,
                event.component_type.value,
                event.status.value,
                event.timestamp,
                metadata_json,
                event.version
            ))

        info = ComponentInfo(
            component_id=event.component_id,
            component_type=event.component_type,
            last_heartbeat=event.timestamp,
            status=event.status,
            metadata=event.metadata,
            version=event.version
        )

        self._components[event.component_id] = info

        if event.status == ComponentStatus.UNHEALTHY:
            self._trigger_alert(
                component_id=event.component_id,
                alert_type="status_unhealthy",
                severity="critical",
                message=f"组件 {event.component_id} 状态变为 UNHEALTHY"
            )

    def record_ci_status(self, event: CIStatusEvent):
        """记录 CI 状态"""
        with sqlite3.connect(self.db_path) as conn:
            metadata_json = json.dumps(event.metadata)
            conn.execute("""
                INSERT OR REPLACE INTO ci_status
                (run_id, status, workflow_name, commit_sha, branch, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event.run_id,
                event.status,
                event.workflow_name,
                event.commit_sha,
                event.branch,
                event.timestamp,
                metadata_json
            ))

        if event.status == "failure" or event.status == "cancelled":
            self._trigger_alert(
                component_id=f"ci_{event.run_id}",
                alert_type="ci_failure",
                severity="high",
                message=f"CI Run {event.workflow_name} 状态: {event.status}"
            )

    def _trigger_alert(
        self,
        component_id: str,
        alert_type: str,
        severity: str,
        message: str
    ):
        """触发告警"""
        alert = {
            "component_id": component_id,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

        self._alerts.append(alert)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO alerts
                (component_id, alert_type, severity, message, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                alert["component_id"],
                alert["alert_type"],
                alert["severity"],
                alert["message"],
                alert["timestamp"]
            ))

        print(f"[ALERT] {severity.upper()}: {message}")

    def get_all_components(self) -> List[ComponentInfo]:
        """获取所有组件状态"""
        now = datetime.now()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    component_id,
                    component_type,
                    status,
                    timestamp,
                    metadata,
                    version
                FROM (
                    SELECT
                        component_id,
                        component_type,
                        status,
                        timestamp,
                        metadata,
                        version,
                        ROW_NUMBER() OVER (
                            PARTITION BY component_id
                            ORDER BY timestamp DESC
                        ) AS rn
                    FROM heartbeats
                )
                WHERE rn = 1
            """)

            components = []

            for row in cursor:
                comp_id = row[0]
                comp_type_str = row[1]
                status_str = row[2]
                timestamp_str = row[3]
                metadata_json = row[4]
                version = row[5]

                comp_type = ComponentType(comp_type_str)
                status = ComponentStatus(status_str)
                metadata = json.loads(metadata_json) if metadata_json else {}

                last_time = datetime.fromisoformat(timestamp_str)
                elapsed = (now - last_time).total_seconds()

                if elapsed > self.timeout_seconds and status == ComponentStatus.HEALTHY:
                    status = ComponentStatus.UNKNOWN

                info = ComponentInfo(
                    component_id=comp_id,
                    component_type=comp_type,
                    last_heartbeat=timestamp_str,
                    status=status,
                    metadata=metadata,
                    version=version,
                    uptime_seconds=elapsed
                )

                components.append(info)

            return components

    def get_unhealthy_components(self) -> List[ComponentInfo]:
        """获取不健康的组件"""
        components = self.get_all_components()
        return [
            c for c in components
            if c.status in [ComponentStatus.UNHEALTHY, ComponentStatus.UNKNOWN]
        ]

    def get_alerts(self, limit: int = 50, severity: Optional[str] = None) -> List[Dict]:
        """获取告警历史"""
        query = "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?"
        params = (limit,)

        if severity:
            query = "SELECT * FROM alerts WHERE severity = ? ORDER BY timestamp DESC LIMIT ?"
            params = (severity, limit)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return [
                {
                    "id": row[0],
                    "component_id": row[1],
                    "alert_type": row[2],
                    "severity": row[3],
                    "message": row[4],
                    "timestamp": row[5]
                }
                for row in cursor
            ]

    def get_ci_status(self, limit: int = 20, branch: Optional[str] = None) -> List[Dict]:
        """获取 CI 状态"""
        query = "SELECT * FROM ci_status ORDER BY timestamp DESC LIMIT ?"
        params = (limit,)

        if branch:
            query = "SELECT * FROM ci_status WHERE branch = ? ORDER BY timestamp DESC LIMIT ?"
            params = (branch, limit)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return [
                {
                    "id": row[0],
                    "run_id": row[1],
                    "status": row[2],
                    "workflow_name": row[3],
                    "commit_sha": row[4],
                    "branch": row[5],
                    "timestamp": row[6],
                    "metadata": json.loads(row[7]) if row[7] else {}
                }
                for row in cursor
            ]

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统整体状态"""
        components = self.get_all_components()
        unhealthy = self.get_unhealthy_components()

        total = len(components)
        healthy = sum(1 for c in components if c.status == ComponentStatus.HEALTHY)
        degraded = sum(1 for c in components if c.status == ComponentStatus.DEGRADED)
        unhealthy_count = len(unhealthy)

        overall_status = ComponentStatus.HEALTHY
        if unhealthy_count > 0:
            overall_status = ComponentStatus.UNHEALTHY
        elif degraded > 0:
            overall_status = ComponentStatus.DEGRADED

        return {
            "overall_status": overall_status.value,
            "components": {
                "total": total,
                "healthy": healthy,
                "degraded": degraded,
                "unhealthy": unhealthy_count,
                "unknown": sum(1 for c in components if c.status == ComponentStatus.UNKNOWN)
            },
            "by_type": {
                ct.value: sum(1 for c in components if c.component_type == ct)
                for ct in ComponentType
            },
            "alerts_count": len(self.get_alerts(limit=1000)),
            "timestamp": datetime.now().isoformat()
        }


class HeartbeatPublisher:
    """
    心跳发布器 - 各组件定期调用此发布 HEARTBEAT 事件
    """

    def __init__(
        self,
        component_id: str,
        component_type: ComponentType,
        monitor: HealthMonitor,
        interval_seconds: float = 10.0
    ):
        self.component_id = component_id
        self.component_type = component_type
        self.monitor = monitor
        self.interval_seconds = interval_seconds
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._start_time = time.time()

    def start(self):
        """启动心跳发布"""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._heartbeat_loop())
        print(f"[HeartbeatPublisher] 启动: {self.component_type.value}/{self.component_id}")

    def stop(self):
        """停止心跳发布"""
        self._stop_event.set()
        if self._task:
            self._task.cancel()
        print(f"[HeartbeatPublisher] 停止: {self.component_type.value}/{self.component_id}")

    async def _heartbeat_loop(self):
        """心跳循环"""
        while not self._stop_event.is_set():
            try:
                await self._publish_heartbeat()
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[HeartbeatPublisher] 错误: {e}")
                await asyncio.sleep(1.0)

    async def _publish_heartbeat(self):
        """发布心跳"""
        event = HeartbeatEvent(
            component_id=self.component_id,
            component_type=self.component_type,
            status=ComponentStatus.HEALTHY,
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            metadata={
                "uptime_seconds": time.time() - self._start_time,
                "timestamp": datetime.now().isoformat()
            }
        )

        self.monitor.record_heartbeat(event)

    def publish_status_change(self, status: ComponentStatus, metadata: Optional[Dict] = None):
        """发布状态变化"""
        event = HeartbeatEvent(
            component_id=self.component_id,
            component_type=self.component_type,
            status=status,
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            metadata=metadata or {}
        )

        self.monitor.record_heartbeat(event)


def create_heartbeat_publisher(
    component_type: ComponentType,
    component_id: Optional[str] = None,
    monitor: Optional[HealthMonitor] = None
) -> HeartbeatPublisher:
    """
    创建心跳发布器（便捷函数）

    各组件调用此函数获取发布器，定期发送心跳
    """
    if not component_id:
        component_id = f"{component_type.value}_{uuid.uuid4().hex[:8]}"

    if not monitor:
        monitor = HealthMonitor()

    return HeartbeatPublisher(
        component_id=component_id,
        component_type=component_type,
        monitor=monitor
    )


if __name__ == "__main__":
    monitor = HealthMonitor()

    print("=" * 60)
    print("  统一健康检查总线")
    print("=" * 60)

    server_publisher = create_heartbeat_publisher(ComponentType.AC_SERVER, "ac_server_01", monitor)
    server_publisher.start()

    import time
    try:
        while True:
            status = monitor.get_system_status()
            print("\n[System Status]")
            print(f"  Overall: {status['overall_status']}")
            print(f"  Components: {status['components']}")

            components = monitor.get_all_components()
            for c in components:
                print(f"  {c.component_type.value}/{c.component_id} = {c.status.value}")

            time.sleep(5)

    except KeyboardInterrupt:
        server_publisher.stop()

