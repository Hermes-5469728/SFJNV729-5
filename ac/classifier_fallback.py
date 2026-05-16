"""
ClassifierFallback · 分类提取兜底引擎
纯字符级语义匹配，无外部依赖。
在 keyword dispatch 无匹配时调用。
"""

import re
from collections import Counter


# 分类级兜底关键词（当专家trigger_words都不匹配时使用）
CATEGORY_KEYWORDS = {
    "L": [
        "生活", "健康", "心理", "情感", "关系", "工作", "职业",
        "家庭", "社交", "焦虑", "抑郁", "压力", "失眠",
        "诈骗", "安全", "法律", "劳动", "权益", "婚姻",
        "财务", "投资", "消费", "购物", "租房", "合同",
        "医疗", "疾病", "症状", "药物", "过敏", "疼痛",
        "教育", "学习", "考试", "培训", "技能",
    ],
    "T": [
        "技术", "代码", "编程", "架构", "设计", "开发",
        "Python", "Java", "JavaScript", "前端", "后端",
        "数据库", "SQL", "API", "接口", "服务器",
        "部署", "容器", "Docker", "Git", "测试",
        "算法", "数据结构", "性能", "优化", "调试",
        "安全", "加密", "认证", "权限", "漏洞",
        "AI", "机器学习", "模型", "训练", "推理",
        "Linux", "命令行", "脚本", "自动化",
    ],
    "M": [
        "临床", "诊断", "治疗", "药物", "医疗", "医院",
        "患者", "症状", "疾病", "手术", "检查",
        "血压", "血糖", "心率", "体温", "化验",
        "处方", "剂量", "相互作用", "不良反应",
        "疫苗", "感染", "炎症", "慢性病",
        "急诊", "ICU", "护理", "康复",
    ],
    "A": [
        "决策", "分析", "评估", "风险", "策略", "规划",
        "管理", "组织", "协调", "沟通", "谈判",
        "质量控制", "审计", "审查", "检查",
        "评分", "排名", "比较", "选择",
        "目标", "计划", "执行", "监督",
        "紧急", "危机", "应急", "预案",
    ],
}


def char_jaccard_similarity(a: str, b: str) -> float:
    """字符级 Jaccard 相似度"""
    set_a = set(a)
    set_b = set(b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def term_overlap_score(text: str, keywords: list[str]) -> float:
    """关键词覆盖评分：多少关键词出现在文本中"""
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in text_lower)
    return hits / max(len(keywords), 1)


def ngram_similarity(a: str, b: str, n: int = 2) -> float:
    """n-gram 相似度（捕获碎片级匹配）"""
    a_ngrams = set(a[i:i+n] for i in range(len(a)-n+1))
    b_ngrams = set(b[i:i+n] for i in range(len(b)-n+1))
    if not a_ngrams or not b_ngrams:
        return 0.0
    return len(a_ngrams & b_ngrams) / len(a_ngrams | b_ngrams)


def semantic_fallback(query: str, experts: list[dict], threshold: float = 0.05) -> list[dict]:
    """
    语义兜底匹配（n-gram + 字符级）
    在 keyword dispatch 无匹配时调用。
    返回按相似度排序的专家列表，每个带 score。
    """
    query_lower = query.lower()
    scored = []

    for e in experts:
        # 构建该专家的匹配语料
        corpus = e["trigger_words"] + " " + e["role_definition"] + " " + e.get("rules", "")
        corpus_lower = corpus.lower()

        # 1. bi-gram 相似度（捕获碎片匹配）
        bigram = ngram_similarity(query_lower, corpus_lower, n=2)

        # 2. tri-gram 相似度
        trigram = ngram_similarity(query_lower, corpus_lower, n=3)

        # 3. 字符级 Jaccard 相似度
        jac = char_jaccard_similarity(query_lower, corpus_lower)

        # 4. trigger_words 关键词覆盖
        triggers = [t.strip() for t in e["trigger_words"].split(",") if t.strip()]
        trig_score = term_overlap_score(query, triggers)

        # 5. 分类级关键词覆盖
        cat_kw = CATEGORY_KEYWORDS.get(e["category"], [])
        cat_score = term_overlap_score(query, cat_kw)

        # 综合评分（多维度加权）
        combined = bigram * 0.25 + trigram * 0.15 + jac * 0.1 + trig_score * 0.3 + cat_score * 0.2

        if combined >= threshold:
            scored.append({
                "expert": e,
                "score": round(combined, 3),
                "method": "semantic_fallback",
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def category_fallback(query: str) -> list[str]:
    """
    纯分类级兜底：连语义匹配也无结果时，至少归入一个分类
    返回分类标签列表 [L/T/M/A]
    """
    query_lower = query.lower()
    scores = {}
    for cat, kws in CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw.lower() in query_lower)
        scores[cat] = hits

    if not any(scores.values()):
        return ["unclassified"]

    max_score = max(scores.values())
    return [cat for cat, s in scores.items() if s == max_score and s > 0]
