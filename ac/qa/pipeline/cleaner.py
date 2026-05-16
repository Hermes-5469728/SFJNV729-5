import re
import unicodedata
from ac.qa.config import QA_CONFIG


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"&#\d+;", " ", text)
    return text


def normalize_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def collapse_whitespace(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = text.strip()
    return text


def strip_ad_tracking(text: str) -> str:
    AD_KEYWORDS = [
        "广告", "推广", "联系微信", "联系电话",
        "阅读原文", "点击原文", "关注公众号",
    ]
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        if any(kw in line for kw in AD_KEYWORDS):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def clean(text: str) -> str:
    cfg = QA_CONFIG["pipeline"]["cleaner"]
    if cfg["strip_html"]:
        text = strip_html(text)
    if cfg["normalize_unicode"]:
        text = normalize_unicode(text)
    text = strip_ad_tracking(text)
    if cfg["collapse_whitespace"]:
        text = collapse_whitespace(text)
    return text


def is_valid_length(text: str) -> bool:
    cfg = QA_CONFIG["pipeline"]["cleaner"]
    return cfg["min_text_length"] <= len(text) <= cfg["max_text_length"]
