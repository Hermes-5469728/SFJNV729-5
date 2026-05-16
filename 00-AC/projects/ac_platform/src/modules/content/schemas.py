"""内容模块 Pydantic 校验 · src/modules/content/schemas.py"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CreativeAssetCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    category: str = Field(..., max_length=64)
    tags: Optional[str] = None
    content: str = Field(..., min_length=1)
    language: str = "zh"
    notes: Optional[str] = None
    metadata_: Optional[dict] = Field(None, alias="metadata")


class CreativeAssetResponse(CreativeAssetCreate):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReferenceCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    ref_type: str = Field(..., max_length=64)
    tags: Optional[str] = None
    content: str = Field(..., min_length=1)
    source: Optional[str] = None
    language: str = "zh"
    notes: Optional[str] = None


class ReferenceResponse(ReferenceCreate):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
