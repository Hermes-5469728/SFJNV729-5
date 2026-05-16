"""内容模块 API 路由 · src/modules/content/api.py"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from src.shared.deps import get_db
from src.core.auth import get_current_user, require_role
from src.modules.content import schemas
from src.modules.content import crud

router = APIRouter(tags=["Content Library"])


# ═══════════════════════════════════════
#  Creative Assets
# ═══════════════════════════════════════
@router.post("/assets", response_model=schemas.CreativeAssetResponse)
def create_asset(data: schemas.CreativeAssetCreate, db: Session = Depends(get_db),
                 _=Depends(require_role("attending", "admin"))):
    return crud.create_asset(db, data)


@router.get("/assets", response_model=list[schemas.CreativeAssetResponse])
def list_assets(category: str = Query(None), q: str = Query(None),
                db: Session = Depends(get_db)):
    if q:
        return crud.search_assets(db, q)
    return crud.get_assets(db, category=category)


@router.delete("/assets/{asset_id}")
def delete_asset(asset_id: int, db: Session = Depends(get_db),
                 _=Depends(require_role("attending", "admin"))):
    ok = crud.delete_asset(db, asset_id)
    if not ok:
        raise HTTPException(404, "Asset not found")
    return {"deleted": True}


# ═══════════════════════════════════════
#  References
# ═══════════════════════════════════════
@router.post("/references", response_model=schemas.ReferenceResponse)
def create_reference(data: schemas.ReferenceCreate, db: Session = Depends(get_db),
                     _=Depends(require_role("attending", "admin"))):
    return crud.create_reference(db, data)


@router.get("/references", response_model=list[schemas.ReferenceResponse])
def list_references(ref_type: str = Query(None), q: str = Query(None),
                    db: Session = Depends(get_db)):
    if q:
        return crud.search_references(db, q)
    return crud.get_references(db, ref_type=ref_type)
