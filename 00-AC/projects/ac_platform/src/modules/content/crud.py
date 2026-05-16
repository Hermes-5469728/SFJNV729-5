"""内容模块数据操作 · 仅操作 cnt_ 表 · src/modules/content/crud.py"""
from typing import List, Optional

from sqlalchemy.orm import Session

from src.modules.content import models, schemas


# ─── Creative Assets ───
def create_asset(db: Session, data: schemas.CreativeAssetCreate) -> models.CntCreativeAsset:
    asset = models.CntCreativeAsset(**data.model_dump(by_alias=True))
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def get_assets(db: Session, category: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[models.CntCreativeAsset]:
    q = db.query(models.CntCreativeAsset)
    if category:
        q = q.filter(models.CntCreativeAsset.category == category)
    return q.order_by(models.CntCreativeAsset.created_at.desc()).offset(skip).limit(limit).all()


def search_assets(db: Session, query: str) -> List[models.CntCreativeAsset]:
    q = f"%{query}%"
    return db.query(models.CntCreativeAsset).filter(
        models.CntCreativeAsset.title.ilike(q) |
        models.CntCreativeAsset.tags.ilike(q) |
        models.CntCreativeAsset.content.ilike(q)
    ).all()


def delete_asset(db: Session, asset_id: int) -> bool:
    asset = db.query(models.CntCreativeAsset).filter(models.CntCreativeAsset.id == asset_id).first()
    if asset:
        db.delete(asset)
        db.commit()
        return True
    return False


# ─── References ───
def create_reference(db: Session, data: schemas.ReferenceCreate) -> models.CntReference:
    ref = models.CntReference(**data.model_dump())
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


def get_references(db: Session, ref_type: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[models.CntReference]:
    q = db.query(models.CntReference)
    if ref_type:
        q = q.filter(models.CntReference.ref_type == ref_type)
    return q.order_by(models.CntReference.created_at.desc()).offset(skip).limit(limit).all()


def search_references(db: Session, query: str) -> List[models.CntReference]:
    q = f"%{query}%"
    return db.query(models.CntReference).filter(
        models.CntReference.title.ilike(q) |
        models.CntReference.tags.ilike(q) |
        models.CntReference.content.ilike(q)
    ).all()
