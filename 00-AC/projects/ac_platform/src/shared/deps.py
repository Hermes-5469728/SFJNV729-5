"""暴露给 N 模块的通用依赖 · src/shared/deps.py"""
from src.core.database import get_db, Session

__all__ = ["get_db", "Session"]
