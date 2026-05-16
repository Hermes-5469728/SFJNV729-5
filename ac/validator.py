"""TruthValidator · 真值三级验证器 — 入库前强制校验"""

import os
import re
import json
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

AC_DIR = Path(__file__).resolve().parent
DB_PATH = AC_DIR / "ac_platform.db"
ANCHOR_PATH = Path(os.environ.get("AC_ANCHOR_PATH", str(AC_DIR / "anchor_db.json")))


@dataclass
class ValidationResult:
    passed: bool
    level: str  # L0 / L2 / L5
    checks: list[dict] = field(default_factory=list)
    score: float = 1.0  # 0-1, 1=完全可信


class TruthValidator:
    """三级验证器"""

    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)

    # ── L0: 语法验证 ─────────────────────────────

    def check_l0(self, title: str, content: str) -> list[dict]:
        findings = []
        # 1. 断言是否可证伪
        unfalsifiable_patterns = [
            r"永远[不]?会", r"从来[不]?会", r"所有人[都]?", r"没有任何",
            r"一定[会不]", r"绝对[不]?", r"根本[不]?",
        ]
        for pat in unfalsifiable_patterns:
            if re.search(pat, content):
                findings.append({
                    "check": "L0-1:可证伪性",
                    "status": "WARN",
                    "detail": f"包含绝对化表述: {pat}",
                })
                break

        # 2. 数字断言是否标注来源
        number_pattern = r"\d+[.%万亿千百]"
        has_number = bool(re.search(number_pattern, content))
        has_source = "来源" in content or "数据" in content or "报告" in content
        if has_number and not has_source:
            findings.append({
                "check": "L0-2:数字来源",
                "status": "WARN",
                "detail": "包含数字断言但未标注出处",
            })

        # 3. 是否有明确的主谓结构
        if len(content.split("。")) < 2 and len(content) < 50:
            findings.append({
                "check": "L0-3:结构完整性",
                "status": "WARN",
                "detail": "内容过短或结构不完整",
            })

        if not findings:
            findings.append({"check": "L0", "status": "PASS", "detail": "语法验证通过"})
        return findings

    # ── L2: 事实一致性验证 ────────────────────────

    def _extract_concepts(self, text: str) -> set:
        """提取关键概念（中文词组 + 英文单词）"""
        chinese = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
        english = re.findall(r'[a-zA-Z]{3,}', text)
        return set(chinese + english)

    def _extract_numbers(self, text: str) -> list:
        """提取数字断言"""
        return re.findall(r'\d+(?:\.\d+)?[.%万亿千百]?', text)

    def _has_negation(self, text: str) -> bool:
        return any(w in text for w in ["不", "不是", "非", "没有", "从未", "错误"])

    def _load_anchor_db(self) -> list[dict]:
        """加载锚点库"""
        try:
            p = Path(str(ANCHOR_PATH))
            if p.exists():
                with open(p, encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("anchors", [])
        except Exception:
            pass
        return []

    def check_l2(self, title: str, content: str) -> list[dict]:
        findings = []
        concepts = self._extract_concepts(content)
        numbers = self._extract_numbers(content)
        has_neg = self._has_negation(content)

        # ── 0. 字符集相似度（兜底，应对分词不一致的问题） ──
        content_chars = set(content)
        # ── 1. 与锚点库比对 ──
        anchors = self._load_anchor_db()
        for a in anchors:
            anchor_concepts = self._extract_concepts(a["verified_truth"])
            shared = concepts & anchor_concepts
            anchor_chars = set(a["verified_truth"])
            char_overlap = len(content_chars & anchor_chars) / max(len(content_chars | anchor_chars), 1)
            if len(shared) >= 1 or char_overlap > 0.3:
                # 主题重叠 → 检查是否矛盾
                anchor_has_neg = self._has_negation(a["verified_truth"])
                if has_neg != anchor_has_neg:
                    # 极性相反 → 冲突
                    findings.append({
                        "check": "L2-1:锚点冲突",
                        "status": "FAIL",
                        "detail": f"与锚点「{a['topic']}」极性相反: 输入含否定但锚点肯定（或反之）",
                    })
                # 检查数字冲突
                anchor_nums = self._extract_numbers(a["verified_truth"])
                if numbers and anchor_nums:
                    if set(numbers) != set(anchor_nums):
                        findings.append({
                            "check": "L2-2:数字冲突",
                            "status": "FAIL",
                            "detail": f"数字不匹配: 输入 {numbers} vs 锚点 {anchor_nums}",
                        })

        # ── 2. 与已有真值库比对 ──
        try:
            conn = sqlite3.connect(str(self.db_path))
            existing = conn.execute(
                "SELECT title, content FROM ac_truth WHERE verified=1"
            ).fetchall()
            for et, ec in existing:
                ec_concepts = self._extract_concepts(ec)
                shared = concepts & ec_concepts
                if len(shared) >= 3:
                    # 主题显著重叠 → 检查是否重复或矛盾
                    sim = len(shared) / max(len(concepts | ec_concepts), 1)
                    if sim > 0.7:
                        findings.append({
                            "check": "L2-3:重复内容",
                            "status": "FAIL",
                            "detail": f"与已有真值「{et}」相似度{sim:.0%}，疑似重复",
                        })
                    ec_neg = self._has_negation(ec)
                    if has_neg != ec_neg:
                        findings.append({
                            "check": "L2-4:真值矛盾",
                            "status": "FAIL",
                            "detail": f"与已有真值「{et}」结论矛盾",
                        })
            conn.close()
        except Exception:
            pass

        if not findings:
            findings.append({
                "check": "L2",
                "status": "PASS",
                "detail": "事实一致性验证通过",
            })
        return findings

    # ── L5: 源头验证 ─────────────────────────────

    def check_l5(self, title: str, content: str) -> list[dict]:
        findings = []
        has_url = bool(re.search(r"https?://", content))
        has_source_tag = "来源" in content or "出处" in content
        if has_url or has_source_tag:
            findings.append({
                "check": "L5-1:出处可溯",
                "status": "PASS",
                "detail": "已标注来源",
            })
        else:
            number_pattern = r"\d+[.%万亿千百]"
            if re.search(number_pattern, content):
                findings.append({
                    "check": "L5-1:出处可溯",
                    "status": "FAIL",
                    "detail": "包含数字断言但无来源，标记为假设",
                })
            else:
                findings.append({
                    "check": "L5-1:出处可溯",
                    "status": "WARN",
                    "detail": "无来源标注，建议补充",
                })
        return findings

    # ── 组合验证 ─────────────────────────────────

    def validate(self, title: str, content: str) -> ValidationResult:
        l0 = self.check_l0(title, content)
        l2 = self.check_l2(title, content)
        l5 = self.check_l5(title, content)
        all_checks = l0 + l2 + l5

        # 算分
        fails = sum(1 for c in all_checks if c["status"] == "FAIL")
        warns = sum(1 for c in all_checks if c["status"] == "WARN")
        score = max(0.0, 1.0 - fails * 0.4 - warns * 0.15)

        return ValidationResult(
            passed=fails == 0,
            level="L5" if score >= 0.85 else "L2" if score >= 0.6 else "L0",
            checks=all_checks,
            score=score,
        )


# ── 快捷入口 ─────────────────────────────────────

_validator: TruthValidator | None = None


def get_validator() -> TruthValidator:
    global _validator
    if _validator is None:
        _validator = TruthValidator()
    return _validator


def validate_truth(title: str, content: str) -> ValidationResult:
    return get_validator().validate(title, content)
