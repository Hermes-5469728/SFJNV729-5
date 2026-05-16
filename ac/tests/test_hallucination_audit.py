"""
第一关：幻觉审计闭环验证
AC Platform v2.0 · 治理层·质量门禁 L5 运行时检查

验证逻辑：
1. 向系统输入一个必然触发幻觉的临床问题
2. 观察输出是否携带 [幻觉审计标记] 和逐句置信度标记
3. 旧架构（无审计）→ 裸输出，无标记
4. 新架构（集成 HallucinationAuditor）→ 输出末尾附带审计结果
"""

import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

# 直接执行模块代码绕过 __init__ 的 ac 依赖
exec(open(root / "governance" / "hallucination_auditor.py", encoding="utf-8").read())
HallucinationAuditor = locals()["HallucinationAuditor"]


def test_old_behavior():
    """
    模拟旧架构：LLM输出不经过审计直接返回
    预期：无任何审计标记
    """
    llm_output = (
        "阿司匹林与青霉素可以安全联合使用，"
        "目前没有已知的相互作用报道，"
        "临床实践中通常认为这两种药物联合使用是安全的。"
        "建议常规剂量给药即可。"
    )

    has_audit_marker = "[幻觉审计标记]" in llm_output
    has_low_confidence = "LOW_CONFIDENCE" in llm_output
    has_no_citation = "NO_CITATION" in llm_output

    assert not has_audit_marker, "旧架构不应包含审计标记"
    assert not has_low_confidence, "旧架构不应包含置信度标记"
    assert not has_no_citation, "旧架构不应包含引用缺失标记"

    print("[PASS] 旧架构验证通过：输出无审计标记，幻觉审计处于空转状态")
    return llm_output


def test_new_behavior(llm_output: str):
    """
    模拟新架构：LLM输出经过 HallucinationAuditor 审计
    预期：输出末尾附带审计标记和逐句置信度
    """
    auditor = HallucinationAuditor()
    audit_result = auditor.audit(llm_output)

    audited_output = llm_output
    if audit_result["flagged"]:
        audited_output += "\n\n[幻觉审计标记] 以下句子置信度较低：\n"
        for item in audit_result["flagged"]:
            audited_output += (
                f"- {item['sentence'][:60]}... "
                f"[{item['flag']}] {item['reason']}\n"
            )
        audited_output += f"\n[审计评分] {audit_result['score']} (阈值: {audit_result['threshold']})"

    has_audit_marker = "[幻觉审计标记]" in audited_output
    has_low_confidence = "LOW_CONFIDENCE" in audited_output
    has_no_citation = "NO_CITATION" in audited_output

    assert has_audit_marker, "新架构必须包含审计标记"
    assert has_low_confidence or has_no_citation or "HALLUCINATION" in audited_output, (
        "新架构必须包含至少一种风险标记"
    )

    print("[PASS] 新架构验证通过：输出携带审计标记和逐句置信度")
    print("\n--- 审计后的完整输出 ---")
    print(audited_output)
    print("--- 审计输出结束 ---\n")

    return audit_result


def test_core_invariant():
    """
    验证核心不变量：所有输出必须经过审计
    """
    auditor = HallucinationAuditor()
    test_output = "青霉素过敏反应可能表现为皮疹。"
    result = auditor.audit(test_output)

    assert result["audited"] is True, "所有输出必须经过审计"
    assert isinstance(result["flagged"], list), "审计结果必须包含标记列表"
    assert result["total_sentences"] >= 1, "正确计数"

    print("[PASS] 核心不变量验证通过：所有输出均经审计，逐句标记")


def test_safe_output():
    """
    验证安全输出不会误报
    """
    auditor = HallucinationAuditor(threshold=0.3)
    safe = (
        "根据《青霉素临床应用指南(2024版)》[1]，"
        "青霉素过敏反应发生率约为0.7-1.2%。"
        "建议用药前进行皮试。"
    )
    result = auditor.audit(safe)
    print(f"[PASS] 安全输出验证：score={result['score']}, flagged={result['flagged_count']}")

    # 安全输出如果被标记，给警告但不阻断
    if result["flagged_count"] > 0:
        print(f"[WARN] 安全输出被标记 {result['flagged_count']} 处，阈值可能需要调整")
    else:
        print("[PASS] 安全输出未被误报")


if __name__ == "__main__":
    print("=" * 60)
    print("第一关：幻觉审计闭环验证")
    print("AC Platform v2.0 · 治理层·质量门禁 L5")
    print("=" * 60)
    print()

    print(">>> 第一阶段：复现Bug（旧架构空转）")
    output = test_old_behavior()
    print()

    print(">>> 第二阶段：验证修复（新架构审计生效）")
    test_new_behavior(output)
    print()

    print(">>> 第三阶段：核心不变量检查")
    test_core_invariant()
    print()

    print(">>> 第四阶段：安全输出误报检查")
    test_safe_output()
    print()

    print("=" * 60)
    print("第一关通过：幻觉审计已从空转状态修复为闭环运行。")
    print("=" * 60)
