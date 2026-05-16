"""AC Medical Module CRUD - 数据操作"""
from sqlalchemy.orm import Session
from typing import List, Optional

from .models import MedDrug, MedInteraction, MedGuideline, MedSafetyAlert, MedUserProfile

def get_drug_by_name(db: Session, name: str) -> Optional[MedDrug]:
    return db.query(MedDrug).filter(MedDrug.name.ilike(f"%{name}%")).first()

def get_drugs(db: Session, skip: int = 0, limit: int = 100) -> List[MedDrug]:
    return db.query(MedDrug).offset(skip).limit(limit).all()

def create_drug(db: Session, drug_data: dict) -> MedDrug:
    drug = MedDrug(**drug_data)
    db.add(drug)
    db.commit()
    db.refresh(drug)
    return drug

def get_interaction(db: Session, drug_a: str, drug_b: str) -> Optional[MedInteraction]:
    return db.query(MedInteraction).filter(
        ((MedInteraction.drug_a.ilike(f"%{drug_a}%")) & (MedInteraction.drug_b.ilike(f"%{drug_b}%"))) |
        ((MedInteraction.drug_a.ilike(f"%{drug_b}%")) & (MedInteraction.drug_b.ilike(f"%{drug_a}%")))
    ).first()

def get_interactions_by_drug(db: Session, drug_name: str) -> List[MedInteraction]:
    return db.query(MedInteraction).filter(
        (MedInteraction.drug_a.ilike(f"%{drug_name}%")) | (MedInteraction.drug_b.ilike(f"%{drug_name}%"))
    ).all()

def search_guidelines(db: Session, query: str, grade: str = None, top_k: int = 5) -> List[MedGuideline]:
    q = db.query(MedGuideline).filter(MedGuideline.topic.ilike(f"%{query}%"))
    if grade:
        q = q.filter(MedGuideline.grade == grade)
    return q.limit(top_k).all()

def get_safety_alerts(db: Session, drug_name: str) -> List[MedSafetyAlert]:
    return db.query(MedSafetyAlert).filter(
        MedSafetyAlert.drug_name.ilike(f"%{drug_name}%"),
        MedSafetyAlert.active == True
    ).all()

def create_safety_alert(db: Session, alert_data: dict) -> MedSafetyAlert:
    alert = MedSafetyAlert(**alert_data)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert

def get_user_profile(db: Session, username: str) -> Optional[MedUserProfile]:
    return db.query(MedUserProfile).filter(MedUserProfile.username == username).first()

def create_user_profile(db: Session, username: str, role: str = "user") -> MedUserProfile:
    profile = MedUserProfile(username=username, role=role)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile
