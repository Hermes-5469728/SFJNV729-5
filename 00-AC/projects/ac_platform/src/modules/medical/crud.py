"""医疗模块数据操作 · 仅操作 med_ 表 · src/modules/medical/crud.py"""
from typing import List, Optional

from sqlalchemy.orm import Session

from src.modules.medical import models, schemas


# ─── Drug ───
def get_drugs(db: Session, skip: int = 0, limit: int = 100) -> List[models.MedDrug]:
    return db.query(models.MedDrug).offset(skip).limit(limit).all()

def get_drug_by_name(db: Session, name: str) -> Optional[models.MedDrug]:
    return db.query(models.MedDrug).filter(models.MedDrug.name.ilike(f"%{name}%")).first()

def create_drug(db: Session, data: schemas.DrugCreate) -> models.MedDrug:
    drug = models.MedDrug(**data.model_dump())
    db.add(drug)
    db.commit()
    db.refresh(drug)
    return drug


# ─── Interaction ───
def get_interactions(db: Session, skip: int = 0, limit: int = 200) -> List[models.MedInteraction]:
    return db.query(models.MedInteraction).offset(skip).limit(limit).all()

def check_interaction_pair(db: Session, drug_a: str, drug_b: str) -> List[models.MedInteraction]:
    return db.query(models.MedInteraction).filter(
        (
            (models.MedInteraction.drug_a.ilike(f"%{drug_a}%")) &
            (models.MedInteraction.drug_b.ilike(f"%{drug_b}%"))
        ) | (
            (models.MedInteraction.drug_a.ilike(f"%{drug_b}%")) &
            (models.MedInteraction.drug_b.ilike(f"%{drug_a}%"))
        )
    ).all()

def create_interaction(db: Session, data: schemas.InteractionCreate) -> models.MedInteraction:
    interaction = models.MedInteraction(**data.model_dump())
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


# ─── Guideline ───
def get_guidelines(db: Session, skip: int = 0, limit: int = 100) -> List[models.MedGuideline]:
    return db.query(models.MedGuideline).offset(skip).limit(limit).all()

def search_guidelines(db: Session, query: str) -> List[models.MedGuideline]:
    q = f"%{query}%"
    return db.query(models.MedGuideline).filter(
        models.MedGuideline.condition_name.ilike(q) |
        models.MedGuideline.source.ilike(q) |
        models.MedGuideline.key_point.ilike(q)
    ).all()

def create_guideline(db: Session, data: schemas.GuidelineCreate) -> models.MedGuideline:
    guideline = models.MedGuideline(**data.model_dump())
    db.add(guideline)
    db.commit()
    db.refresh(guideline)
    return guideline


# ─── Clinical Note ───
def create_clinical_note(db: Session, user_id: int, data: schemas.ClinicalNoteCreate) -> models.MedClinicalNote:
    note = models.MedClinicalNote(user_id=user_id, **data.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note

def get_user_notes(db: Session, user_id: int) -> List[models.MedClinicalNote]:
    return db.query(models.MedClinicalNote).filter(
        models.MedClinicalNote.user_id == user_id
    ).order_by(models.MedClinicalNote.created_at.desc()).all()
