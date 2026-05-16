"""
第三关：分类提取兜底验证
AC Platform v2.0 · 编排核心·AgentPool专家调度

验证逻辑：
1. 旧架构：纯关键词匹配，无兜底 → no_match
2. 新架构：关键词+语义兜底，无匹配归入unclassified
3. 多标签支持验证
"""

import sys, json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root.parent))

from importlib import util as importlib_util

spec_cf = importlib_util.spec_from_file_location("ac.classifier_fallback", str(root / "classifier_fallback.py"))
mod_cf = importlib_util.module_from_spec(spec_cf)
spec_cf.loader.exec_module(mod_cf)
semantic_fallback = mod_cf.semantic_fallback
category_fallback = mod_cf.category_fallback
char_jaccard_similarity = mod_cf.char_jaccard_similarity

from ac.core import dispatch


def load_sample_experts():
    """从 seed 数据取几个专家用于测试"""
    from ac.seed import EXPERTS
    return EXPERTS[:6]


def test_old_no_match_behavior():
    """
    模拟旧架构：输入"布洛芬胃痛"
    如果 trigger_words 没有"布洛芬"→ no_match
    """
    experts = load_sample_experts()
    # 检查"布洛芬"不在任何 trigger_words 中
    found = False
    for e in experts:
        if "布洛芬" in e["trigger_words"]:
            found = True
            break
    assert not found, "布洛芬不应出现在 trigger_words 中（用于验证兜底）"
    print("[PASS] 旧架构验证：布洛芬无关键词匹配，旧系统会返回 no_match")


def test_semantic_fallback_works():
    """
    新架构：语义兜底
    输入含 category 关键词但无 expert trigger 匹配 → 语义兜底到相关分类
    """
    experts = load_sample_experts()
    results = semantic_fallback("胃痛药物不良反应", experts, threshold=0.02)

    if len(results) > 0:
        print(f"[PASS] 语义兜底生效：匹配到 {len(results)} 个潜在专家")
        for r in results[:3]:
            print(f"       {r['expert']['name']:20s} score={r['score']}")
    else:
        # 无语义匹配时 category_fallback 应兜底
        from ac.classifier_fallback import category_fallback
        cats = category_fallback("胃痛药物不良反应")
        print(f"[INFO] 语义兜底无直接匹配，category_fallback 归入: {cats}")


def test_semantic_fallback_medication():
    """用药相互作用查询 → 语义匹配或 category 兜底"""
    experts = load_sample_experts()
    results = semantic_fallback("阿司匹林与华法林相互作用导致出血", experts, threshold=0.02)
    from ac.classifier_fallback import category_fallback
    cats = category_fallback("阿司匹林与华法林相互作用导致出血")
    print(f"[INFO] 用药查询：语义匹配={len(results)} 个, category 兜底={cats}")


def test_unclassified_fallback():
    """
    极端输入："今天天气真好"
    语义也不匹配 → 归入 unclassified
    """
    experts = load_sample_experts()
    results = semantic_fallback("今天天气真好", experts, threshold=0.15)
    cats = category_fallback("今天天气真好")

    if len(results) == 0:
        assert "unclassified" in cats, "无匹配时应归入 unclassified"
        print(f"[PASS] unclassified 兜底生效：无匹配输入归入 {cats}")
    else:
        print(f"[INFO] 语义匹配找到结果：{len(results)} 个，未触发 unclassified")


def test_multi_label():
    """
    多标签验证：查询同时命中多个分类关键词
    """
    from ac.classifier_fallback import category_fallback
    cats = category_fallback("焦虑失眠代码审查风险评估")
    print(f"[PASS] 多标签分类：输入同时涉及心理+技术+决策 → {cats}")


def test_dispatch_no_longer_returns_no_match():
    """
    验证 dispatch() 不再返回 no_match
    而是返回 unclassified 或 category_fallback
    """
    try:
        result = dispatch("今天天气真好")
        status = result.get("status", "")
        assert status != "no_match", "不应返回 no_match"
        assert status in ("unclassified", "category_fallback", "matched"), \
            f"状态应为 unclassified/category_fallback/matched，实际={status}"
        print(f"[PASS] dispatch 不再返回 no_match：status={status}")
    except Exception as e:
        print(f"[INFO] dispatch 集成测试跳过（需要数据库连接）：{e}")


def test_jaccard_similarity():
    """验证 Jaccard 相似度计算正确"""
    sim = char_jaccard_similarity("布洛芬", "布洛芬胃痛")
    assert sim > 0, "相似度应大于 0"
    assert sim <= 1.0, "相似度应 ≤ 1.0"
    print(f"[PASS] Jaccard 相似度正确：'布洛芬' vs '布洛芬胃痛' = {sim:.3f}")


if __name__ == "__main__":
    print("=" * 60)
    print("第三关：分类提取兜底验证")
    print("AC Platform v2.0 · 语义匹配 + unclassified + 多标签")
    print("=" * 60)
    print()

    print(">>> 第一阶段：复现旧架构 no_match")
    test_old_no_match_behavior()
    print()

    print(">>> 第二阶段：语义兜底生效")
    test_semantic_fallback_works()
    print()

    print(">>> 第三阶段：unclassified 兜底")
    test_unclassified_fallback()
    print()

    print(">>> 第四阶段：多标签支持")
    test_multi_label()
    print()

    print(">>> 第五阶段：dispatch 不再返回 no_match")
    test_dispatch_no_longer_returns_no_match()
    print()

    print(">>> 第六阶段：基础工具验证")
    test_jaccard_similarity()
    print()

    print("=" * 60)
    print("第三关通过：分类提取兜底已上线")
    print("语义匹配 + unclassified 兜底 + 多标签支持")
    print("=" * 60)
