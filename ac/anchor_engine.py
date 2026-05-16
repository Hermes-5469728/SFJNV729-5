"""AnchorEngine v3 · EAV 结构化比对 + 关键词兜底 — 无生成，硬拦截"""

import json, re
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
ANCHOR_PATH = _PROJECT_ROOT / "00-DataCenter" / "anchor_db.json"

# 人工维护的对立词表（凭常识可确定的直接对立，非推理）
# 每对：(正向词集, 反向词集)
ANTONYM_PAIRS = [
    ({"必须", "需要", "应该", "只能", "只有", "才允许"}, {"不必须", "不需要", "不一定", "不一定要", "也可以", "不用"}),
    ({"严禁", "禁止", "不得", "不准", "不能", "不应"}, {"可以", "允许", "能够", "可用"}),
    ({"DAG", "有向无环图", "无环"}, {"循环", "有环", "环路", "回环"}),
]


class EAVExtractor:
    """确定性 EAV 抽取器，嵌入引擎内部。"""

    @staticmethod
    def _polarity(text: str) -> str:
        negations = [r"不应", r"不需", r"不是", r"不必", r"不要", r"不能", r"不会", r"可以不用", r"并非", r"无需", r"不用", r"不准", r"禁止", r"反对", r"不需要"]
        if any(re.search(p, text) for p in negations):
            return "negative"
        return "positive"

    @staticmethod
    def extract(text: str) -> list[dict]:
        results = []
        pol = EAVExtractor._polarity(text)
        # R1: X的Y是Z
        for m in re.finditer(r"([\u4e00-\u9fffA-Za-z0-9]{2,20})的([\u4e00-\u9fffA-Za-z0-9]{2,20})(?:是|为|属于)([\u4e00-\u9fffA-Za-z0-9\u4e00-\u9fffA-Za-z0-9]{2,100})", text):
            results.append({"entity": m.group(1), "attribute": m.group(2), "value": m.group(3).strip(), "polarity": pol, "rule": "R1"})
        # R2: X是Y的Z / X是Y
        for m in re.finditer(r"([\u4e00-\u9fffA-Za-z0-9]{2,20})(?:是)([\u4e00-\u9fffA-Za-z0-9\u4e00-\u9fff\u4e00-\u9fff\s]{2,80})(?:的)([\u4e00-\u9fffA-Za-z0-9]{2,20})", text):
            results.append({"entity": m.group(1), "attribute": m.group(3), "value": m.group(2).strip()[:80], "polarity": pol, "rule": "R2"})
        for m in re.finditer(r"([\u4e00-\u9fffA-Za-z0-9]{2,20})(?:是)([\u4e00-\u9fffA-Za-z0-9\u4e00-\u9fff\s]{4,60})(?![的])", text):
            if ":\"" not in m.group(0):
                results.append({"entity": m.group(1), "attribute": "定义", "value": m.group(2).strip()[:80], "polarity": pol, "rule": "R2b"})
        # R3: 具备/支持/包含X管理
        for m in re.finditer(r"(?:具备|支持|包含|拥有)([\u4e00-\u9fffA-Za-z0-9]{2,20})管理", text):
            em = text.split(":")[0].strip() if ":" in text else ""
            results.append({"entity": em, "attribute": "管理能力", "value": m.group(1) + "态管理", "polarity": pol, "rule": "R3"})
        # R4: X: Y
        if ":" in text and not text.startswith("http"):
            p = text.split(":", 1)
            if len(p[0].strip()) >= 2 and len(p[1].strip()) >= 4:
                results.append({"entity": p[0].strip(), "attribute": "定义", "value": p[1].strip()[:100], "polarity": pol, "rule": "R4"})
        # R5: 必须/不得/严禁
        for m in re.finditer(r"(?:必须|不得|严禁|应该|需要)([\u4e00-\u9fffA-Za-z0-9\u4e00-\u9fffA-Za-z\s/]{4,80})", text):
            results.append({"entity": text.split(":")[0].strip() if ":" in text else "系统", "attribute": "规范", "value": m.group(0).strip()[:100], "polarity": pol, "rule": "R5"})
        # R6: 将X存入Y
        for m in re.finditer(r"将([\u4e00-\u9fffA-Za-z0-9\u4e00-\u9fff、，/\s]{4,80})(?:存入|写入|记录到|存储到)([\u4e00-\u9fffA-Za-z0-9]{2,40})", text):
            results.append({"entity": m.group(2), "attribute": "存储内容", "value": m.group(1).strip()[:100], "polarity": pol, "rule": "R6"})
        # R7: X全部Y
        for m in re.finditer(r"([\u4e00-\u9fffA-Za-z0-9\u4e00-\u9fff、/]{4,60})(?:全部|均|统一)([\u4e00-\u9fffA-Za-z0-9]{2,40})", text):
            results.append({"entity": m.group(1).strip().split("的")[-1] if "的" in m.group(1) else m.group(1).strip(), "attribute": "操作方式", "value": m.group(0).strip()[:100], "polarity": pol, "rule": "R7"})
        # R8: 使用X（来）Y
        for m in re.finditer(r"(?:使用|用|通过|利用)([\u4e00-\u9fffA-Za-z0-9\u4e00-\u9fff\s]{4,60})(?:来|以|)([\u4e00-\u9fffA-Za-z0-9\u4e00-\u9fff]{4,60})", text):
            results.append({"entity": m.group(1).strip()[:30], "attribute": "实现方式", "value": m.group(2).strip()[:60], "polarity": pol, "rule": "R8"})

        seen = set()
        unique = []
        for r in results:
            key = (r["entity"][:15], r["attribute"][:8])
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique


class AnchorEngine:
    """独立比对引擎 v3。EAV 结构化比对 + 关键词兜底。"""

    def __init__(self, anchor_path: str | Path = ANCHOR_PATH):
        self.anchors = []
        self._anchor_eav: list[dict] = []
        if Path(anchor_path).exists():
            self.anchors = json.loads(Path(anchor_path).read_text(encoding="utf-8"))
            # 预抽取锚点的 EAV
            for a in self.anchors:
                text = a.get("topic", "") + " " + a.get("verified_truth", "")
                eavs = EAVExtractor.extract(text)
                for e in eavs:
                    e["source_topic"] = a.get("topic", "")[:40]
                    self._anchor_eav.append(e)
        # n-gram 索引（兜底）
        self._index = {}
        for a in self.anchors:
            text = a.get("topic", "") + " " + a.get("verified_truth", "")[:300]
            chars = re.findall(r"[\u4e00-\u9fff]", text)
            for size in range(2, 6):
                for i in range(len(chars) - size + 1):
                    g = "".join(chars[i:i+size])
                    self._index.setdefault(g, []).append(a.get("topic", ""))
            for w in re.findall(r"[a-zA-Z]{3,}", text):
                self._index.setdefault(w.lower(), []).append(a.get("topic", ""))

    def count(self) -> int:
        return len(self.anchors)

    def detect_conflict(self, title: str, content: str) -> dict:
        # 1. EAV 抽取待验文本
        input_eav = EAVExtractor.extract(title + " " + content)

        # 2. EAV 结构化比对
        factual_conflicts = []
        for ie in input_eav:
            for ae in self._anchor_eav:
                if ie["entity"][:10] and ae["entity"][:10] and ie["entity"][:10] == ae["entity"][:10]:
                    # 同实体
                    if ie["attribute"][:6] and ae["attribute"][:6] and ie["attribute"][:6] == ae["attribute"][:6]:
                        # 同属性 → 检查值是否相反
                        if ie["polarity"] != ae["polarity"]:
                            # 值级重叠检查：避免"规范-需要13态" vs "规范-不能自研"误报
                            iv = ie.get("value", "")[:20]
                            av = ae.get("value", "")[:20]
                            value_overlap = len(set(iv) & set(av)) > 3 if (iv and av) else False
                            if value_overlap or ie["polarity"] == "negative":
                                factual_conflicts.append({
                                    "anchor_topic": ae.get("source_topic", ""),
                                    "entity": ie["entity"],
                                    "attribute": ie["attribute"],
                                    "input_value": iv,
                                    "anchor_value": av,
                                    "confidence": 0.8 if value_overlap else 0.5,
                                })

        # 3. n-gram 兜底（主题覆盖检测）
        chars = re.findall(r"[\u4e00-\u9fff]", title + " " + content)
        input_grams = set()
        for size in range(2, 6):
            for i in range(len(chars) - size + 1):
                input_grams.add("".join(chars[i:i+size]))
        for w in re.findall(r"[a-zA-Z]{3,}", title + " " + content):
            input_grams.add(w.lower())

        matched_topics = {}
        for gram in input_grams:
            if gram in self._index:
                for t in self._index[gram]:
                    matched_topics[t] = matched_topics.get(t, 0) + 1
        effective_hits = {t: c for t, c in matched_topics.items() if c >= 3}
        covered = len(effective_hits) > 0

        all_conflicts = list(factual_conflicts)
        has_factual = len(all_conflicts) > 0

        # 4. 对立词表检测（人工维护的常识性对立）
        antonym_conflicts = []
        for pos_set, neg_set in ANTONYM_PAIRS:
            input_has_pos = any(w in content for w in pos_set)
            input_has_neg = any(w in content for w in neg_set)
            if not (input_has_pos or input_has_neg):
                continue
            # 检查锚点中是否存在对立方的关键词
            for anchor_topic in effective_hits:
                for a in self.anchors:
                    atext = (a.get("topic", "") + " " + a.get("verified_truth", ""))
                    if input_has_pos and any(w in atext for w in neg_set):
                        # 检查输入与锚点的内容是否有实质重叠（避免不同规则误触）
                        overlap = len(set(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", content)) & set(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", atext)))
                        if overlap >= 1:
                            antonym_conflicts.append({
                                "anchor_topic": anchor_topic[:40],
                                "anchor_truth": a.get("verified_truth", "")[:80],
                                "confidence": 0.7,
                                "trigger": "antonym:pos_vs_neg",
                            })
                            break
                    if input_has_neg and any(w in atext for w in pos_set):
                        overlap = len(set(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", content)) & set(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", atext)))
                        if overlap >= 1:
                            antonym_conflicts.append({
                                "anchor_topic": anchor_topic[:40],
                                "anchor_truth": a.get("verified_truth", "")[:80],
                                "confidence": 0.7,
                                "trigger": "antonym:neg_vs_pos",
                            })
                            break

        all_conflicts = factual_conflicts + antonym_conflicts

        # 5. 显式否定兜底：输入中包含"不应/不能/不需要"等否定词且主题覆盖 → 事实矛盾
        negation_keywords = r"(?:不应|不能|不需要|不是|不必|不要|不会|可以不用|并非|无需|不用|不准|禁止|反对)"
        if covered and not any(c.get("trigger","").startswith("antonym") for c in all_conflicts):
            if re.search(negation_keywords, content):
                all_conflicts.append({
                    "anchor_topic": (list(effective_hits.keys()) + ["unknown"])[0][:40],
                    "confidence": 0.5,
                    "trigger": "negation_keyword",
                })
        has_factual = len(all_conflicts) > 0

        return {
            "conflicts": all_conflicts[:5],
            "has_conflict": has_factual,
            "conflict_type": "factual_contradiction" if has_factual else ("topic_overlap" if covered else "none"),
            "covered_by_anchors": covered,
            "score": 0.0 if has_factual else (0.5 if not covered else 0.9),
            "eav_matched": len(input_eav),
            "reason": f"{len(factual_conflicts)} factual conflict(s)" if has_factual else ("no anchor coverage" if not covered else "topic overlap, no contradiction"),
        }


_engine: AnchorEngine | None = None


def get_engine() -> AnchorEngine:
    global _engine
    if _engine is None:
        _engine = AnchorEngine()
    return _engine


if __name__ == "__main__":
    e = get_engine()
    print(f"anchors: {e.count()}, anchor_eav_tuples: {len(e._anchor_eav)}")

    tests = [
        ("地球形状", "地球是平的"),
        ("UBI定义", "UBI是全民基本收入"),
        ("UBI否定", "UBI不是全民分红而是维稳费"),
        ("AGI定义", "AGI指在几乎所有经济工作上都能胜过人类的AI"),
        ("状态机", "状态机管理具备13态管理"),
        ("EAV样本", "使用状态模式定义状态跳转条件"),
        ("LLM日志", "每次LLM调用的Prompt/输出/Token/耗时全部存入数据库"),
    ]
    for t, c in tests:
        r = e.detect_conflict(t, c)
        print(f"  [{r['conflict_type']:25s}] eav={r['eav_matched']} score={r['score']}  {t}")

    # 全库回归
    import sqlite3
    db = Path("{USER_HOME}/ac/ac_platform.db")
    conn = sqlite3.connect(str(db))
    rows = conn.execute("SELECT rowid, title, content FROM ac_truth ORDER BY rowid").fetchall()
    conn.close()
    results = {"factual": 0, "overlap": 0, "none": 0}
    for rowid, title, content in rows:
        r = e.detect_conflict(title, content)
        results[r["conflict_type"]] += 1
    print(f"\n全库回归: factual={results['factual']} topic_overlap={results['overlap']} none={results['none']}")
