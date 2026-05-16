"""意图契约验证器 - 确保需求传递的完整性和准确性"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, ValidationError, field_validator


class AcceptanceCriteria(BaseModel):
    """验收标准模型"""
    id: str
    description: str
    verification_method: str


class RiskItem(BaseModel):
    """风险项模型"""
    risk: str
    level: str  # high, medium, low
    mitigation: str


class IntentContract(BaseModel):
    """意图契约数据模型"""
    task_id: str
    title: str
    complexity: str  # low, medium, high
    deadline: Optional[str] = None
    author: str
    created_at: str
    status: str = "pending"
    
    # 核心内容
    requirement_description: str
    acceptance_criteria: List[AcceptanceCriteria]
    technical_constraints: str
    related_resources: Dict[str, str]
    risks: List[RiskItem]
    deliverables: List[str]

    @field_validator('complexity')
    def validate_complexity(cls, v):
        if v not in ['low', 'medium', 'high']:
            raise ValueError('complexity must be low, medium, or high')
        return v

    @field_validator('status')
    def validate_status(cls, v):
        if v not in ['pending', 'in_progress', 'review', 'completed']:
            raise ValueError('invalid status')
        return v


def generate_task_id() -> str:
    """生成唯一任务ID"""
    date_str = datetime.now().strftime("%Y%m%d")
    # 这里可以结合计数器生成序列号
    return f"TASK-{date_str}-001"


def validate_contract(contract: dict) -> tuple[bool, str]:
    """验证意图契约的完整性"""
    try:
        IntentContract(**contract)
        
        # 额外的业务规则验证
        if not contract.get('acceptance_criteria') or len(contract['acceptance_criteria']) < 2:
            return False, "验收标准至少需要2条"
        
        if contract.get('complexity') == 'high' and not contract.get('risks'):
            return False, "高复杂度任务必须包含风险评估"
        
        return True, "契约验证通过"
    
    except ValidationError as e:
        return False, f"数据验证失败: {str(e)}"


def format_contract_markdown(contract: IntentContract) -> str:
    """将契约对象格式化为Markdown"""
    md = f"""---
title: "{contract.title}"
task_id: "{contract.task_id}"
complexity: "{contract.complexity}"
deadline: "{contract.deadline or ''}"
author: "{contract.author}"
created_at: "{contract.created_at}"
status: "{contract.status}"
---

# 📋 {contract.title}

## 1. 需求描述

{contract.requirement_description}

## 2. 验收标准

| 编号 | 标准描述 | 验证方式 |
|------|----------|----------|
"""
    for ac in contract.acceptance_criteria:
        md += f"| {ac.id} | {ac.description} | {ac.verification_method} |\n"
    
    md += "\n## 3. 技术约束\n\n"
    md += f"> [!IMPORTANT]\n> {contract.technical_constraints}\n\n"
    
    md += "## 4. 相关资源\n\n"
    md += "| 类型 | 链接/路径 |\n|------|----------|\n"
    for key, value in contract.related_resources.items():
        md += f"| {key} | {value} |\n"
    
    md += "\n## 5. 风险评估\n\n"
    md += "| 风险 | 等级 | 应对策略 |\n|------|------|----------|\n"
    for risk in contract.risks:
        md += f"| {risk.risk} | {risk.level} | {risk.mitigation} |\n"
    
    md += "\n## 6. 交付物清单\n\n"
    for item in contract.deliverables:
        md += f"- [ ] {item}\n"
    
    return md
