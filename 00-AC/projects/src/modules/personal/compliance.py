"""DADS Personal - 病历/处方合规性自查引擎

P0核心功能：自动检测高套编码、过度医疗嫌疑，符合医保飞检规则。
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class RiskLevel(Enum):
    SAFE = "safe"
    WARNING = "warning"
    HIGH_RISK = "high_risk"
    VIOLATION = "violation"


class InspectionType(Enum):
    OUTPATIENT = "outpatient"
    INPATIENT = "inpatient"
    EMERGENCY = "emergency"
    PRESCRIPTION = "prescription"


@dataclass
class ComplianceIssue:
    code: str
    category: str
    description: str
    risk_level: RiskLevel
    regulation_reference: str
    suggestion: str


@dataclass
class ComplianceCheckResult:
    check_id: str
    timestamp: str
    inspection_type: InspectionType
    patient_id: Optional[str]
    overall_risk: RiskLevel
    issues: List[ComplianceIssue]
    compliance_score: float
    recommendations: List[str]
    passed: bool


class MedicalRecordComplianceChecker:
    """病历合规性检查器"""

    HIGH_RISK_CODES = {
        "E11": "2型糖尿病",
        "I10": "原发性高血压",
        "J44": "慢性阻塞性肺疾病",
        "M54": "腰痛",
        "K29": "胃炎",
        "N39": "泌尿道感染",
    }

    PROHIBITED_COMBINATIONS = [
        {"codes": ["J01", "J01"], "name": "重复使用同类抗生素"},
        {"codes": ["N02", "N02"], "name": "重复使用镇痛药"},
        {"codes": ["M01", "M01"], "name": "重复使用非甾体抗炎药"},
    ]

    EXCESSIVE_TREATMENT_PATTERNS = [
        {"name": "套餐式检查", "indicators": ["全腹B超", "胸片", "心电图", "血常规", "尿常规"], "threshold": 5},
        {"name": "过度化验", "indicators": ["肝功能", "肾功能", "血脂", "血糖", "心肌酶", "甲状腺功能"], "threshold": 6},
    ]

    def __init__(self):
        self.version = "1.0.0"

    def check_icd编码(self, diagnosis_codes: List[str]) -> List[ComplianceIssue]:
        issues = []
        unique_codes = set(diagnosis_codes)

        if len(diagnosis_codes) != len(unique_codes):
            issues.append(ComplianceIssue(
                code="C001",
                category="编码重复",
                description="存在重复诊断编码",
                risk_level=RiskLevel.WARNING,
                regulation_reference="医保飞检规则-诊断编码规范",
                suggestion="删除重复编码，每个诊断只能选择一个主要编码"
            ))

        for code in diagnosis_codes:
            if code.startswith("Z") and len(diagnosis_codes) > 3:
                issues.append(ComplianceIssue(
                    code="C002",
                    category="高套编码嫌疑",
                    description=f"编码 {code} 为状态类编码，不应作为主要诊断",
                    risk_level=RiskLevel.HIGH_RISK,
                    regulation_reference="DRG/DIP付费下的高套编码认定",
                    suggestion="主要诊断应选择消耗医疗资源最多、对本次住院起主要作用的疾病"
                ))

        return issues

    def check_excessive_treatment(
        self,
        treatment_list: List[str],
        diagnosis_codes: List[str]
    ) -> List[ComplianceIssue]:
        issues = []

        for pattern in self.EXCESSIVE_TREATMENT_PATTERNS:
            matched = sum(1 for t in treatment_list if any(ind in t for ind in pattern["indicators"]))
            if matched >= pattern["threshold"]:
                issues.append(ComplianceIssue(
                    code="C003",
                    category="过度医疗嫌疑",
                    description=f"检测到'{pattern['name']}'模式：{matched}项检查",
                    risk_level=RiskLevel.HIGH_RISK,
                    regulation_reference="医疗机构检查检验结果互认管理办法",
                    suggestion=f"评估患者情况，确认每一项检查的临床必要性"
                ))

        if len(treatment_list) > 20 and len(diagnosis_codes) == 1:
            issues.append(ComplianceIssue(
                code="C004",
                category="诊疗合理性",
                description="单病种患者接受了超过常规数量的诊疗项目",
                risk_level=RiskLevel.WARNING,
                regulation_reference="临床路径管理规范",
                suggestion="确保诊疗项目与诊断相符，避免无关检查"
            ))

        return issues

    def check_prohibited_drug_combinations(
        self,
        drug_list: List[str]
    ) -> List[ComplianceIssue]:
        issues = []
        drug_codes = [d.split()[0] if d else "" for d in drug_list]

        for combo in self.PROHIBITED_COMBINATIONS:
            count = sum(1 for dc in drug_codes if any(c in dc for c in combo["codes"]))
            if count >= 2:
                issues.append(ComplianceIssue(
                    code="C005",
                    category="用药安全",
                    description=f"检测到重复用药：{combo['name']}",
                    risk_level=RiskLevel.VIOLATION,
                    regulation_reference="处方管理办法",
                    suggestion="合并用药需有明确临床指征，否则视为大处方"
                ))

        return issues

    def check_insurance_fly_check(
        self,
        record: Dict,
        inspection_type: InspectionType
    ) -> ComplianceCheckResult:
        issues = []
        diagnosis_codes = record.get("diagnosis_codes", [])
        treatment_list = record.get("treatment_list", [])
        drug_list = record.get("drug_list", [])

        issues.extend(self.check_icd编码(diagnosis_codes))
        issues.extend(self.check_excessive_treatment(treatment_list, diagnosis_codes))
        issues.extend(self.check_prohibited_drug_combinations(drug_list))

        if inspection_type == InspectionType.OUTPATIENT:
            if len(drug_list) > 5:
                issues.append(ComplianceIssue(
                    code="C006",
                    category="大处方监控",
                    description=f"门诊处方包含 {len(drug_list)} 种药品",
                    risk_level=RiskLevel.WARNING,
                    regulation_reference="药品处方集管理规范",
                    suggestion="单张处方药品数不超过5种（中成药不超过2种）"
                ))

        risk_counts = {RiskLevel.SAFE: 0, RiskLevel.WARNING: 0, RiskLevel.HIGH_RISK: 0, RiskLevel.VIOLATION: 0}
        for issue in issues:
            risk_counts[issue.risk_level] += 1

        if risk_counts[RiskLevel.VIOLATION] > 0:
            overall_risk = RiskLevel.VIOLATION
            passed = False
        elif risk_counts[RiskLevel.HIGH_RISK] > 0:
            overall_risk = RiskLevel.HIGH_RISK
            passed = False
        elif risk_counts[RiskLevel.WARNING] > 0:
            overall_risk = RiskLevel.WARNING
            passed = True
        else:
            overall_risk = RiskLevel.SAFE
            passed = True

        compliance_score = max(0, 100 - (risk_counts[RiskLevel.WARNING] * 10) - (risk_counts[RiskLevel.HIGH_RISK] * 25) - (risk_counts[RiskLevel.VIOLATION] * 50))

        recommendations = []
        if not passed:
            recommendations.append("建议在提交前修正以上问题")
        if overall_risk in [RiskLevel.HIGH_RISK, RiskLevel.VIOLATION]:
            recommendations.append("此类问题可能被医保飞检重点关注")

        return ComplianceCheckResult(
            check_id=f"CC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            inspection_type=inspection_type,
            patient_id=record.get("patient_id"),
            overall_risk=overall_risk,
            issues=issues,
            compliance_score=compliance_score,
            recommendations=recommendations,
            passed=passed
        )


def check_medical_record(record: Dict, inspection_type: str = "outpatient") -> Dict:
    """主检查函数"""
    checker = MedicalRecordComplianceChecker()
    ins_type = InspectionType[inspection_type.upper()]

    result = checker.check_insurance_fly_check(record, ins_type)

    return {
        "check_id": result.check_id,
        "timestamp": result.timestamp,
        "inspection_type": result.inspection_type.value,
        "patient_id": result.patient_id,
        "overall_risk": result.overall_risk.value,
        "issues": [
            {
                "code": i.code,
                "category": i.category,
                "description": i.description,
                "risk_level": i.risk_level.value,
                "regulation_reference": i.regulation_reference,
                "suggestion": i.suggestion
            }
            for i in result.issues
        ],
        "compliance_score": result.compliance_score,
        "recommendations": result.recommendations,
        "passed": result.passed
    }


if __name__ == "__main__":
    test_record = {
        "patient_id": "P12345",
        "diagnosis_codes": ["E11", "E11", "I10", "Z95"],
        "treatment_list": ["全腹B超", "胸片", "心电图", "血常规", "尿常规", "肝功能", "肾功能"],
        "drug_list": ["J01DB9 头孢氨苄", "J01DD4 头孢克肟", "N02BE1 对乙酰氨基酚"]
    }

    result = check_medical_record(test_record, "outpatient")
    print(f"检查ID: {result['check_id']}")
    print(f"风险等级: {result['overall_risk']}")
    print(f"合规评分: {result['compliance_score']}")
    print(f"是否通过: {result['passed']}")
    print(f"发现问题: {len(result['issues'])} 个")
    for issue in result['issues']:
        print(f"  - [{issue['risk_level']}] {issue['code']}: {issue['description']}")
        print(f"    建议: {issue['suggestion']}")
