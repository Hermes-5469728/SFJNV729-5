"""AC Platform Dependencies - 依赖注入导出"""
from fastapi import Depends
from sqlalchemy.orm import Session
from src.core.database import get_db

__all__ = ["get_db"]
