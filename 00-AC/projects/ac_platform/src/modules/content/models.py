"""内容库模型 · cnt_ 表前缀 · src/modules/content/models.py"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func

from src.core.base import Base


class CntCreativeAsset(Base):
    """创意素材库 · 广告文案/视频脚本/金句等"""
    __tablename__ = "cnt_creative_assets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(256), nullable=False)
    category = Column(String(64), nullable=False, index=True)
    tags = Column(String(512))
    content = Column(Text, nullable=False)
    language = Column(String(16), default="zh")
    notes = Column(Text)
    metadata_ = Column("metadata", JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CntReference(Base):
    """通用参考资料 · 方法论/模板/配方等"""
    __tablename__ = "cnt_references"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(256), nullable=False)
    ref_type = Column(String(64), nullable=False, index=True)
    tags = Column(String(512))
    content = Column(Text, nullable=False)
    source = Column(String(256))
    language = Column(String(16), default="zh")
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
