"""
SDK Layer - Plugin Manager (插件管理器颗粒)
OpenCode Hooks:
  /sdk list-plugins          # 列出所有插件
  /sdk load-plugin <name>    # 加载指定插件
  /sdk unload-plugin <name>  # 卸载指定插件
  /sdk execute-plugin <id> <request>  # 执行插件
"""

import importlib
import os
import sys
from loguru import logger
from typing import Dict, Any, Type, Optional, List
from abc import ABC, abstractmethod

class IPlugin(ABC):
    """插件接口定义（颗粒化标准接口）"""

    @abstractmethod
    def get_id(self) -> str:
        """获取插件ID"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """获取插件名称"""
        pass

    @abstractmethod
    def get_version(self) -> str:
        """获取插件版本"""
        pass

    @abstractmethod
    def initialize(self, context: Dict[str, Any]) -> bool:
        """初始化插件"""
        pass

    @abstractmethod
    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """执行插件逻辑"""
        pass

    @abstractmethod
    def shutdown(self):
        """关闭插件"""
        pass

class PluginInfo:
    """插件信息"""
    def __init__(self, plugin_id: str, name: str, version: str, status: str):
        self.plugin_id = plugin_id
        self.name = name
        self.version = version
        self.status = status

class PluginManager:
    """
    自定义插件管理器
    颗粒化模块：独立的插件生命周期管理

    OpenCode TUI 交互:
    - /sdk list-plugins     -> list_plugins()
    - /sdk load-plugin <id> -> load_plugin(id)
    - /sdk unload-plugin <id> -> unload_plugin(id)
    - /sdk execute-plugin <id> <request> -> execute_plugin(id, request)
    """

    def __init__(self, plugin_dir: str = None):
        self.plugin_dir = plugin_dir or os.path.join(os.path.dirname(__file__), '../plugins')
        self.plugins: Dict[str, IPlugin] = {}
        self.plugin_info: Dict[str, PluginInfo] = {}
        self.context: Dict[str, Any] = {}
        os.makedirs(self.plugin_dir, exist_ok=True)

        if self.plugin_dir not in sys.path:
            sys.path.insert(0, self.plugin_dir)

        logger.info(f"PluginManager initialized, plugin_dir: {self.plugin_dir}")

    def set_context(self, context: Dict[str, Any]):
        """设置插件上下文（注入依赖）"""
        self.context = context
        logger.debug(f"Plugin context updated: {list(context.keys())}")

    def load_plugin(self, plugin_module: str) -> bool:
        """加载插件"""
        try:
            module = importlib.import_module(plugin_module)

            plugin_class = None
            for name, obj in module.__dict__.items():
                if isinstance(obj, type) and issubclass(obj, IPlugin) and obj != IPlugin:
                    plugin_class = obj
                    break

            if not plugin_class:
                logger.error(f"No IPlugin implementation found in {plugin_module}")
                return False

            plugin = plugin_class()
            plugin_id = plugin.get_id()

            self.plugin_info[plugin_id] = PluginInfo(
                plugin_id=plugin_id,
                name=plugin.get_name(),
                version=plugin.get_version(),
                status="loaded"
            )

            self.plugins[plugin_id] = plugin
            logger.info(f"Loaded plugin: {plugin_id} ({plugin.get_name()})")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_module}: {e}")
            return False

    def initialize_plugin(self, plugin_id: str) -> bool:
        """初始化插件"""
        try:
            plugin = self.plugins.get(plugin_id)
            if not plugin:
                logger.error(f"Plugin {plugin_id} not found")
                return False

            if plugin.initialize(self.context):
                self.plugin_info[plugin_id].status = "initialized"
                logger.info(f"Initialized plugin: {plugin_id}")
                return True
            else:
                self.plugin_info[plugin_id].status = "error"
                return False

        except Exception as e:
            logger.error(f"Failed to initialize plugin {plugin_id}: {e}")
            if plugin_id in self.plugin_info:
                self.plugin_info[plugin_id].status = "error"
            return False

    def execute_plugin(self, plugin_id: str, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """执行插件"""
        try:
            plugin = self.plugins.get(plugin_id)
            if not plugin:
                logger.error(f"Plugin {plugin_id} not found")
                return None

            info = self.plugin_info.get(plugin_id)
            if info and info.status != "initialized":
                logger.warning(f"Plugin {plugin_id} not initialized, initializing...")
                self.initialize_plugin(plugin_id)

            result = plugin.execute(request)
            logger.info(f"Executed plugin: {plugin_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to execute plugin {plugin_id}: {e}")
            return None

    def unload_plugin(self, plugin_id: str):
        """卸载插件"""
        try:
            plugin = self.plugins.get(plugin_id)
            if plugin:
                plugin.shutdown()
                del self.plugins[plugin_id]
                del self.plugin_info[plugin_id]
                logger.info(f"Unloaded plugin: {plugin_id}")
        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_id}: {e}")

    def list_plugins(self) -> List[PluginInfo]:
        """获取所有插件信息"""
        return list(self.plugin_info.values())

    def get_plugin(self, plugin_id: str) -> Optional[IPlugin]:
        """获取插件实例"""
        return self.plugins.get(plugin_id)

    def get_status(self) -> Dict[str, Any]:
        """获取状态（OpenCode监控接口）"""
        return {
            "loaded_count": len(self.plugins),
            "plugins": [
                {
                    "id": p.plugin_id,
                    "name": p.name,
                    "status": p.status
                }
                for p in self.plugin_info.values()
            ]
        }