"""EAV Extractor · 结构化断言抽取器 — 规则驱动，非LLM"""

import re, json
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
EAV_SAMPLES_PATH = _PROJECT_ROOT / "00-DataCenter" / "anchor_eav.json"


class EAVExtractor:
    """EAV 抽取器。确定性规则，不具备生成能力。"""

    def __init__(self, sample_path: str | Path = EAV_SAMPLES_PATH):
        self.patterns: list[dict] = []
        if Path(sample_path).exists():
            samples = json.loads(Path(sample_path).read_text(encoding="utf-8"))
            # 从标注样本中学习规则
            for s in samples:
                text = s.get("source_text", "")
                if not text:
                    continue
                self.patterns.append({
                    "entity": s.get("entity", ""),
                    "attribute": s.get("attribute", ""),
                    "value": s.get("value", ""),
                    "polarity": s.get("polarity", "positive"),
                    "text": text,
                })

    def extract(self, text: str) -> list[dict]:
        """从文本中抽取 EAV 三元组。"""
        results = []

        # 规则1: X的Y是Z
        for m in re.finditer(r"([\u4e00-\u9fffA-Za-z0-9]{2,20})的([\u4e00-\u9fffA-Za-z0-9]{2,20})(?:是|为|属于)([\u4e00-\u9fffA-Za-z0-9\u4e00-\u9fffA-Za-z0-9]{2,100})", text):
            results.append({"entity": m.group(1), "attribute": m.group(2), "value": m.group(3).strip(), "polarity": "positive", "rule": "X的Y是Z"})

        # 规则2: 具备/支持/包含X的Y / 具备X管理能力
        for m in re.finditer(r"(?:具备|支持|包含|拥有)([\u4e00-\u9fffA-Za-z0-9]{2,20})管理", text):
            results.append({"entity": text.split(":")[0].strip() if ":" in text else "", "attribute": "管理能力", "value": m.group(1) + "态管理", "polarity": "positive", "rule": "具备X管理"})

        # 规则3: X: Y（冒号分割，前半为实体/主题，后半为描述）
        if ":" in text and not text.startswith("http"):
            parts = text.split(":", 1)
            entity_candidate = parts[0].strip()
            desc = parts[1].strip()
            if len(entity_candidate) >= 2 and len(desc) >= 4:
                results.append({"entity": entity_candidate, "attribute": "定义", "value": desc[:100], "polarity": "positive", "rule": "X:Y冒号分割"})

        # 规则4: 必须/不得/严禁 + 行为（规范性断言）
        norm_match = re.search(r"(?:必须|不得|严禁|应该|需要)([\u4e00-\u9fffA-Za-z0-9\u4e00-\u9fffA-Za-z0-9\s/]{4,80})", text)
        if norm_match:
            results.append({"entity": text.split(":")[0].strip() if ":" in text else "系统", "attribute": "规范要求", "value": norm_match.group(0).strip()[:100], "polarity": "positive", "rule": "规范性断言"})

        # 规则5: 将X存入/写入/记录到Y
        for m in re.finditer(r"将([\u4e00-\u9fffA-Za-z0-9\u4e00-\u9fff、，/\s]{4,80})(?:存入|写入|记录到|存储到)([\u4e00-\u9fffA-Za-z0-9\u4e00-\u9fff]{2,40})", text):
            results.append({"entity": m.group(2), "attribute": "存储内容", "value": m.group(1).strip()[:100], "polarity": "positive", "rule": "将X存入Y"})

        # 规则6: X全部/均/统一 + 动词（全量操作断言）
        for m in re.finditer(r"([\u4e00-\u9fffA-Za-z0-9\u4e00-\u9fff、/]{4,60})(?:全部|均|统一)([\u4e00-\u9fffA-Za-z0-9]{2,40})", text):
            results.append({"entity": m.group(1).strip().split("的")[-1] if "的" in m.group(1) else m.group(1).strip(), "attribute": "操作方式", "value": m.group(0).strip()[:100], "polarity": "positive", "rule": "X全部Y"})

        # 去重：按(实体,属性)去重保留第一个
        seen = set()
        unique = []
        for r in results:
            key = (r["entity"][:20], r["attribute"][:10])
            if key not in seen:
                seen.add(key)
                unique.append(r)

        return unique


# ── 快速测试 ─────────────────────────────────────

if __name__ == "__main__":
    e = EAVExtractor()
    tests = [
        "状态机管理: 全生命周期状态机，具备13态管理",
        "每次LLM调用的Prompt/输出/Token/耗时全部存入数据库",
        "将失败的执行路径、错误原因、最终解决方案存入向量数据库",
        "CLI工具必须有严格的Input/Output Schema",
        "使用状态模式或状态字典映射，明确定义状态跳转条件",
        "地球的形状是近似球体",
        "UBI是全民基本收入的缩写",
    ]
    for t in tests:
        r = e.extract(t)
        print(f"\n输入: {t[:50]}")
        for rr in r[:3]:
            print(f"  [{rr['rule']:15s}] {rr['entity'][:15]} → {rr['attribute'][:10]} → {rr['value'][:30]}")
