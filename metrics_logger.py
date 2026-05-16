"""
元认知校准系统 - 指标记录器
记录每次校验的偏差率数据，用于计算系统可信度评分
"""

import csv
import json
from datetime import datetime
from typing import List, Dict, Optional
from anchor_schema import MetricsRecord


class MetricsLogger:
    """指标记录器 - 记录偏差率和系统性能"""
    
    def __init__(self, csv_path: str = "metrics.csv", json_path: str = "metrics_summary.json"):
        self.csv_path = csv_path
        self.json_path = json_path
        self._ensure_csv_exists()
    
    def _ensure_csv_exists(self):
        """确保CSV文件存在，不存在则创建并写入表头"""
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                # 文件已存在，检查表头
                header = f.readline()
                if not header.startswith("timestamp"):
                    # 表头不正确，重新创建
                    self._create_csv()
        except FileNotFoundError:
            # 文件不存在，创建新文件
            self._create_csv()
    
    def _create_csv(self):
        """创建CSV文件并写入表头"""
        with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "question_type",
                "triggered_anchor",
                "initial_deviation_rate",
                "rewrote",
                "final_deviation_rate",
                "query",
                "anchor_topic"
            ])
    
    def log_record(self, record: MetricsRecord):
        """记录一条指标数据"""
        with open(self.csv_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                record.timestamp,
                record.question_type,
                str(record.triggered_anchor),
                record.initial_deviation_rate,
                str(record.rewrote),
                record.final_deviation_rate or "",
                record.query[:100],
                record.anchor_topic or ""
            ])
    
    def get_summary(self) -> Dict:
        """生成系统可信度评分摘要"""
        records = self._load_all_records()
        
        if not records:
            return {
                "total_records": 0,
                "system_trust_score": 0.0,
                "avg_deviation_rate": 0.0,
                "rewrite_rate": 0.0,
                "anchor_trigger_rate": 0.0,
                "last_updated": datetime.now().isoformat()
            }
        
        total = len(records)
        triggered = sum(1 for r in records if r.triggered_anchor)
        rewrote = sum(1 for r in records if r.rewrote)
        avg_deviation = sum(r.initial_deviation_rate for r in records) / total
        
        # 计算系统可信度评分
        # 评分公式: (1 - 平均偏差率) * (1 + 重写修正率) * (锚点触发覆盖率)
        rewrite_correction = 1.0 + (rewrote / max(1, triggered)) * 0.3 if triggered > 0 else 1.0
        anchor_coverage = triggered / total if total > 0 else 0.0
        trust_score = (1.0 - avg_deviation) * rewrite_correction * anchor_coverage
        
        summary = {
            "total_records": total,
            "system_trust_score": round(min(1.0, max(0.0, trust_score)), 4),
            "avg_deviation_rate": round(avg_deviation, 4),
            "rewrite_rate": round(rewrote / total, 4) if total > 0 else 0.0,
            "anchor_trigger_rate": round(anchor_coverage, 4),
            "last_updated": datetime.now().isoformat(),
            "breakdown": {
                "total_records": total,
                "triggered_anchors": triggered,
                "rewrote_count": rewrote,
                "avg_initial_deviation": round(avg_deviation * 100, 2),
                "avg_final_deviation": round(
                    sum(r.final_deviation_rate or r.initial_deviation_rate for r in records) / total * 100,
                    2
                ) if total > 0 else 0.0
            }
        }
        
        # 保存摘要到JSON文件
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        return summary
    
    def _load_all_records(self) -> List[MetricsRecord]:
        """加载所有记录"""
        records = []
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    record = MetricsRecord(
                        timestamp=row['timestamp'],
                        question_type=row['question_type'],
                        triggered_anchor=row['triggered_anchor'].lower() == 'true',
                        initial_deviation_rate=float(row['initial_deviation_rate']),
                        rewrote=row['rewrote'].lower() == 'true',
                        final_deviation_rate=float(row['final_deviation_rate']) if row['final_deviation_rate'] else None,
                        query=row['query'],
                        anchor_topic=row['anchor_topic']
                    )
                    records.append(record)
        except Exception as e:
            print(f"⚠️ 加载记录失败: {e}")
        
        return records
    
    def print_summary(self):
        """打印系统可信度评分"""
        summary = self.get_summary()
        
        print("=" * 50)
        print("    🧠 元认知校准系统 - 可信度评分报告")
        print("=" * 50)
        print(f"系统可信度评分: {summary['system_trust_score']:.2%}")
        print(f"平均偏差率: {summary['avg_deviation_rate']:.2%}")
        print(f"重写率: {summary['rewrite_rate']:.2%}")
        print(f"锚点触发率: {summary['anchor_trigger_rate']:.2%}")
        print(f"总记录数: {summary['total_records']}")
        print(f"最后更新: {summary['last_updated']}")
        print("=" * 50)


# 测试代码
if __name__ == "__main__":
    logger = MetricsLogger()
    
    # 测试记录
    test_record = MetricsRecord(
        timestamp=datetime.now().isoformat(),
        question_type="definition",
        triggered_anchor=True,
        initial_deviation_rate=0.15,
        rewrote=False,
        query="什么是AGI?",
        anchor_topic="AGI定义"
    )
    
    logger.log_record(test_record)
    logger.print_summary()