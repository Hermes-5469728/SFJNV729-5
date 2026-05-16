from shared.hermes.client import HermesClient


_client = HermesClient()

MEDICAL_KB = [
    {
        "disease": "急性髓系白血病 (AML)",
        "symptoms": ["贫血", "乏力", "发热", "出血倾向", "骨痛", "反复感染",
                     "牙龈增生", "皮肤瘀斑", "体重下降"],
        "severity": "critical",
        "confidence_base": 0.67,
        "advice": "建议立即血液科就诊，完善骨髓穿刺+流式细胞术+细胞遗传学检查",
    },
    {
        "disease": "急性淋巴细胞白血病 (ALL)",
        "symptoms": ["发热", "贫血", "出血", "淋巴结肿大", "骨关节痛",
                     "肝脾肿大", "乏力", "食欲减退"],
        "severity": "critical",
        "confidence_base": 0.65,
        "advice": "建议立即儿科/血液科就诊，完善骨髓穿刺+免疫分型+融合基因检测",
    },
    {
        "disease": "急性心肌梗死",
        "symptoms": ["胸痛", "胸闷", "呼吸困难", "大汗", "恶心", "濒死感",
                     "左肩放射痛", "下颌痛", "心悸"],
        "severity": "critical",
        "confidence_base": 0.72,
        "advice": "立即拨打120，嚼服阿司匹林300mg，保持静卧，监测生命体征",
    },
    {
        "disease": "重症肺炎 / 脓毒症",
        "symptoms": ["高热", "寒战", "咳嗽", "咳痰", "呼吸困难", "胸痛",
                     "意识模糊", "血压下降", "尿少"],
        "severity": "severe",
        "confidence_base": 0.63,
        "advice": "建议急诊就诊，完善血常规+CRP+降钙素原+胸部CT+血培养",
    },
    {
        "disease": "糖尿病酮症酸中毒",
        "symptoms": ["多饮", "多尿", "恶心", "呕吐", "腹痛", "呼吸深快",
                     "意识障碍", "乏力", "体重下降", "口干"],
        "severity": "severe",
        "confidence_base": 0.61,
        "advice": "建议急诊就诊，立即查血糖+血酮+血气分析+电解质",
    },
    {
        "disease": "社区获得性肺炎",
        "symptoms": ["咳嗽", "发热", "咳痰", "胸痛", "呼吸困难", "乏力",
                     "头痛", "肌肉酸痛"],
        "severity": "moderate",
        "confidence_base": 0.74,
        "advice": "建议门诊查血常规+CRP+胸部X线，根据病原学结果选用抗生素",
    },
    {
        "disease": "缺铁性贫血",
        "symptoms": ["乏力", "头晕", "面色苍白", "心悸", "气短", "异食癖",
                     "反甲", "脱发", "注意力不集中"],
        "severity": "moderate",
        "confidence_base": 0.78,
        "advice": "建议门诊查血常规+铁代谢四项+便潜血，排查消化道慢性失血",
    },
    {
        "disease": "原发性高血压",
        "symptoms": ["头晕", "头痛", "颈项僵硬", "心悸", "耳鸣", "视物模糊",
                     "失眠", "鼻出血", "乏力"],
        "severity": "moderate",
        "confidence_base": 0.76,
        "advice": "建议非同日三次以上血压测量，完善动态血压+心超+肾功能+眼底检查",
    },
    {
        "disease": "急性上呼吸道感染",
        "symptoms": ["鼻塞", "流涕", "喷嚏", "咽痛", "咳嗽", "发热",
                     "头痛", "乏力", "声音嘶哑"],
        "severity": "mild",
        "confidence_base": 0.88,
        "advice": "多饮水、休息，可对症使用解热镇痛药，症状加重或持续5天以上及时就医",
    },
    {
        "disease": "急性胃肠炎",
        "symptoms": ["腹痛", "腹泻", "恶心", "呕吐", "发热", "食欲不振",
                     "肠鸣音亢进", "脱水"],
        "severity": "mild",
        "confidence_base": 0.82,
        "advice": "清淡饮食，口服补液盐预防脱水，腹泻严重或血便时及时就医",
    },
]


def query_medical_knowledge(keywords: str) -> list | None:
    endpoint = f"/knowledge/medical/disease/{keywords[:30]}"
    _client.read_data(endpoint)

    tokens = set(keywords.lower().replace("，", " ").replace(",", " ").split())

    scored = []
    for entry in MEDICAL_KB:
        entry_tokens = set(s.lower() for s in entry["symptoms"])
        match_count = len(tokens & entry_tokens)
        if match_count == 0:
            continue
        coverage = match_count / len(entry["symptoms"])
        specificity = match_count / len(tokens) if tokens else 0
        score = 0.6 * coverage + 0.4 * specificity
        scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored] if scored else None
