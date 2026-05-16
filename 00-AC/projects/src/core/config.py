"""AC Platform Global Configuration - 全局配置 + AC_CORE_MODE"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

BASE_DIR = Path(__file__).parent.parent.parent

class Settings(BaseModel):
    AC_CORE_MODE: bool = True
    API_KEY: Optional[str] = None
    DATABASE_URL: str = "sqlite:///./ac_platform.db"
    MOTHER_CITY: str = "仙桃市"
    MOTHER_PROVINCE: str = "湖北省"
    OLLAMA_HOST: str = "http://localhost:11434"
    DASHSCOPE_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

AC_CORE_MODE = os.environ.get("AC_CORE_MODE", "true").lower() == "true"
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./ac_platform.db")
