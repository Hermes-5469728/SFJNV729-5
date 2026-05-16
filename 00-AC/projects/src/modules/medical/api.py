"""AC Medical Module API Routes - FastAPI 路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ..shared.dependencies import get_db
from .schemas import (
    DrugCreate, DrugResponse,
    InteractionCheckRequest, InteractionResponse,
    ClinicalScoreRequest, ClinicalScoreResponse,
    GuidelineSearchRequest, GuidelineResponse,
    SafetyAlertRequest, SafetyAlertResponse,
    DefenseCheckRequest, DefenseCheckResponse,
)
from . import crud, scores
from .defense import DADSDefenseProcessor

router = APIRouter(prefix="/medical", tags=["medical"])
_defense = DADSDefenseProcessor()

@router.get("/drugs", response_model=List[DrugResponse])
def list_drugs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    drugs = crud.get_drugs(db, skip=skip, limit=limit)
    return drugs

@router.post("/drugs", response_model=DrugResponse)
def create_drug(drug: DrugCreate, db: Session = Depends(get_db)):
    return crud.create_drug(db, drug.model_dump())

@router.get("/drugs/{drug_name}", response_model=DrugResponse)
def get_drug(drug_name: str, db: Session = Depends(get_db)):
    drug = crud.get_drug_by_name(db, drug_name)
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")
    return drug

@router.post("/interactions/check", response_model=InteractionResponse)
def check_interaction(req: InteractionCheckRequest, db: Session = Depends(get_db)):
    interaction = crud.get_interaction(db, req.drug_a, req.drug_b)
    if not interaction:
        return InteractionResponse(
            drug_a=req.drug_a, drug_b=req.drug_b,
            severity="Unknown", description="No interaction data found.",
            management="Verify with pharmacist or drug database."
        )
    return interaction

@router.get("/interactions/{drug_name}", response_model=List[InteractionResponse])
def list_interactions(drug_name: str, db: Session = Depends(get_db)):
    return crud.get_interactions_by_drug(db, drug_name)

@router.post("/scores/calculate", response_model=ClinicalScoreResponse)
def calculate_score(req: ClinicalScoreRequest):
    score, risk = scores.calculate_score(req.score_type, req.params)
    return ClinicalScoreResponse(score_type=req.score_type, score=score, risk=risk)

@router.get("/scores/crcl_adjustment/{drug_name}")
def crcl_adjustment(drug_name: str, crcl: float = Query(..., description="CrCl in mL/min")):
    recommendation = scores.check_crcl_adjustment(drug_name, crcl)
    return {"drug": drug_name, "crcl": crcl, "recommendation": recommendation}

@router.post("/guidelines/search", response_model=List[GuidelineResponse])
def search_guidelines(req: GuidelineSearchRequest, db: Session = Depends(get_db)):
    return crud.search_guidelines(db, req.query, req.grade, req.top_k)

@router.get("/safety/{drug_name}", response_model=List[SafetyAlertResponse])
def get_safety_alerts(drug_name: str, db: Session = Depends(get_db)):
    return crud.get_safety_alerts(db, drug_name)

@router.post("/safety/alerts", response_model=SafetyAlertResponse)
def create_alert(alert: SafetyAlertRequest, db: Session = Depends(get_db)):
    return crud.create_safety_alert(db, alert.model_dump())

@router.post("/defense/check", response_model=DefenseCheckResponse)
def defense_check(req: DefenseCheckRequest):
    result = _defense.process(req.input, req.context)
    return DefenseCheckResponse(
        blocked=result["blocked"],
        reason=result["reason"],
        layers=result.get("layers", {}),
    )

@router.get("/defense/status")
def defense_status():
    return _defense.get_status()
