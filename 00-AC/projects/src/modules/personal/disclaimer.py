"""DADS Personal - 免责话术生成器

P0核心功能：针对高风险操作或患者不依从情况，生成标准化、具有法律效力的告知话术。
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import json


class DisclosureType(Enum):
    CONSENT = "consent"
    REFUSAL = "refusal"
    RISK_WARNING = "risk_warning"
    NON_COMPLIANCE = "non_compliance"
    TRANSFER = "transfer"
    DISCHARGE = "discharge"


class Severity(Enum):
    ROUTINE = "routine"
    MODERATE = "moderate"
    SERIOUS = "serious"
    CRITICAL = "critical"


@dataclass
class DisclosureStatement:
    statement_id: str
    disclosure_type: DisclosureType
    timestamp: str
    patient_id: Optional[str]
    patient_name: Optional[str]
    doctor_id: str
    doctor_name: str
    department: str
    content: str
    severity: Severity
    signature_required: bool
    witness_required: bool
    hash_value: str
    archived: bool = False


@dataclass
class PatientResponse:
    response_type: str
    timestamp: str
    patient_name: str
    guardian_name: Optional[str] = None
    signature_obtained: bool = False
    witness_name: Optional[str] = None
    notes: Optional[str] = None


class DisclaimerGenerator:
    """免责话术生成器"""

    TEMPLATES = {
        DisclosureType.CONSENT: {
            "title": "知情同意书",
            "template": "【知情同意告知】\n\n患者（姓名）：{patient_name}（病历号：{patient_id}）\n\n您已被告知以下信息：\n\n1. 诊断情况：{diagnosis}\n\n2. 拟进行的诊疗操作：{procedure}\n\n3. 诊疗操作的目的和必要性：{purpose}\n\n4. 可能存在的风险和并发症：\n{risks}\n\n5. 替代诊疗方案（如有）：\n{alternatives}\n\n6. 如不接受诊疗可能产生的后果：\n{consequences}\n\n\n【患者声明】\n本人（或授权代理人）已充分了解上述告知内容，知晓诊疗操作的目的、风险和必要性，经权衡利弊后，自愿选择接受上述诊疗操作。\n\n签名：________________   日期：{timestamp}\n\n【医师声明】\n本人已向患者或授权代理人详细告知了病情、诊疗方案及可能的风险，并解答了相关问题。\n\n医师签名：________________   日期：{timestamp}"
        },
        DisclosureType.REFUSAL: {
            "title": "拒绝诊疗知情书",
            "template": "【拒绝诊疗知情书】\n\n患者（姓名）：{patient_name}（病历号：{patient_id}）\n\n本人已被明确告知：\n\n1. 当前诊断：{diagnosis}\n\n2. 医师建议的诊疗方案：{recommended_procedure}\n\n3. 如不接受该诊疗方案，可能产生的后果包括但不限于：\n{potential_consequences}\n\n4. 本人充分理解拒绝诊疗可能带来的健康风险。\n\n【患者/授权人声明】\n本人经充分考虑，自愿拒绝上述诊疗方案，已知晓并愿意承担由此产生的一切后果。\n\n签名：________________   日期：{timestamp}\n\n【医师确认】\n已向患者充分说明拒绝诊疗的风险，仍被患者拒绝。\n\n医师签名：________________   日期：{timestamp}"
        },
        DisclosureType.RISK_WARNING: {
            "title": "高风险诊疗项目知情告知",
            "template": "【高风险诊疗项目特别告知书】\n\n患者（姓名）：{patient_name}（病历号：{patient_id}）\n\n鉴于您的病情具有以下特殊性质：\n{condition_description}\n\n拟进行的诊疗项目属于高风险项目：{high_risk_procedure}\n\n【特别风险告知】\n该诊疗项目可能发生以下严重并发症，发生率及预后如下：\n{special_risks}\n\n【紧急情况处理预案】\n一旦发生上述严重并发症，医疗机构将采取以下急救措施：\n{emergency_plan}\n\n【患者确认】\n本人已了解上述高风险项目的性质、风险及应急预案，自愿接受该诊疗项目。\n\n签名：________________   日期：{timestamp}"
        },
        DisclosureType.NON_COMPLIANCE: {
            "title": "患者不依从知情记录",
            "template": "【患者不依从情况记录】\n\n患者（姓名）：{patient_name}（病历号：{patient_id}）\n记录时间：{timestamp}\n记录医师：{doctor_name}（工号：{doctor_id}）\n\n【沟通时间】{communication_time}\n\n【沟通内容摘要】\n已向患者详细说明以下事项：\n{communication_content}\n\n【患者态度表现】\n{patient_attitude}\n\n【不依从具体情况】\n不依从行为：{non_compliance_behavior}\n患者理由：{patient_reason}\n\n【已采取的措施】\n{measures_taken}\n\n【医师声明】\n以上沟通内容已如实记录，必要时可作为医疗争议的证据材料。\n\n医师签名：________________   日期：{timestamp}"
        },
        DisclosureType.TRANSFER: {
            "title": "转诊/转科知情同意书",
            "template": "【转诊/转科知情同意书】\n\n患者（姓名）：{patient_name}（病历号：{patient_id}）\n\n因病情需要，拟将您转至：\n转诊/转科目的医院/科室：{target_department}\n\n【转诊/转科原因】\n{transfer_reason}\n\n【当前病情摘要】\n{current_condition}\n\n【已完成的诊疗情况】\n{completed_treatment}\n\n【注意事项】\n转诊途中应注意：{transfer_precautions}\n\n【患者/授权人声明】\n本人已知晓转诊/转科的原因和必要性，同意转诊。\n\n签名：________________   日期：{timestamp}"
        },
        DisclosureType.DISCHARGE: {
            "title": "自动出院/离院知情同意书",
            "template": "【自动出院/离院知情同意书】\n\n患者（姓名）：{patient_name}（病历号：{patient_id}）\n\n【当前诊断】\n{diagnosis}\n\n【当前病情】\n{current_condition}\n\n【医师建议】\n建议继续住院治疗，理由如下：\n{recommended_treatment}\n\n【自动出院/离院风险告知】\n患者自行出院/离院可能产生的风险：\n{discharge_risks}\n\n【出院/离院后注意事项】\n{discharge_instructions}\n\n【患者/授权人声明】\n本人已充分了解出院/离院的风险，仍坚持出院/离院，后果自负。\n\n签名：________________   日期：{timestamp}"
        }
    }

    def __init__(self):
        self.version = "1.0.0"
        self.statement_archive: List[DisclosureStatement] = []

    def generate_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def generate_statement(
        self,
        disclosure_type: DisclosureType,
        patient_id: Optional[str],
        patient_name: Optional[str],
        doctor_id: str,
        doctor_name: str,
        department: str,
        template_params: Dict,
        severity: Severity = Severity.ROUTINE
    ) -> DisclosureStatement:
        template = self.TEMPLATES[disclosure_type]
        timestamp = datetime.now().strftime("%Y年%m月%d日 %H:%M")

        template_params.update({
            "patient_name": patient_name or "_______",
            "patient_id": patient_id or "_______",
            "doctor_name": doctor_name,
            "doctor_id": doctor_id,
            "department": department,
            "timestamp": timestamp
        })

        content = template["template"].format(**template_params)
        statement_id = f"DS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{disclosure_type.value.upper()}"
        hash_value = self.generate_hash(content + statement_id)

        statement = DisclosureStatement(
            statement_id=statement_id,
            disclosure_type=disclosure_type,
            timestamp=datetime.now().isoformat(),
            patient_id=patient_id,
            patient_name=patient_name,
            doctor_id=doctor_id,
            doctor_name=doctor_name,
            department=department,
            content=content,
            severity=severity,
            signature_required=True,
            witness_required=severity in [Severity.SERIOUS, Severity.CRITICAL],
            hash_value=hash_value,
            archived=False
        )

        self.statement_archive.append(statement)
        return statement

    def record_patient_response(
        self,
        statement_id: str,
        response: PatientResponse
    ) -> bool:
        for statement in self.statement_archive:
            if statement.statement_id == statement_id:
                return True
        return False

    def get_archive(self, patient_id: Optional[str] = None) -> List[DisclosureStatement]:
        if patient_id:
            return [s for s in self.statement_archive if s.patient_id == patient_id]
        return self.statement_archive

    def verify_statement(self, statement_id: str, content: str) -> bool:
        for statement in self.statement_archive:
            if statement.statement_id == statement_id:
                return statement.hash_value == self.generate_hash(content + statement_id)
        return False


def generate_consent(
    patient_id: str,
    patient_name: str,
    doctor_id: str,
    doctor_name: str,
    department: str,
    diagnosis: str,
    procedure: str,
    purpose: str,
    risks: str,
    alternatives: str = "无",
    consequences: str = "可能延误诊疗，导致病情加重"
) -> Dict:
    generator = DisclaimerGenerator()
    statement = generator.generate_statement(
        disclosure_type=DisclosureType.CONSENT,
        patient_id=patient_id,
        patient_name=patient_name,
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        department=department,
        template_params={
            "diagnosis": diagnosis,
            "procedure": procedure,
            "purpose": purpose,
            "risks": risks,
            "alternatives": alternatives,
            "consequences": consequences
        },
        severity=Severity.MODERATE
    )

    return {
        "statement_id": statement.statement_id,
        "timestamp": statement.timestamp,
        "content": statement.content,
        "signature_required": statement.signature_required,
        "witness_required": statement.witness_required,
        "hash_value": statement.hash_value
    }


def generate_refusal(
    patient_id: str,
    patient_name: str,
    doctor_id: str,
    doctor_name: str,
    department: str,
    diagnosis: str,
    recommended_procedure: str,
    potential_consequences: str
) -> Dict:
    generator = DisclaimerGenerator()
    statement = generator.generate_statement(
        disclosure_type=DisclosureType.REFUSAL,
        patient_id=patient_id,
        patient_name=patient_name,
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        department=department,
        template_params={
            "diagnosis": diagnosis,
            "recommended_procedure": recommended_procedure,
            "potential_consequences": potential_consequences
        },
        severity=Severity.SERIOUS
    )

    return {
        "statement_id": statement.statement_id,
        "timestamp": statement.timestamp,
        "content": statement.content,
        "signature_required": statement.signature_required,
        "witness_required": statement.witness_required,
        "hash_value": statement.hash_value
    }


def generate_non_compliance_record(
    patient_id: str,
    patient_name: str,
    doctor_id: str,
    doctor_name: str,
    department: str,
    communication_content: str,
    patient_attitude: str,
    non_compliance_behavior: str,
    patient_reason: str = "患者未说明",
    measures_taken: str = "已告知风险并记录"
) -> Dict:
    generator = DisclaimerGenerator()
    statement = generator.generate_statement(
        disclosure_type=DisclosureType.NON_COMPLIANCE,
        patient_id=patient_id,
        patient_name=patient_name,
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        department=department,
        template_params={
            "communication_time": datetime.now().strftime("%Y年%m月%d日 %H:%M"),
            "communication_content": communication_content,
            "patient_attitude": patient_attitude,
            "non_compliance_behavior": non_compliance_behavior,
            "patient_reason": patient_reason,
            "measures_taken": measures_taken
        },
        severity=Severity.MODERATE
    )

    return {
        "statement_id": statement.statement_id,
        "timestamp": statement.timestamp,
        "content": statement.content,
        "signature_required": statement.signature_required,
        "witness_required": statement.witness_required,
        "hash_value": statement.hash_value,
        "archived": statement.archived
    }


if __name__ == "__main__":
    print("=== 知情同意书生成测试 ===")
    result = generate_consent(
        patient_id="P12345",
        patient_name="张三",
        doctor_id="D001",
        doctor_name="李医生",
        department="心内科",
        diagnosis="冠状动脉粥样硬化性心脏病",
        procedure="冠状动脉支架植入术",
        purpose="改善心肌供血，缓解心绞痛症状",
        risks="1. 出血、血肿 2. 血管迷走反射 3. 支架内血栓形成 4. 急诊冠状动脉搭桥术 5. 死亡（发生率<0.5%）",
        alternatives="药物保守治疗，但症状可能持续或加重"
    )
    print(f"文书ID: {result['statement_id']}")
    print(f"防篡改哈希: {result['hash_value']}")
    print(f"需签名: {result['signature_required']}")
    print(f"需见证: {result['witness_required']}")
    print("\n--- 文书内容预览 ---")
    print(result['content'][:500] + "...")

    print("\n\n=== 拒绝诊疗知情书生成测试 ===")
    refusal_result = generate_refusal(
        patient_id="P12345",
        patient_name="张三",
        doctor_id="D001",
        doctor_name="李医生",
        department="心内科",
        diagnosis="急性心肌梗死",
        recommended_procedure="急诊PCI手术",
        potential_consequences="1. 心力衰竭 2. 心律失常 3. 心脏骤停 4. 死亡"
    )
    print(f"文书ID: {refusal_result['statement_id']}")
    print(f"需见证人: {refusal_result['witness_required']}")
