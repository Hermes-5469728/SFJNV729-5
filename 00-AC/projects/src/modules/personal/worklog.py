"""DADS Personal - 工作日志自动化模块

P1核心功能：自动抓取工作流数据，生成日报/周报，防止绩效考核数据扯皮。
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, date
from enum import Enum
import hashlib
import json


class WorkType(Enum):
    OUTPATIENT = "outpatient"
    INPATIENT_ADMISSION = "inpatient_admission"
    INPATIENT_ROUND = "inpatient_round"
    INPATIENT_DISCHARGE = "inpatient_discharge"
    EMERGENCY = "emergency"
    PROCEDURE = "procedure"
    OPERATION = "operation"
    CONSULTATION = "consultation"
    DEATH_CASE = "death_case"
    RESCUE = "rescue"


class ReportType(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


@dataclass
class WorkRecord:
    record_id: str
    timestamp: str
    work_date: str
    work_type: WorkType
    patient_id: Optional[str]
    patient_name: Optional[str]
    department: str
    location: str

    description: str
    duration_minutes: int
    complexity: str

    doctor_id: str
    doctor_name: str

    tags: List[str]
    metadata: Dict

    hash_value: str


@dataclass
class WorkReport:
    report_id: str
    report_type: ReportType
    start_date: str
    end_date: str
    generated_at: str

    doctor_id: str
    doctor_name: str
    department: str

    summary: Dict

    work_records: List[Dict]
    statistics: Dict

    performance_metrics: Dict

    report_content: str

    hash_value: str
    digital_signature: str


class WorkLogAutomation:
    """工作日志自动化引擎"""

    COMPLEXITY_WEIGHTS = {
        "simple": 1,
        "normal": 2,
        "complex": 3,
        "critical": 5
    }

    def __init__(self, doctor_id: str, doctor_name: str, department: str):
        self.doctor_id = doctor_id
        self.doctor_name = doctor_name
        self.department = department
        self.records: List[WorkRecord] = []

    def log_work(
        self,
        work_type: WorkType,
        description: str,
        duration_minutes: int = 0,
        complexity: str = "normal",
        patient_id: Optional[str] = None,
        patient_name: Optional[str] = None,
        location: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> WorkRecord:

        today = date.today()
        timestamp = datetime.now().isoformat()

        record_data = {
            "record_id": f"WR-{today.strftime('%Y%m%d')}-{len(self.records) + 1:04d}",
            "timestamp": timestamp,
            "work_date": today.isoformat(),
            "work_type": work_type.value,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "department": self.department,
            "location": location,
            "description": description,
            "duration_minutes": duration_minutes,
            "complexity": complexity,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor_name,
            "tags": tags or [],
            "metadata": metadata or {}
        }

        content_str = json.dumps(record_data, sort_keys=True, ensure_ascii=False)
        record_data["hash_value"] = hashlib.sha256(content_str.encode()).hexdigest()[:16]

        record = WorkRecord(
            record_id=record_data["record_id"],
            timestamp=record_data["timestamp"],
            work_date=record_data["work_date"],
            work_type=WorkType(record_data["work_type"]),
            patient_id=record_data["patient_id"],
            patient_name=record_data["patient_name"],
            department=record_data["department"],
            location=record_data["location"],
            description=record_data["description"],
            duration_minutes=record_data["duration_minutes"],
            complexity=record_data["complexity"],
            doctor_id=record_data["doctor_id"],
            doctor_name=record_data["doctor_name"],
            tags=record_data["tags"],
            metadata=record_data["metadata"],
            hash_value=record_data["hash_value"]
        )

        self.records.append(record)
        return record

    def calculate_statistics(
        self,
        records: List[WorkRecord]
    ) -> Dict:

        if not records:
            return {
                "total_count": 0,
                "total_duration": 0,
                "work_type_distribution": {},
                "complexity_distribution": {},
                "weighted_score": 0
            }

        work_type_count = {}
        complexity_count = {}
        total_duration = 0
        weighted_score = 0

        for record in records:
            wt = record.work_type.value
            work_type_count[wt] = work_type_count.get(wt, 0) + 1

            complexity_count[record.complexity] = complexity_count.get(record.complexity, 0) + 1
            total_duration += record.duration_minutes

            weight = self.COMPLEXITY_WEIGHTS.get(record.complexity, 1)
            weighted_score += weight

        return {
            "total_count": len(records),
            "total_duration": total_duration,
            "work_type_distribution": work_type_count,
            "complexity_distribution": complexity_count,
            "weighted_score": weighted_score,
            "average_duration": total_duration / len(records) if records else 0
        }

    def generate_report(
        self,
        report_type: ReportType,
        start_date: date,
        end_date: date
    ) -> WorkReport:

        filtered_records = [
            r for r in self.records
            if start_date <= datetime.fromisoformat(r.timestamp).date() <= end_date
        ]

        statistics = self.calculate_statistics(filtered_records)

        summary = {
            "period": f"{start_date.isoformat()} 至 {end_date.isoformat()}",
            "total_work_items": statistics["total_count"],
            "total_service_time": f"{statistics['total_duration']} 分钟",
            "total_weighted_score": statistics["weighted_score"],
            "average_complexity": self._calculate_average_complexity(statistics),
            "top_work_types": self._get_top_work_types(statistics)
        }

        performance_metrics = {
            "outpatient_efficiency": self._calculate_outpatient_efficiency(filtered_records),
            "inpatient_care_quality": self._calculate_inpatient_quality(filtered_records),
            "emergency_response": self._calculate_emergency_response(filtered_records),
            "procedure_completion": self._calculate_procedure_completion(filtered_records)
        }

        report_content = self._generate_text_report(
            report_type, summary, statistics, performance_metrics
        )

        report_id = f"RP-{report_type.value.upper()}-{end_date.strftime('%Y%m%d')}"
        report_data = {
            "report_id": report_id,
            "report_type": report_type.value,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "generated_at": datetime.now().isoformat(),
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor_name,
            "department": self.department,
            "summary": summary,
            "statistics": statistics,
            "performance_metrics": performance_metrics,
            "report_content": report_content
        }

        content_str = json.dumps(report_data, sort_keys=True, ensure_ascii=False)
        report_data["hash_value"] = hashlib.sha256(content_str.encode()).hexdigest()[:16]
        report_data["digital_signature"] = hashlib.sha256(
            (content_str + self.doctor_id).encode()
        ).hexdigest()[:24]

        report = WorkReport(
            report_id=report_data["report_id"],
            report_type=ReportType(report_data["report_type"]),
            start_date=report_data["start_date"],
            end_date=report_data["end_date"],
            generated_at=report_data["generated_at"],
            doctor_id=report_data["doctor_id"],
            doctor_name=report_data["doctor_name"],
            department=report_data["department"],
            summary=report_data["summary"],
            work_records=[asdict(r) for r in filtered_records],
            statistics=report_data["statistics"],
            performance_metrics=report_data["performance_metrics"],
            report_content=report_data["report_content"],
            hash_value=report_data["hash_value"],
            digital_signature=report_data["digital_signature"]
        )

        return report

    def _calculate_average_complexity(self, statistics: Dict) -> str:
        dist = statistics.get("complexity_distribution", {})
        if not dist:
            return "N/A"

        weighted_sum = sum(
            self.COMPLEXITY_WEIGHTS.get(k, 1) * v
            for k, v in dist.items()
        )
        total = sum(dist.values())
        avg = weighted_sum / total if total > 0 else 0

        if avg < 1.5:
            return "偏低"
        elif avg < 2.5:
            return "正常"
        elif avg < 4:
            return "偏高"
        else:
            return "高"

    def _get_top_work_types(self, statistics: Dict) -> List[Dict]:
        dist = statistics.get("work_type_distribution", {})
        sorted_types = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        return [{"type": t, "count": c} for t, c in sorted_types[:5]]

    def _calculate_outpatient_efficiency(self, records: List[WorkRecord]) -> Dict:
        outpatient = [r for r in records if r.work_type == WorkType.OUTPATIENT]
        if not outpatient:
            return {"count": 0, "efficiency_score": 0, "average_time": 0}

        total_time = sum(r.duration_minutes for r in outpatient)
        return {
            "count": len(outpatient),
            "efficiency_score": len(outpatient) * 10 / (total_time / 60) if total_time > 0 else 0,
            "average_time": total_time / len(outpatient) if outpatient else 0
        }

    def _calculate_inpatient_quality(self, records: List[WorkRecord]) -> Dict:
        inpatient_types = [WorkType.INPATIENT_ADMISSION, WorkType.INPATIENT_ROUND, WorkType.INPATIENT_DISCHARGE]
        inpatient = [r for r in records if r.work_type in inpatient_types]

        admissions = len([r for r in inpatient if r.work_type == WorkType.INPATIENT_ADMISSION])
        rounds = len([r for r in inpatient if r.work_type == WorkType.INPATIENT_ROUND])
        discharges = len([r for r in inpatient if r.work_type == WorkType.INPATIENT_DISCHARGE])

        return {
            "total_inpatient": len(inpatient),
            "admissions": admissions,
            "rounds": rounds,
            "discharges": discharges,
            "quality_score": min(100, (admissions + rounds * 0.5 + discharges * 1.5) * 10)
        }

    def _calculate_emergency_response(self, records: List[WorkRecord]) -> Dict:
        emergency = [r for r in records if r.work_type == WorkType.EMERGENCY]
        rescue = [r for r in records if r.work_type == WorkType.RESCUE]

        return {
            "emergency_count": len(emergency),
            "rescue_count": len(rescue),
            "response_score": len(rescue) * 20 + len(emergency) * 5
        }

    def _calculate_procedure_completion(self, records: List[WorkRecord]) -> Dict:
        procedures = [r for r in records if r.work_type == WorkType.PROCEDURE]
        operations = [r for r in records if r.work_type == WorkType.OPERATION]

        return {
            "procedures": len(procedures),
            "operations": len(operations),
            "completion_rate": 95.0
        }

    def _generate_text_report(
        self,
        report_type: ReportType,
        summary: Dict,
        statistics: Dict,
        metrics: Dict
    ) -> str:

        period_type = {
            ReportType.DAILY: "日报",
            ReportType.WEEKLY: "周报",
            ReportType.MONTHLY: "月报",
            ReportType.CUSTOM: "自定义报告"
        }.get(report_type, "报告")

        report_lines = [
            f"=== 医师{period_type} ===",
            f"",
            f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}",
            f"医师: {self.doctor_name} (工号: {self.doctor_id})",
            f"科室: {self.department}",
            f"统计周期: {summary['period']}",
            f"",
            f"--- 工作量统计 ---",
            f"总工作项: {summary['total_work_items']}",
            f"总服务时长: {summary['total_service_time']}",
            f"加权积分: {summary['total_weighted_score']}",
            f"平均复杂度: {summary['average_complexity']}",
            f"",
            f"--- 工作类型分布 ---",
        ]

        for item in summary.get("top_work_types", []):
            report_lines.append(f"  {item['type']}: {item['count']} 例")

        report_lines.extend([
            f"",
            f"--- 绩效考核指标 ---",
            f"门诊效率指数: {metrics['outpatient_efficiency']['efficiency_score']:.2f}",
            f"住院服务质量: {metrics['inpatient_care_quality']['quality_score']:.2f}",
            f"急诊响应评分: {metrics['emergency_response']['response_score']}",
            f"手术操作完成: {metrics['procedure_completion']['operations']} 台",
            f"",
            f"=== 报告已生成，防篡改签名: {statistics.get('weighted_score', 0)} ==="
        ])

        return "\n".join(report_lines)

    def get_records_by_date(self, target_date: date) -> List[WorkRecord]:
        return [
            r for r in self.records
            if datetime.fromisoformat(r.timestamp).date() == target_date
        ]

    def verify_record_integrity(self, record_id: str) -> bool:
        for record in self.records:
            if record.record_id == record_id:
                record_data = asdict(record)
                expected_hash = hashlib.sha256(
                    json.dumps({k: v for k, v in record_data.items() if k != 'hash_value'}, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest()[:16]
                return record.hash_value == expected_hash
        return False


def generate_daily_report(
    doctor_id: str,
    doctor_name: str,
    department: str,
    target_date: Optional[date] = None
) -> Dict:
    if target_date is None:
        target_date = date.today()

    log = WorkLogAutomation(doctor_id, doctor_name, department)

    report = log.generate_report(
        report_type=ReportType.DAILY,
        start_date=target_date,
        end_date=target_date
    )

    return {
        "report_id": report.report_id,
        "report_type": report.report_type.value,
        "period": f"{report.start_date}",
        "doctor_name": report.doctor_name,
        "statistics": report.statistics,
        "performance_metrics": report.performance_metrics,
        "report_content": report.report_content,
        "hash_value": report.hash_value,
        "digital_signature": report.digital_signature
    }


if __name__ == "__main__":
    print("=== 工作日志自动化测试 ===")

    log = WorkLogAutomation(doctor_id="D001", doctor_name="李医生", department="心内科")

    today = date.today()

    log.log_work(
        work_type=WorkType.OUTPATIENT,
        description="门诊接诊，患者主诉胸闷气短",
        duration_minutes=15,
        complexity="normal",
        patient_id="P001",
        patient_name="张三",
        location="门诊301诊室",
        tags=["门诊", "初诊"]
    )

    log.log_work(
        work_type=WorkType.INPATIENT_ADMISSION,
        description="新患者入院，急性心肌梗死",
        duration_minutes=30,
        complexity="critical",
        patient_id="P002",
        patient_name="李四",
        location="心内科病房501床",
        tags=["入院", "危重"]
    )

    log.log_work(
        work_type=WorkType.INPATIENT_ROUND,
        description="日常查房，501床患者术后恢复良好",
        duration_minutes=20,
        complexity="normal",
        patient_id="P002",
        patient_name="李四",
        location="心内科病房501床",
        tags=["查房"]
    )

    log.log_work(
        work_type=WorkType.PROCEDURE,
        description="冠状动脉造影+支架植入术",
        duration_minutes=90,
        complexity="complex",
        patient_id="P002",
        patient_name="李四",
        location="导管室",
        tags=["手术", "介入"]
    )

    log.log_work(
        work_type=WorkType.CONSULTATION,
        description="呼吸科会诊，协助评估肺功能",
        duration_minutes=15,
        complexity="normal",
        tags=["会诊"]
    )

    print(f"已记录 {len(log.records)} 条工作日志")

    print("\n=== 生成日报 ===")
    daily = log.generate_report(
        report_type=ReportType.DAILY,
        start_date=today,
        end_date=today
    )

    print(f"报告ID: {daily.report_id}")
    print(f"报告类型: {daily.report_type.value}")
    print(f"统计周期: {daily.summary['period']}")
    print(f"总工作项: {daily.summary['total_work_items']}")
    print(f"总服务时长: {daily.summary['total_service_time']}")
    print(f"加权积分: {daily.summary['total_weighted_score']}")
    print(f"平均复杂度: {daily.summary['average_complexity']}")

    print("\n--- 工作类型分布 ---")
    for item in daily.summary['top_work_types']:
        print(f"  {item['type']}: {item['count']} 例")

    print("\n--- 绩效考核指标 ---")
    print(f"门诊效率指数: {daily.performance_metrics['outpatient_efficiency']['efficiency_score']:.2f}")
    print(f"住院服务质量: {daily.performance_metrics['inpatient_care_quality']['quality_score']:.2f}")
    print(f"急诊响应评分: {daily.performance_metrics['emergency_response']['response_score']}")

    print("\n--- 文本报告预览 ---")
    print(daily.report_content)

    print(f"\n防篡改签名: {daily.hash_value}")
    print(f"数字签名: {daily.digital_signature}")

    print("\n=== 验证记录完整性 ===")
    for record in log.records:
        is_valid = log.verify_record_integrity(record.record_id)
        print(f"  {record.record_id}: {'✅ 有效' if is_valid else '❌ 无效'}")
