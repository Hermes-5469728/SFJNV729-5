"""
SDK Layer - FastAPI Application (API网关颗粒)
OpenCode Hook: /sdk api-status
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import os
import json

from .auth_manager import AuthManager
from .vector_db import VectorDB
from .plugin_manager import PluginManager
from .dual_track_router import DualTrackRouter, TrackType

auth_manager = AuthManager()
vector_db = VectorDB()
plugin_manager = PluginManager()
dual_track_router = DualTrackRouter()

app = FastAPI(
    title="Personal Data Center API",
    description="个人数据处理中心核心API - OpenCode TUI Compatible",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_auth_manager():
    return auth_manager

def get_vector_db():
    return vector_db

def get_plugin_manager():
    return plugin_manager

def get_dual_track_router():
    return dual_track_router

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "Personal Data Center",
        "components": {
            "auth": auth_manager.get_status(),
            "vector_db": vector_db.get_status(),
            "plugins": plugin_manager.get_status(),
            "router": dual_track_router.get_status()
        }
    }

@app.get("/sdk/status")
async def sdk_status():
    """OpenCode Hook: /sdk api-status"""
    return {
        "auth": auth_manager.get_status(),
        "vector_db": vector_db.get_status(),
        "plugins": plugin_manager.get_status(),
        "router": dual_track_router.get_status()
    }

@app.post("/auth/enforce")
async def enforce_auth(
    subject: str, 
    object: str, 
    action: str,
    auth: AuthManager = Depends(get_auth_manager)
):
    """权限检查"""
    result = auth.enforce(subject, object, action)
    return {"allowed": result}

@app.post("/vector/search")
async def vector_search(
    table_name: str,
    query_vector: list,
    top_k: int = 5,
    db: VectorDB = Depends(get_vector_db)
):
    """向量检索"""
    import numpy as np
    query_vec = np.array(query_vector, dtype=np.float32)
    results = db.search(table_name, query_vec, top_k)
    return {"results": results}

@app.get("/plugins/list")
async def list_plugins(pm: PluginManager = Depends(get_plugin_manager)):
    """列出所有插件"""
    plugins = pm.list_plugins()
    return [{"id": p.plugin_id, "name": p.name, "version": p.version, "status": p.status} for p in plugins]

@app.post("/plugins/load")
async def load_plugin(plugin_module: str, pm: PluginManager = Depends(get_plugin_manager)):
    """加载插件"""
    result = pm.load_plugin(plugin_module)
    return {"success": result}

@app.post("/plugins/execute")
async def execute_plugin(
    plugin_id: str,
    request_data: dict = {},
    pm: PluginManager = Depends(get_plugin_manager)
):
    """执行插件"""
    result = pm.execute_plugin(plugin_id, request_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Plugin not found or execution failed")
    return result

@app.get("/routes/list")
async def list_routes(router: DualTrackRouter = Depends(get_dual_track_router)):
    """列出所有路由"""
    return router.get_all_routes()

@app.post("/track/{track_type}/route/{path}")
async def track_route(
    track_type: str,
    path: str,
    request: Request,
    router: DualTrackRouter = Depends(get_dual_track_router)
):
    """双轨路由分发"""
    try:
        track = TrackType(track_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid track type: {track_type}")
    
    request_data = await request.json()
    result = await router.dispatch(path, request_data, track)
    return result

def register_routes():
    """注册示例路由"""
    def personal_handler(request):
        return {"track": "personal", "data": request}
    
    def medical_handler(request):
        return {"track": "medical", "data": request}
    
    dual_track_router.add_route("/api/personal/query", personal_handler, TrackType.PERSONAL)
    dual_track_router.add_route("/api/medical/query", medical_handler, TrackType.MEDICAL)

register_routes()

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Personal Data Center API...")
    uvicorn.run(app, host="127.0.0.1", port=8000)