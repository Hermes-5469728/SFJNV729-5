"""
SDK Layer - Dual Track Router (双轨路由颗粒)
OpenCode Hooks:
  /sdk route-info                    # 查看路由配置
  /sdk add-route <path> <track>      # 添加路由
  /sdk route-track <path>            # 获取路由轨道类型
  /sdk dispatch <track> <path> <data> # 分发请求
"""

from loguru import logger
from typing import Dict, Any, Callable, Optional, List
from enum import Enum
from fastapi import HTTPException

class TrackType(Enum):
    """双轨路由类型"""
    PERSONAL = "personal"    # 保命模式
    MEDICAL = "medical"      # 救人模式

class RouteHandler:
    """路由处理器"""
    def __init__(self, handler: Callable, track: TrackType, permissions: List[str] = None):
        self.handler = handler
        self.track = track
        self.permissions = permissions or []

class DualTrackRouter:
    """
    双轨路由系统
    颗粒化模块：独立的路由分发逻辑
    
    OpenCode TUI 交互:
    - /sdk route-info -> get_all_routes()
    - /sdk add-route <path> <track> -> add_route()
    - /sdk route-track <path> -> get_track_type()
    - /sdk dispatch <track> <path> <data> -> dispatch()
    """
    
    def __init__(self):
        self.routes: Dict[str, RouteHandler] = {}
        self.track_middlewares = {
            TrackType.PERSONAL: [],
            TrackType.MEDICAL: []
        }
        logger.info("DualTrackRouter initialized")
    
    def add_route(self, path: str, handler: Callable, track: TrackType, permissions: List[str] = None):
        """
        添加路由
        OpenCode Hook: /sdk add-route <path> <track>
        """
        self.routes[path] = RouteHandler(handler, track, permissions)
        logger.info(f"Added route: {path} -> {track.value}")
    
    def add_middleware(self, track: TrackType, middleware: Callable):
        """添加轨道专属中间件"""
        self.track_middlewares[track].append(middleware)
        logger.info(f"Added middleware for {track.value} track")
    
    async def dispatch(self, path: str, request: Dict[str, Any], track: TrackType) -> Any:
        """
        分发请求到对应轨道
        OpenCode Hook: /sdk dispatch <track> <path> <data>
        """
        route_handler = self.routes.get(path)
        if not route_handler:
            logger.error(f"Route not found: {path}")
            raise HTTPException(status_code=404, detail="Route not found")
        
        if route_handler.track != track:
            logger.warning(f"Track mismatch: route requires {route_handler.track.value}, got {track.value}")
        
        for middleware in self.track_middlewares[track]:
            try:
                result = middleware(request, track)
                if result is not None:
                    return result
            except Exception as e:
                logger.error(f"Middleware failed: {e}")
                raise HTTPException(status_code=500, detail="Middleware error")
        
        if route_handler.permissions:
            user_permissions = request.get("user_permissions", [])
            for perm in route_handler.permissions:
                if perm not in user_permissions:
                    logger.warning(f"Permission denied: {perm}")
                    raise HTTPException(status_code=403, detail=f"Permission denied: {perm}")
        
        try:
            result = route_handler.handler(request)
            return result
        except Exception as e:
            logger.error(f"Handler failed: {e}")
            raise HTTPException(status_code=500, detail="Handler error")
    
    def get_routes_by_track(self, track: TrackType) -> List[str]:
        """获取指定轨道的所有路由"""
        return [path for path, handler in self.routes.items() if handler.track == track]
    
    def get_track_type(self, path: str) -> Optional[TrackType]:
        """获取路由所属轨道"""
        handler = self.routes.get(path)
        return handler.track if handler else None
    
    def get_all_routes(self) -> List[Dict[str, Any]]:
        """
        获取所有路由信息
        OpenCode Hook: /sdk route-info
        """
        return [
            {
                "path": path,
                "track": handler.track.value,
                "permissions": handler.permissions
            }
            for path, handler in self.routes.items()
        ]
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态（OpenCode监控接口）"""
        return {
            "total_routes": len(self.routes),
            "personal_routes": len(self.get_routes_by_track(TrackType.PERSONAL)),
            "medical_routes": len(self.get_routes_by_track(TrackType.MEDICAL)),
            "routes": self.get_all_routes()
        }