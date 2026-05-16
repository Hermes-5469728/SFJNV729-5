"""AC Medical Module Schemas - Pydantic 请求/响应校验"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class DrugBase(BaseModel):
    name: str
    generic_name: Optional[str] = None
    drug_class: Optional[str] = None

class DrugCreate(DrugBase):
    indication: Optional[str] = None
    dosage: Optional[str] = None
    contraindications: Optional[str] = None

class DrugResponse(DrugBase):
    id: int
    indication: Optional[str] = None
    dosage: Optional[str] = None
    contraindications: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class InteractionCheckRequest(BaseModel):
    drug_a: str
    drug_b: str

class InteractionResponse(BaseModel):
    drug_a: str
    drug_b: str
    severity: str
    description: str
    management: str

class ClinicalScoreRequest(BaseModel):
    score_type: str = Field(..., description="cha2ds2_vasc, has_bled, wells_dvt, etc.")
    params: dict

class ClinicalScoreResponse(BaseModel):
    score_type: str
    score: int
    risk: str

class GuidelineSearchRequest(BaseModel):
    query: str
    grade: Optional[str] = None
    top_k: int = 5

class GuidelineResponse(BaseModel):
    topic: str
    source: str
    grade: str
    recommendation: str
    evidence: str

class SafetyAlertRequest(BaseModel):
    drug_name: str
    alert_type: str
    description: str

class SafetyAlertResponse(BaseModel):
    id: int
    drug_name: str
    alert_type: str
    description: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class DefenseCheckRequest(BaseModel):
    input: str
    context: Optional[dict] = None

class DefenseCheckResponse(BaseModel):
    blocked: bool
    reason: str
    layers: dict
