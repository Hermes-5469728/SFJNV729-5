"""AC Platform Tool Registry - 工具注册中心 + 双轨路由"""
from enum import Enum
from typing import Dict, List, Callable, Any
from datetime import datetime

class RouteMode(Enum):
    DETERMINISTIC = "deterministic"
    HEURISTIC = "heuristic"

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, handler: Callable, mode: RouteMode, module: str, description: str):
        self._tools[name] = {
            "handler": handler,
            "mode": mode,
            "module": module,
            "description": description,
            "registered_at": datetime.now().isoformat(),
        }

    def get_tool(self, name: str) -> Dict[str, Any]:
        return self._tools.get(name)

    def list_tools(self, module: str = None) -> List[Dict[str, Any]]:
        if module:
            return [t for t in self._tools.values() if t["module"] == module]
        return list(self._tools.values())

registry = ToolRegistry()
