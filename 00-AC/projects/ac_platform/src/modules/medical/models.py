"""医疗模块数据库模型 · med_ 表前缀 · src/modules/medical/models.py"""
from datetime import date as date_t
from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.core.base import Base


class CoreUser(Base):
    __tablename__ = "core_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False, default="resident")
    created_at = Column(DateTime, server_default=func.now())


class MedDrug(Base):
    __tablename__ = "med_drugs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, index=True)
    class_name = Column(String(64))
    aliases = Column(Text)
    guideline = Column(Text)
    verified_date = Column(Date)
    created_at = Column(DateTime, server_default=func.now())


class MedInteraction(Base):
    __tablename__ = "med_interactions"

    id = Column(Integer, primary_key=True, index=True)
    drug_a = Column(String(128), nullable=False, index=True)
    drug_b = Column(String(128), nullable=False, index=True)
    severity = Column(String(32), nullable=False)
    mechanism = Column(Text)
    recommendation = Column(Text)
    source = Column(String(256))
    verified_date = Column(Date)
    created_at = Column(DateTime, server_default=func.now())


class MedGuideline(Base):
    __tablename__ = "med_guidelines"

    id = Column(Integer, primary_key=True, index=True)
    condition_name = Column(String(256), nullable=False, index=True)
    source = Column(String(256))
    key_point = Column(Text, nullable=False)
    evidence_level = Column(String(8))
    guideline_date = Column(Date)
    created_at = Column(DateTime, server_default=func.now())


class MedClinicalNote(Base):
    __tablename__ = "med_clinical_notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("core_users.id"), nullable=False)
    note_type = Column(String(32))
    content = Column(Text)
    entities = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("CoreUser")
