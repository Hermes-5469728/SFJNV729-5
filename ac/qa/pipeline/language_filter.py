import re
from typing import Tuple
from ac.qa.config import QA_CONFIG


ZH_CHARS = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")
EN_CHARS = re.compile(r"[a-zA-Z]")
JA_KANA = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")


def detect_language(text: str) -> Tuple[str, float]:
    total = len(text.strip())
    if total == 0:
        return ("unknown", 0.0)

    zh_count = len(ZH_CHARS.findall(text))
    en_count = len(EN_CHARS.findall(text))
    ja_count = len(JA_KANA.findall(text))

    zh_ratio = zh_count / max(total, 1)
    en_ratio = en_count / max(total, 1)
    ja_ratio = ja_count / max(total, 1)

    if zh_ratio > en_ratio and zh_ratio > ja_ratio:
        return ("zh", zh_ratio)
    elif en_ratio > zh_ratio and en_ratio > ja_ratio:
        return ("en", en_ratio)
    elif ja_ratio > 0.05:
        return ("ja", ja_ratio)
    return ("zh" if zh_ratio > 0.1 else "en", max(zh_ratio, en_ratio))


def is_target_language(text: str, target: str = "zh") -> Tuple[bool, float]:
    lang, confidence = detect_language(text)
    cfg = QA_CONFIG["pipeline"]["language_filter"]
    if lang == target:
        return (confidence >= cfg["confidence_threshold"], confidence)
    return (False, confidence)
