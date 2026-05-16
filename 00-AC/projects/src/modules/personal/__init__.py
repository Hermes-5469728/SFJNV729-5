"""DADS Personal 模块 - 个人版医生自我保护助手

P0 核心功能：
- 病历/处方合规性自查引擎
- 免责话术生成器

P1 辅助功能：
- 关键沟通留痕模块
- 工作日志自动化模块
"""
from .compliance import (
    MedicalRecordComplianceChecker,
    check_medical_record,
    RiskLevel,
    InspectionType,
    ComplianceIssue,
    ComplianceCheckResult,
)
from .disclaimer import (
    DisclaimerGenerator,
    generate_consent,
    generate_refusal,
    generate_non_compliance_record,
    DisclosureType,
    Severity,
    DisclosureStatement,
    PatientResponse,
)
from .communication import (
    CommunicationTracker,
    CommunicationRecord,
    CommunicationType,
    PatientAttitude,
    KeyPointType,
    quick_log_communication,
)
from .worklog import (
    WorkLogAutomation,
    WorkRecord,
    WorkReport,
    WorkType,
    ReportType,
    generate_daily_report,
)

__all__ = [
    # P0 合规自查
    "MedicalRecordComplianceChecker",
    "check_medical_record",
    "RiskLevel",
    "InspectionType",
    "ComplianceIssue",
    "ComplianceCheckResult",
    # P0 免责话术
    "DisclaimerGenerator",
    "generate_consent",
    "generate_refusal",
    "generate_non_compliance_record",
    "DisclosureType",
    "Severity",
    "DisclosureStatement",
    "PatientResponse",
    # P1 沟通留痕
    "CommunicationTracker",
    "CommunicationRecord",
    "CommunicationType",
    "PatientAttitude",
    "KeyPointType",
    "quick_log_communication",
    # P1 工作日志
    "WorkLogAutomation",
    "WorkRecord",
    "WorkReport",
    "WorkType",
    "ReportType",
    "generate_daily_report",
]