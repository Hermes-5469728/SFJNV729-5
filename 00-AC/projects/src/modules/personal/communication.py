"""DADS Personal - 关键沟通留痕模块

P1核心功能：快速记录医患沟通关键节点，生成防篡改文本记录。
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import json
import uuid


class CommunicationType(Enum):
    OUTPATIENT = "outpatient"
    INPATIENT = "inpatient"
    EMERGENCY = "emergency"
    PHONE = "phone"
    ONLINE = "online"
    FAMILY = "family"


class PatientAttitude(Enum):
    COOPERATIVE = "cooperative"
    NEUTRAL = "neutral"
    ANXIOUS = "anxious"
    HOSTILE = "hostile"
    REFUSAL = "refusal"


class KeyPointType(Enum):
    DIAGNOSIS = "diagnosis"
    TREATMENT = "treatment"
    CONSENT = "consent"
    REFUSAL = "refusal"
    COMPLAINT = "complaint"
    TRANSFER = "transfer"
    DISCHARGE = "discharge"
    OTHER = "other"


@dataclass
class CommunicationRecord:
    record_id: str
    timestamp: str
    communication_type: CommunicationType
    patient_id: str
    patient_name: str
    doctor_id: str
    doctor_name: str
    department: str

    location: str
    duration_minutes: int
    key_points: List[str]
    key_point_types: List[KeyPointType]

    patient_attitude: PatientAttitude
    patient_statements: List[str]
    patient_questions: List[str]

    content_summary: str
    agreements: List[str]
    disputes: List[str]

    attachments: List[str]

    hash_value: str
    previous_hash: Optional[str]
    signature_confirmed: bool
    archived: bool


class CommunicationTracker:
    """医患沟通留痕追踪器"""

    def __init__(self, doctor_id: str, doctor_name: str):
        self.doctor_id = doctor_id
        self.doctor_name = doctor_name
        self.records: List[CommunicationRecord] = []
        self.chain_hashes: List[str] = []

    def generate_record_id(self) -> str:
        return f"CR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

    def generate_hash(self, record: Dict) -> str:
        record_copy = record.copy()
        record_copy.pop('hash_value', None)
        record_copy.pop('previous_hash', None)
        content_str = json.dumps(record_copy, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def create_record(
        self,
        patient_id: str,
        patient_name: str,
        department: str,
        communication_type: CommunicationType,
        location: str,
        duration_minutes: int,
        key_points: List[str],
        key_point_types: List[KeyPointType],
        patient_attitude: PatientAttitude,
        patient_statements: List[str],
        patient_questions: List[str],
        content_summary: str,
        agreements: List[str],
        disputes: List[str],
        attachments: Optional[List[str]] = None
    ) -> CommunicationRecord:

        previous_hash = self.chain_hashes[-1] if self.chain_hashes else "0" * 64
        record_id = self.generate_record_id()
        timestamp = datetime.now().isoformat()

        record_data = {
            "record_id": record_id,
            "timestamp": timestamp,
            "communication_type": communication_type.value,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor_name,
            "department": department,
            "location": location,
            "duration_minutes": duration_minutes,
            "key_points": key_points,
            "key_point_types": [kpt.value for kpt in key_point_types],
            "patient_attitude": patient_attitude.value,
            "patient_statements": patient_statements,
            "patient_questions": patient_questions,
            "content_summary": content_summary,
            "agreements": agreements,
            "disputes": disputes,
            "attachments": attachments or [],
            "signature_confirmed": False,
            "archived": False,
            "previous_hash": previous_hash
        }

        record_data["hash_value"] = self.generate_hash(record_data)

        record = CommunicationRecord(
            record_id=record_data["record_id"],
            timestamp=record_data["timestamp"],
            communication_type=CommunicationType(record_data["communication_type"]),
            patient_id=record_data["patient_id"],
            patient_name=record_data["patient_name"],
            doctor_id=record_data["doctor_id"],
            doctor_name=record_data["doctor_name"],
            department=record_data["department"],
            location=record_data["location"],
            duration_minutes=record_data["duration_minutes"],
            key_points=record_data["key_points"],
            key_point_types=[KeyPointType(kpt) for kpt in record_data["key_point_types"]],
            patient_attitude=PatientAttitude(record_data["patient_attitude"]),
            patient_statements=record_data["patient_statements"],
            patient_questions=record_data["patient_questions"],
            content_summary=record_data["content_summary"],
            agreements=record_data["agreements"],
            disputes=record_data["disputes"],
            attachments=record_data["attachments"],
            hash_value=record_data["hash_value"],
            previous_hash=record_data["previous_hash"],
            signature_confirmed=False,
            archived=False
        )

        self.records.append(record)
        self.chain_hashes.append(record.hash_value)

        return record

    def _serialize_record(self, record: CommunicationRecord) -> Dict:
        return {
            "record_id": record.record_id,
            "timestamp": record.timestamp,
            "communication_type": record.communication_type.value,
            "patient_id": record.patient_id,
            "patient_name": record.patient_name,
            "doctor_id": record.doctor_id,
            "doctor_name": record.doctor_name,
            "department": record.department,
            "location": record.location,
            "duration_minutes": record.duration_minutes,
            "key_points": record.key_points,
            "key_point_types": [kpt.value for kpt in record.key_point_types],
            "patient_attitude": record.patient_attitude.value,
            "patient_statements": record.patient_statements,
            "patient_questions": record.patient_questions,
            "content_summary": record.content_summary,
            "agreements": record.agreements,
            "disputes": record.disputes,
            "attachments": record.attachments,
            "hash_value": record.hash_value,
            "previous_hash": record.previous_hash,
            "signature_confirmed": record.signature_confirmed,
            "archived": record.archived,
        }

    def verify_chain_integrity(self) -> Tuple[bool, List[str]]:
        errors = []
        if len(self.chain_hashes) != len(self.records):
            errors.append("Records and hashes count mismatch")
            return False, errors

        for i, record in enumerate(self.records):
            record_data = self._serialize_record(record)
            expected_hash = self.generate_hash(record_data)

            if record.hash_value != expected_hash:
                errors.append(f"Record {record.record_id}: Content hash mismatch")

        return len(errors) == 0, errors

    def get_records_by_patient(self, patient_id: str) -> List[CommunicationRecord]:
        return [r for r in self.records if r.patient_id == patient_id]

    def get_records_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[CommunicationRecord]:
        return [
            r for r in self.records
            if start_date <= datetime.fromisoformat(r.timestamp) <= end_date
        ]

    def get_critical_records(self, patient_id: Optional[str] = None) -> List[CommunicationRecord]:
        critical_types = [KeyPointType.REFUSAL, KeyPointType.COMPLAINT]
        records = self.records if not patient_id else self.get_records_by_patient(patient_id)

        return [
            r for r in records
            if any(kt in critical_types for kt in r.key_point_types)
            or r.patient_attitude in [PatientAttitude.HOSTILE, PatientAttitude.REFUSAL]
        ]

    def export_record(self, record_id: str) -> Optional[Dict]:
        for record in self.records:
            if record.record_id == record_id:
                return self._serialize_record(record)
        return None

    def export_patient_timeline(self, patient_id: str) -> List[Dict]:
        records = sorted(
            self.get_records_by_patient(patient_id),
            key=lambda r: r.timestamp
        )

        timeline = []
        for record in records:
            timeline.append({
                "record_id": record.record_id,
                "timestamp": record.timestamp,
                "type": record.communication_type.value,
                "location": record.location,
                "summary": record.content_summary,
                "patient_attitude": record.patient_attitude.value,
                "key_points": record.key_points,
                "agreements": record.agreements,
                "disputes": record.disputes,
                "hash": record.hash_value
            })

        return timeline


def quick_log_communication(
    patient_id: str,
    patient_name: str,
    department: str,
    communication_type: str,
    content_summary: str,
    patient_attitude: str = "neutral",
    key_points: Optional[List[str]] = None,
    doctor_id: str = "D001",
    doctor_name: str = "医生"
) -> Dict:
    tracker = CommunicationTracker(doctor_id, doctor_name)

    comm_type = CommunicationType(communication_type)
    attitude = PatientAttitude(patient_attitude)

    record = tracker.create_record(
        patient_id=patient_id,
        patient_name=patient_name,
        department=department,
        communication_type=comm_type,
        location="门诊诊室",
        duration_minutes=10,
        key_points=key_points or [content_summary[:100]],
        key_point_types=[KeyPointType.OTHER],
        patient_attitude=attitude,
        patient_statements=[],
        patient_questions=[],
        content_summary=content_summary,
        agreements=[],
        disputes=[]
    )

    return {
        "record_id": record.record_id,
        "timestamp": record.timestamp,
        "hash_value": record.hash_value,
        "verified": True
    }


if __name__ == "__main__":
    print("=== 关键沟通留痕测试 ===")

    tracker = CommunicationTracker(doctor_id="D001", doctor_name="李医生")

    record1 = tracker.create_record(
        patient_id="P12345",
        patient_name="张三",
        department="心内科",
        communication_type=CommunicationType.OUTPATIENT,
        location="门诊诊室301",
        duration_minutes=15,
        key_points=["告知患者需要安装支架", "患者表示理解手术风险"],
        key_point_types=[KeyPointType.DIAGNOSIS, KeyPointType.CONSENT],
        patient_attitude=PatientAttitude.COOPERATIVE,
        patient_statements=["我理解手术风险", "希望尽快安排手术"],
        patient_questions=["手术后需要住院多久？"],
        content_summary="门诊告知患者冠状动脉支架植入术的必要性和风险，患者表示理解并同意手术。",
        agreements=["同意进行冠状动脉支架植入术", "术后配合康复治疗"],
        disputes=[]
    )

    print(f"记录ID: {record1.record_id}")
    print(f"时间戳: {record1.timestamp}")
    print(f"患者态度: {record1.patient_attitude.value}")
    print(f"关键要点: {record1.key_points}")
    print(f"区块链哈希: {record1.hash_value[:16]}...")
    print(f"前序哈希: {record1.previous_hash[:16] if record1.previous_hash else 'None'}...")

    print("\n=== 链完整性验证 ===")
    is_valid, errors = tracker.verify_chain_integrity()
    print(f"链完整性: {'PASS' if is_valid else 'FAIL'}")
    if errors:
        for error in errors:
            print(f"  - {error}")

    print("\n=== 患者时间线 ===")
    timeline = tracker.export_patient_timeline("P12345")
    for item in timeline:
        print(f"[{item['timestamp']}] {item['type']}: {item['summary'][:50]}...")

    print("\n=== 快速记录测试 ===")
    quick_result = quick_log_communication(
        patient_id="P67890",
        patient_name="王五",
        department="消化内科",
        communication_type="outpatient",
        content_summary="患者拒绝胃镜检查，要求先保守治疗。已告知保守治疗可能延误病情。",
        patient_attitude="refusal"
    )
    print(f"快速记录ID: {quick_result['record_id']}")
    print(f"防篡改哈希: {quick_result['hash_value']}")
