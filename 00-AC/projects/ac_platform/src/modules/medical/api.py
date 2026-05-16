"""医疗模块 API 路由 · 相对路径, main.py 统一挂载 · src/modules/medical/api.py"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from src.shared.deps import get_db
from src.core.auth import get_current_user, require_role, create_token, verify_password, hash_password
from src.modules.medical import schemas
from src.modules.medical import crud
from src.modules.medical.models import CoreUser

router = APIRouter(tags=["Medical"])

# ═══════════════════════════════════════
#  Auth
# ═══════════════════════════════════════
@router.post("/login", response_model=schemas.TokenResponse)
def login(data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(CoreUser).filter(CoreUser.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    token = create_token(user.id, user.username, user.role)
    return schemas.TokenResponse(access_token=token, role=user.role)


# ═══════════════════════════════════════
#  Drugs
# ═══════════════════════════════════════
@router.get("/drugs", response_model=list[schemas.DrugResponse])
def list_drugs(name: str = Query(None), db: Session = Depends(get_db)):
    if name:
        drug = crud.get_drug_by_name(db, name)
        return [drug] if drug else []
    return crud.get_drugs(db)

@router.post("/drugs", response_model=schemas.DrugResponse)
def add_drug(data: schemas.DrugCreate, db: Session = Depends(get_db),
             _=Depends(require_role("attending", "pharmacist"))):
    return crud.create_drug(db, data)


# ═══════════════════════════════════════
#  Interactions
# ═══════════════════════════════════════
@router.get("/interactions", response_model=list[schemas.InteractionResponse])
def list_interactions(drug_a: str = Query(None), drug_b: str = Query(None),
                      db: Session = Depends(get_db)):
    if drug_a and drug_b:
        return crud.check_interaction_pair(db, drug_a, drug_b)
    return crud.get_interactions(db)

@router.post("/interactions", response_model=schemas.InteractionResponse)
def add_interaction(data: schemas.InteractionCreate, db: Session = Depends(get_db),
                    _=Depends(require_role("attending", "pharmacist"))):
    return crud.create_interaction(db, data)


# ═══════════════════════════════════════
#  Guidelines
# ═══════════════════════════════════════
@router.get("/guidelines", response_model=list[schemas.GuidelineResponse])
def list_guidelines(q: str = Query(None), db: Session = Depends(get_db)):
    if q:
        return crud.search_guidelines(db, q)
    return crud.get_guidelines(db)

@router.post("/guidelines", response_model=schemas.GuidelineResponse)
def add_guideline(data: schemas.GuidelineCreate, db: Session = Depends(get_db),
                  _=Depends(require_role("attending"))):
    return crud.create_guideline(db, data)


# ═══════════════════════════════════════
#  Clinical Notes
# ═══════════════════════════════════════
@router.post("/notes", response_model=schemas.ClinicalNoteResponse)
def create_note(data: schemas.ClinicalNoteCreate, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    return crud.create_clinical_note(db, user.id, data)

@router.get("/notes", response_model=list[schemas.ClinicalNoteResponse])
def list_notes(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return crud.get_user_notes(db, user.id)
