"""AC Medical Module Models - SQLAlchemy 模型 - 强制 med_ 前缀"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from src.core.database import Base

class MedDrug(Base):
    __tablename__ = "med_drugs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), index=True, nullable=False)
    generic_name = Column(String(200))
    drug_class = Column(String(100))
    indication = Column(Text)
    dosage = Column(String(200))
    contraindications = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

class MedInteraction(Base):
    __tablename__ = "med_interactions"

    id = Column(Integer, primary_key=True, index=True)
    drug_a = Column(String(200), index=True)
    drug_b = Column(String(200), index=True)
    severity = Column(String(50))
    description = Column(Text)
    management = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

class MedGuideline(Base):
    __tablename__ = "med_guidelines"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(300), index=True)
    source = Column(String(200))
    grade = Column(String(10))
    recommendation = Column(Text)
    evidence = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

class MedSafetyAlert(Base):
    __tablename__ = "med_safety_alerts"

    id = Column(Integer, primary_key=True, index=True)
    drug_name = Column(String(200), index=True)
    alert_type = Column(String(100))
    description = Column(Text)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class MedUserProfile(Base):
    __tablename__ = "med_user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    role = Column(String(50))
    prefs_json = Column(Text)
    last_login = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
