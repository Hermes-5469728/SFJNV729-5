"""DADS Medical - 临床诊断支持模块

提供急性白血病等血液疾病的诊断决策支持功能。
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SeverityLevel(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class LabResult:
    name: str
    value: float
    unit: str
    reference_range: Tuple[float, float]


@dataclass
class DiagnosisResult:
    disease: str
    confidence: float
    severity: SeverityLevel
    findings: List[str]
    recommendations: List[str]
    differential_diagnosis: List[Dict]


class BloodCancerDiagnoser:
    """血液肿瘤诊断器"""

    def __init__(self):
        self.aml_markers = ["CD13", "CD33", "MPO", "CD117"]
        self.all_markers_b = ["CD19", "CD20", "CD10", "CD22"]
        self.all_markers_t = ["CD3", "CD7", "CD2", "CD5"]

    def diagnose(
        self,
        bone_marrow_blast: Optional[float] = None,
        peripheral_blast: Optional[float] = None,
        auer_rods: bool = False,
        immunophenotyping: Optional[List[str]] = None,
        symptoms: Optional[List[str]] = None,
    ) -> DiagnosisResult:
        findings = []
        recommendations = []

        if bone_marrow_blast is not None:
            findings.append(f"骨髓原始细胞: {bone_marrow_blast}%")

        if peripheral_blast is not None:
            findings.append(f"外周血原始细胞: {peripheral_blast}%")

        if auer_rods:
            findings.append("Auer小体阳性")

        if immunophenotyping:
            findings.append(f"免疫表型: {', '.join(immunophenotyping)}")

        if symptoms:
            findings.append(f"症状: {', '.join(symptoms)}")

        if bone_marrow_blast is not None and bone_marrow_blast >= 20:
            if auer_rods or any(m in (immunophenotyping or []) for m in self.aml_markers):
                disease = "急性髓系白血病 (AML)"
                severity = SeverityLevel.CRITICAL
                recommendations.extend([
                    "立即进行诱导缓解治疗",
                    "完善细胞遗传学检查",
                    "评估造血干细胞移植可行性"
                ])
            elif any(m in (immunophenotyping or []) for m in self.all_markers_b + self.all_markers_t):
                disease = "急性淋巴细胞白血病 (ALL)"
                severity = SeverityLevel.CRITICAL
                recommendations.extend([
                    "立即进行VP/DVLP方案诱导",
                    "评估CNS预防治疗",
                    "考虑CAR-T或移植"
                ])
            else:
                disease = "急性白血病 (AL - 类型待定)"
                severity = SeverityLevel.CRITICAL
                recommendations.append("进一步完善免疫表型和遗传学检查")
        elif bone_marrow_blast is not None and 5 <= bone_marrow_blast < 20:
            disease = "骨髓增生异常综合征 (MDS)"
            severity = SeverityLevel.WARNING
            recommendations.extend([
                "定期监测血常规",
                "评估去铁治疗",
                "注意感染预防"
            ])
        else:
            disease = "暂不支持当前数据的明确诊断"
            severity = SeverityLevel.NORMAL
            recommendations.append("提供更多信息以支持诊断")

        return DiagnosisResult(
            disease=disease,
            confidence=0.85 if bone_marrow_blast else 0.5,
            severity=severity,
            findings=findings,
            recommendations=recommendations,
            differential_diagnosis=[]
        )


def diagnose_leukemia(
    lab_results: List[LabResult],
    clinical_info: Dict
) -> Dict:
    """主诊断函数"""
    diagnoser = BloodCancerDiagnoser()

    bone_marrow_blast = clinical_info.get("bone_marrow_blast")
    peripheral_blast = clinical_info.get("peripheral_blast")
    auer_rods = clinical_info.get("auer_rods", False)
    immunophenotyping = clinical_info.get("immunophenotyping", [])
    symptoms = clinical_info.get("symptoms", [])

    result = diagnoser.diagnose(
        bone_marrow_blast=bone_marrow_blast,
        peripheral_blast=peripheral_blast,
        auer_rods=auer_rods,
        immunophenotyping=immunophenotyping,
        symptoms=symptoms
    )

    return {
        "disease": result.disease,
        "confidence": result.confidence,
        "severity": result.severity.value,
        "findings": result.findings,
        "recommendations": result.recommendations,
        "differential_diagnosis": result.differential_diagnosis
    }


if __name__ == "__main__":
    test_clinical_info = {
        "bone_marrow_blast": 75,
        "auer_rods": True,
        "immunophenotyping": ["CD13", "CD33", "MPO", "CD34"],
        "symptoms": ["发热", "贫血", "胸骨压痛"]
    }

    result = diagnose_leukemia([], test_clinical_info)
    print(f"诊断结果: {result['disease']}")
    print(f"严重程度: {result['severity']}")
    print(f"置信度: {result['confidence']}")
    print(f"发现: {result['findings']}")
    print(f"建议: {result['recommendations']}")
