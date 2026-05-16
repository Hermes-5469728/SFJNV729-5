"""跨模块通用工具 · src/shared/utils.py"""
from datetime import datetime, date
from typing import Any, Dict, Optional


def now_iso() -> str:
    """当前时间 ISO 格式字符串"""
    return datetime.utcnow().isoformat() + "Z"


def parse_date(value: Optional[str]) -> Optional[date]:
    """安全解析日期字符串"""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def truncate(text: str, max_len: int = 500) -> str:
    """截断文本到指定长度"""
    return text[:max_len] + ("..." if len(text) > max_len else "")


# ─── 以下为跨模块可复用的业务工具 ───

def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """BMI 计算 · 体重(kg) / 身高(m)²"""
    if height_m <= 0:
        return 0.0
    return round(weight_kg / (height_m ** 2), 1)


def calculate_bsa(weight_kg: float, height_cm: float) -> float:
    """BSA · Mosteller 公式"""
    if weight_kg <= 0 or height_cm <= 0:
        return 0.0
    return round(((height_cm * weight_kg) / 3600) ** 0.5, 2)


def calculate_crcl(age: int, weight_kg: float, scr: float, is_female: bool = False) -> float:
    """CrCl · Cockcroft-Gault"""
    if scr <= 0:
        return 0.0
    crcl = ((140 - age) * weight_kg) / (72 * scr)
    if is_female:
        crcl *= 0.85
    return round(crcl, 1)
