"""医疗模块 Pydantic 校验模型 · src/modules/medical/schemas.py"""
from datetime import date as date_t
from typing import Optional, List
from pydantic import BaseModel, Field


# ─── Drug ───
class DrugBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    class_name: Optional[str] = Field(None, max_length=64)
    aliases: Optional[str] = None
    guideline: Optional[str] = None
    verified_date: Optional[date_t] = None

class DrugCreate(DrugBase):
    pass

class DrugResponse(DrugBase):
    id: int
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Interaction ───
class InteractionBase(BaseModel):
    drug_a: str = Field(..., min_length=1, max_length=128)
    drug_b: str = Field(..., min_length=1, max_length=128)
    severity: str = Field(..., pattern=r"^(CONTRAINDICATED|HIGH|MODERATE|MONITOR)$")
    mechanism: Optional[str] = None
    recommendation: Optional[str] = None
    source: Optional[str] = None

class InteractionCreate(InteractionBase):
    pass

class InteractionResponse(InteractionBase):
    id: int
    verified_date: Optional[date_t] = None

    class Config:
        from_attributes = True


# ─── Guideline ───
class GuidelineBase(BaseModel):
    condition_name: str = Field(..., min_length=1, max_length=256)
    source: Optional[str] = None
    key_point: str = Field(..., min_length=1)
    evidence_level: Optional[str] = None
    guideline_date: Optional[date_t] = None

class GuidelineCreate(GuidelineBase):
    pass

class GuidelineResponse(GuidelineBase):
    id: int

    class Config:
        from_attributes = True


# ─── Clinical Note ───
class ClinicalNoteCreate(BaseModel):
    note_type: Optional[str] = "SOAP"
    content: str = Field(..., min_length=1)
    entities: Optional[dict] = None

class ClinicalNoteResponse(BaseModel):
    id: int
    user_id: int
    note_type: Optional[str]
    content: str
    entities: Optional[dict]
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Auth ───
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
