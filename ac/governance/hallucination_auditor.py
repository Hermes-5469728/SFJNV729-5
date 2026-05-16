"""
HallucinationAuditor v1 · 运行时幻觉检测引擎
治理层可插拔检查器，在 LLM 输出后逐句审计。
集成位置：governance/pipeline.py → semantic check 之后
"""

from typing import Any
import re


class HallucinationAuditor:
    """运行时幻觉检测引擎"""

    LOW_CONFIDENCE_MARKERS: list[str] = [
        "可能", "也许", "或许", "大概", "大约",
        "通常", "一般认为", "据推测", "有可能",
        "不一定", "可能是", "似乎是", "看上去",
        "某种程度上", "在某种程度上",
    ]

    NO_CITATION_MARKERS: list[str] = [
        "研究表明", "研究显示", "据文献报道",
        "临床实践表明", "有研究指出",
        "据统计", "调查显示",
    ]

    HALLUCINATION_TRIGGERS: list[str] = [
        "没有已知的", "目前没有", "未见报道",
        "安全联合使用", "可以安全使用",
        "没有相互作用", "无相互作用",
        "常规剂量即可",
    ]

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold

    def audit(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """逐句审计，返回结构化审计结果"""
        sentences = self._split_sentences(text)
        flagged = []
        detail = []

        for idx, sent in enumerate(sentences):
            sent_clean = sent.strip()
            if not sent_clean:
                continue

            flags = []
            reasons = []

            # 规则1：低置信度表述
            if any(m in sent_clean for m in self.LOW_CONFIDENCE_MARKERS):
                flags.append("LOW_CONFIDENCE")
                reasons.append("包含不确定表述")

            # 规则2：缺少引用来源（有结论性断言但无引用标记）
            if self._has_assertion_without_citation(sent_clean):
                flags.append("NO_CITATION")
                reasons.append("结论性断言无引用来源")

            # 规则3：疑似幻觉模式（临床安全相关的危险断言）
            if any(m in sent_clean for m in self.HALLUCINATION_TRIGGERS):
                flags.append("HALLUCINATION")
                reasons.append("匹配已知幻觉模式")

            # 规则4：数字/剂量无来源
            if self._has_unverified_number(sent_clean):
                if "NO_CITATION" not in flags:
                    flags.append("NO_CITATION")
                    reasons.append("具体数字/剂量无引用来源")

            if flags:
                flagged.append({
                    "sentence": sent_clean,
                    "index": idx,
                    "flags": flags,
                    "flag": flags[0],
                    "reason": "; ".join(reasons),
                })

            detail.append({
                "sentence": sent_clean,
                "index": idx,
                "flagged": len(flags) > 0,
                "flags": flags,
            })

        total = len(sentences)
        flagged_count = len(flagged)
        score = 1.0 - (flagged_count / max(total, 1))
        passed = score >= self.threshold

        return {
            "audited": True,
            "passed": passed,
            "score": round(score, 2),
            "threshold": self.threshold,
            "total_sentences": total,
            "flagged_count": flagged_count,
            "flagged": flagged,
            "detail": detail,
        }

    def _split_sentences(self, text: str) -> list[str]:
        """分句"""
        raw = re.split(r'[。！？\n]', text)
        return [s.strip() for s in raw if s.strip()]

    def _has_assertion_without_citation(self, sent: str) -> bool:
        """检查是否有结论性断言但缺引用"""
        assertion_markers = [
            "是安全的", "有效", "无效", "禁忌",
            "建议", "推荐", "应该", "必须",
            "会导致", "引起", "造成",
        ]
        citation_markers = [
            "研究", "文献", "报道", "指南",
            "试验", "分析", "数据显示",
            "[1]", "[2]", "[3]", "[4]", "[5]",
        ]
        has_assertion = any(m in sent for m in assertion_markers)
        has_citation = any(m in sent for m in citation_markers)
        return has_assertion and not has_citation

    def _has_unverified_number(self, sent: str) -> bool:
        """检查是否有数字/剂量但无引用"""
        has_number = bool(re.search(r'\d+', sent))
        if not has_number:
            return False
        citation_markers = [
            "研究", "文献", "报道", "指南", "指南推荐",
            "试验", "数据显示",
            "[1]", "[2]", "[3]", "[4]", "[5]",
        ]
        has_citation = any(m in sent for m in citation_markers)
        return has_number and not has_citation
