"""AC Platform API Entry Point - 1+N 双轨架构总入口"""
__version__ = "1.0.0"

import os, sys, json
from pathlib import Path

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.core.config import settings, AC_CORE_MODE
from src.core.database import init_db, engine, Base
from src.core.gaia_defense import GaiaDefensePipeline
from src.modules.medical.models import MedDrug, MedInteraction, MedGuideline, MedSafetyAlert, MedUserProfile

gaia_defense = GaiaDefensePipeline()

app = FastAPI(
    title="AC Platform API",
    description="1+N Dual-Track Architecture · Core + Medical Module",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/")
def root():
    return {
        "name": "AC Platform",
        "version": __version__,
        "mode": "AC_CORE" if AC_CORE_MODE else "STANDALONE",
        "1+N": {
            "core": True,
            "modules": ["medical"],
            "dual_track": ["deterministic", "heuristic"],
        }
    }

@app.get("/health")
def health():
    return {"status": "ok", "db_connected": True}

@app.post("/defense/process")
def defense_process(request: Request):
    body = request.json()
    user_input = body.get("input", "")
    result = gaia_defense.process(user_input)
    return result

@app.get("/defense/stats")
def defense_stats():
    return gaia_defense.stats()

@app.get("/api/modules")
def list_modules():
    return {
        "modules": [
            {"name": "medical", "enabled": True, "prefix": "/medical"},
        ],
        "core_enabled": AC_CORE_MODE,
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api_main:app", host="0.0.0.0", port=port, reload=False)
