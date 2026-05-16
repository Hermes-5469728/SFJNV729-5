"""AC Platform Date Utilities - 日期处理工具模块

提供从文本中提取各类日期格式的功能。
支持格式：ISO (YYYY-MM-DD)、斜杠 (YYYY/MM/DD)、中文 (YYYY年MM月DD日)
"""

import re
from typing import List


class DatePattern:
    """日期正则表达式模式常量类。"""

    ISO_FORMAT: str = r"\d{4}-\d{2}-\d{2}"
    SLASH_FORMAT: str = r"\d{4}/\d{2}/\d{2}"
    CN_FORMAT: str = r"\d{4}年\d{1,2}月\d{1,2}日"

    ALL_PATTERNS: List[str] = [ISO_FORMAT, SLASH_FORMAT, CN_FORMAT]


def extract_dates(text: str) -> List[str]:
    """从文本中提取所有匹配的日期字符串。

    Args:
        text: 输入文本，包含任意日期格式的字符串。

    Returns:
        日期字符串列表（按发现顺序排列，可能包含重复）。

    Supported formats:
        - ISO: YYYY-MM-DD (e.g., 2026-05-11)
        - Slash: YYYY/MM/DD (e.g., 2026/05/11)
        - Chinese: YYYY年MM月DD日 (e.g., 2026年5月11日)

    Example:
        >>> extract_dates("今天是2026-05-11，明天是2026/05/12")
        ["2026-05-11", "2026/05/12"]
    """
    dates: List[str] = []
    for pattern in DatePattern.ALL_PATTERNS:
        matches = re.findall(pattern, text)
        dates.extend(matches)
    return dates


def extract_unique_dates(text: str) -> List[str]:
    """提取不重复的日期列表。

    Args:
        text: 输入文本，包含任意日期格式的字符串。

    Returns:
        去重后的日期字符串列表（按首次出现顺序排列）。

    Example:
        >>> extract_unique_dates("2026-05-11 和 2026-05-11")
        ["2026-05-11"]
    """
    return list(set(extract_dates(text)))
