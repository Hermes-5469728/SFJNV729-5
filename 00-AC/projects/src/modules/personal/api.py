"""DADS Personal Module API Routes - 个人版医生自我保护助手"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional

from . import compliance, disclaimer, communication, worklog
from .communication import (
    CommunicationType, PatientAttitude, KeyPointType,
    CommunicationTracker
)
from .worklog import WorkType, ReportType, WorkLogAutomation

router = APIRouter(prefix="/personal", tags=["personal"])


class DiagnosisCodeInput(BaseModel):
    codes: List[str] = Field(..., description="ICD-10诊断编码列表")


class TreatmentInput(BaseModel):
    items: List[str] = Field(..., description="诊疗项目列表")


class DrugInput(BaseModel):
    drugs: List[str] = Field(..., description="药品列表，格式：'编码 药品名'")


class MedicalRecordCheckRequest(BaseModel):
    patient_id: Optional[str] = Field(None, description="患者ID")
    diagnosis_codes: List[str] = Field(..., description="诊断编码列表")
    treatment_list: List[str] = Field(default_factory=list, description="诊疗项目列表")
    drug_list: List[str] = Field(default_factory=list, description="药品列表")
    inspection_type: str = Field("outpatient", description="检查类型: outpatient/inpatient/emergency/prescription")


class MedicalRecordCheckResponse(BaseModel):
    check_id: str
    timestamp: str
    inspection_type: str
    patient_id: Optional[str]
    overall_risk: str
    issues: List[dict]
    compliance_score: float
    recommendations: List[str]
    passed: bool


@router.post("/compliance/check", response_model=MedicalRecordCheckResponse)
def check_medical_record_compliance(req: MedicalRecordCheckRequest):
    record = {
        "patient_id": req.patient_id,
        "diagnosis_codes": req.diagnosis_codes,
        "treatment_list": req.treatment_list,
        "drug_list": req.drug_list
    }
    result = compliance.check_medical_record(record, req.inspection_type)
    return result


@router.get("/compliance/risk-codes")
def get_high_risk_codes():
    return {
        "high_risk_codes": compliance.MedicalRecordComplianceChecker.HIGH_RISK_CODES,
        "prohibited_combinations": [
            {"codes": c["codes"], "name": c["name"]}
            for c in compliance.MedicalRecordComplianceChecker.PROHIBITED_COMBINATIONS
        ],
        "excessive_patterns": compliance.MedicalRecordComplianceChecker.EXCESSIVE_TREATMENT_PATTERNS
    }


class ConsentRequest(BaseModel):
    patient_id: str
    patient_name: str
    doctor_id: str
    doctor_name: str
    department: str
    diagnosis: str
    procedure: str
    purpose: str
    risks: str
    alternatives: Optional[str] = "无"
    consequences: Optional[str] = "可能延误诊疗，导致病情加重"


class ConsentResponse(BaseModel):
    statement_id: str
    timestamp: str
    content: str
    signature_required: bool
    witness_required: bool
    hash_value: str


@router.post("/disclaimer/consent", response_model=ConsentResponse)
def create_consent(req: ConsentRequest):
    result = disclaimer.generate_consent(
        patient_id=req.patient_id,
        patient_name=req.patient_name,
        doctor_id=req.doctor_id,
        doctor_name=req.doctor_name,
        department=req.department,
        diagnosis=req.diagnosis,
        procedure=req.procedure,
        purpose=req.purpose,
        risks=req.risks,
        alternatives=req.alternatives,
        consequences=req.consequences
    )
    return result


class RefusalRequest(BaseModel):
    patient_id: str
    patient_name: str
    doctor_id: str
    doctor_name: str
    department: str
    diagnosis: str
    recommended_procedure: str
    potential_consequences: str


class RefusalResponse(BaseModel):
    statement_id: str
    timestamp: str
    content: str
    signature_required: bool
    witness_required: bool
    hash_value: str


@router.post("/disclaimer/refusal", response_model=RefusalResponse)
def create_refusal(req: RefusalRequest):
    result = disclaimer.generate_refusal(
        patient_id=req.patient_id,
        patient_name=req.patient_name,
        doctor_id=req.doctor_id,
        doctor_name=req.doctor_name,
        department=req.department,
        diagnosis=req.diagnosis,
        recommended_procedure=req.recommended_procedure,
        potential_consequences=req.potential_consequences
    )
    return result


class NonComplianceRequest(BaseModel):
    patient_id: str
    patient_name: str
    doctor_id: str
    doctor_name: str
    department: str
    communication_content: str
    patient_attitude: str
    non_compliance_behavior: str
    patient_reason: Optional[str] = "患者未说明"
    measures_taken: Optional[str] = "已告知风险并记录"


class NonComplianceResponse(BaseModel):
    statement_id: str
    timestamp: str
    content: str
    signature_required: bool
    witness_required: bool
    hash_value: str
    archived: bool


@router.post("/disclaimer/non-compliance", response_model=NonComplianceResponse)
def create_non_compliance_record(req: NonComplianceRequest):
    result = disclaimer.generate_non_compliance_record(
        patient_id=req.patient_id,
        patient_name=req.patient_name,
        doctor_id=req.doctor_id,
        doctor_name=req.doctor_name,
        department=req.department,
        communication_content=req.communication_content,
        patient_attitude=req.patient_attitude,
        non_compliance_behavior=req.non_compliance_behavior,
        patient_reason=req.patient_reason,
        measures_taken=req.measures_taken
    )
    return result


@router.get("/disclaimer/types")
def get_disclaimer_types():
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in disclaimer.DisclosureType
        ],
        "severity_levels": [
            {"value": s.value, "name": s.name}
            for s in disclaimer.Severity
        ]
    }


class CommunicationRecordRequest(BaseModel):
    patient_id: str
    patient_name: str
    department: str
    communication_type: str
    location: Optional[str] = ""
    duration_minutes: Optional[int] = 0
    key_points: List[str]
    key_point_types: List[str]
    patient_attitude: str
    patient_statements: Optional[List[str]] = []
    patient_questions: Optional[List[str]] = []
    content_summary: str
    agreements: Optional[List[str]] = []
    disputes: Optional[List[str]] = []
    attachments: Optional[List[str]] = []


class CommunicationRecordResponse(BaseModel):
    record_id: str
    timestamp: str
    communication_type: str
    patient_attitude: str
    key_points: List[str]
    hash_value: str
    chain_valid: bool


@router.post("/communication/record", response_model=CommunicationRecordResponse)
def create_communication_record(req: CommunicationRecordRequest):
    tracker = CommunicationTracker()
    record = tracker.create_record(
        patient_id=req.patient_id,
        patient_name=req.patient_name,
        department=req.department,
        communication_type=CommunicationType(req.communication_type),
        location=req.location,
        duration_minutes=req.duration_minutes,
        key_points=req.key_points,
        key_point_types=[KeyPointType(kpt) for kpt in req.key_point_types],
        patient_attitude=PatientAttitude(req.patient_attitude),
        patient_statements=req.patient_statements,
        patient_questions=req.patient_questions,
        content_summary=req.content_summary,
        agreements=req.agreements,
        disputes=req.disputes,
        attachments=req.attachments
    )
    valid, _ = tracker.verify_chain_integrity()
    return CommunicationRecordResponse(
        record_id=record.record_id,
        timestamp=record.timestamp,
        communication_type=record.communication_type.value,
        patient_attitude=record.patient_attitude.value,
        key_points=record.key_points,
        hash_value=record.hash_value,
        chain_valid=valid
    )


class QuickLogRequest(BaseModel):
    patient_id: str
    patient_name: str
    department: str
    communication_type: str
    content_summary: str
    key_points: List[str]
    patient_attitude: str


class QuickLogResponse(BaseModel):
    record_id: str
    hash_value: str
    timestamp: str


@router.post("/communication/quick-log", response_model=QuickLogResponse)
def quick_log_communication(req: QuickLogRequest):
    record = communication.quick_log_communication(
        patient_id=req.patient_id,
        patient_name=req.patient_name,
        department=req.department,
        communication_type=CommunicationType(req.communication_type),
        content_summary=req.content_summary,
        key_points=req.key_points,
        patient_attitude=PatientAttitude(req.patient_attitude)
    )
    return QuickLogResponse(
        record_id=record.record_id,
        hash_value=record.hash_value,
        timestamp=record.timestamp
    )


@router.get("/communication/verify")
def verify_communication_chain():
    tracker = CommunicationTracker()
    valid, errors = tracker.verify_chain_integrity()
    return {
        "chain_valid": valid,
        "errors": errors,
        "record_count": len(tracker.records)
    }


@router.get("/communication/timeline/{patient_id}")
def get_patient_timeline(patient_id: str):
    tracker = CommunicationTracker()
    timeline = tracker.export_patient_timeline(patient_id)
    return {"patient_id": patient_id, "timeline": timeline}


class WorkRecordRequest(BaseModel):
    work_type: str
    content: str
    duration_minutes: int
    location: Optional[str] = ""
    participants: Optional[List[str]] = []
    outcome: Optional[str] = ""
    issues: Optional[List[str]] = []
    metadata: Optional[dict] = {}


class WorkRecordResponse(BaseModel):
    record_id: str
    timestamp: str
    work_type: str
    content: str
    duration_minutes: int
    hash_value: str


@router.post("/worklog/record", response_model=WorkRecordResponse)
def create_work_record(req: WorkRecordRequest):
    automation = WorkLogAutomation()
    record = automation.record_work(
        work_type=WorkType(req.work_type),
        content=req.content,
        duration_minutes=req.duration_minutes,
        location=req.location,
        participants=req.participants,
        outcome=req.outcome,
        issues=req.issues,
        metadata=req.metadata
    )
    return WorkRecordResponse(
        record_id=record.record_id,
        timestamp=record.timestamp,
        work_type=record.work_type.value,
        content=record.content,
        duration_minutes=record.duration_minutes,
        hash_value=record.hash_value
    )


@router.get("/worklog/report/{report_type}")
def generate_work_report(report_type: str):
    from datetime import date, timedelta
    automation = WorkLogAutomation()
    today = date.today()
    start_date = today - timedelta(days=today.weekday())
    end_date = today
    report = automation.generate_report(
        report_type=ReportType(report_type),
        start_date=start_date,
        end_date=end_date
    )
    return {
        "report_id": report.report_id,
        "report_type": report.report_type.value,
        "start_date": str(report.start_date),
        "end_date": str(report.end_date),
        "total_records": report.total_records,
        "total_minutes": report.total_minutes,
        "statistics": report.statistics,
        "highlights": report.highlights,
        "issues": report.issues
    }


@router.get("/worklog/statistics")
def get_work_statistics():
    from datetime import date, timedelta
    automation = WorkLogAutomation()
    today = date.today()
    start_date = today - timedelta(days=30)
    records = [
        r for r in automation.records
        if start_date <= date.fromisoformat(r.timestamp[:10]) <= today
    ]
    return automation.calculate_statistics(records)
