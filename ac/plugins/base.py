"""AC Plugin Protocol — 所有外部项目接入的标准接口"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class PluginStatus(Enum):
    ACTIVE = "active"
    STANDBY = "standby"
    OFF = "off"

@dataclass
class ACPlugin:
    name: str
    url: str = ""
    port: int = 0
    category: str = ""
    status: PluginStatus = PluginStatus.STANDBY
    layer: str = ""
    health_check_url: str = ""

    def __post_init__(self):
        if self.port and not self.health_check_url:
            self.health_check_url = f"http://localhost:{self.port}/health"

    def mount_cmd(self) -> str:
        return f"# {self.name}: docker/pip/手动启动 | 端口 {self.port} | {self.category}"

    def unmount_cmd(self) -> str:
        return f"# {self.name}: docker stop / pip uninstall | 端口 {self.port}"
