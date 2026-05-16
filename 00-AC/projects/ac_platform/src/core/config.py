"""全局配置 · src/core/config.py"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ─── 应用 ───
    APP_NAME: str = "AC Platform"
    DEBUG: bool = True

    # ─── 数据库 ───
    DATABASE_URL: str = "postgresql://ac_admin:ac_platform_2026@localhost:5432/ac_platform"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # ─── 安全 ───
    SECRET_KEY: str = "ac-platform-secret-key-change-in-production"
    TOKEN_EXPIRE_HOURS: int = 24

    # ─── CORS ───
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8500", "http://localhost:8501"]

    # ─── AI/LLM ───
    DASHSCOPE_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
