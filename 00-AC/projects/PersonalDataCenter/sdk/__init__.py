"""
OpenCode TUI Hooks:
/sdk list-plugins          # 列出所有插件
/sdk load-plugin <name>    # 加载指定插件
/sdk unload-plugin <name>  # 卸载指定插件
/sdk route-info            # 查看路由配置
/sdk auth-check <sub> <obj> <act>  # 权限检查
/sdk genesis-status        # 查看创世状态
/sdk claim-genesis         # 申请创世管理员身份
/sdk lock-system           # 手动锁定系统
/sdk backup-sdk            # 备份SDK核心数据
/sdk restore-sdk           # 恢复SDK初始数据
/sdk regenerate-mirror     # 一键复原镜像文件
"""

from .plugin_manager import PluginManager
from .dual_track_router import DualTrackRouter, TrackType
from .auth_manager import AuthManager
from .vector_db import VectorDB
from .genesis_manager import GenesisManager, get_genesis_manager

__all__ = ["PluginManager", "DualTrackRouter", "TrackType", "AuthManager", "VectorDB", 
           "GenesisManager", "get_genesis_manager"]