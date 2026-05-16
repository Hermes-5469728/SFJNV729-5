"""AC Platform API Key Authentication - API Key 鉴权"""
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from typing import Optional

from .config import settings
from .database import get_db

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(get_db)
) -> str:
    if not settings.API_KEY:
        return "dev_mode"
    if api_key == settings.API_KEY:
        return "authenticated"
    raise HTTPException(status_code=401, detail="Invalid API Key")
