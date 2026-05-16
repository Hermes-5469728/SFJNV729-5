# DADS 个人版 (DADS-Personal) 产品架构

## 定位

面向医生的职业防护系统——在三明医改（DRG/DIP 支付改革）背景下，帮助医生合规执业、规避法律/行政风险。

**1+N 轨道**中作为 `ac-core/BaseAgent` 的垂直插件；**独立产品轨道**中作为医生日常工作台的完整工具。

---

## 一、1+N 轨道 — 垂直插件

### 代码位置
```
AgentHub/dads-personal/
├── __init__.py              # 统一导出
├── risk_assessment.py       # DoctorRiskAgent(BaseAgent) — assess() / _analyze()
└── protection_rules.py      # query_protection_rules() — 8条防护规则KB
```

### 调用链
```
User Input
  └→ DoctorRiskAgent.assess(description)
       ├→ think(description)                  # 继承自 BaseAgent
       │    ├→ query_protection_rules()       # 查询防护规则库
       │    ├→ TaskPlanner.decompose()        # 任务拆解
       │    └→ ShortTermMemory.add()          # 记忆记录
       └→ _analyze(description)              # 规则匹配
            ├→ 场景关键词 token 化
            ├→ 与 PROTECTION_KB (8条) 匹配评分
            └→ 返回: scenario / rule_id / severity / confidence / advice
```

### 三明医改防护规则 (PROTECTION_KB)

| ID | 场景 | 严重度 | 置信度 |
|---|---|---|---|
| PR-001 | DRG费用超支——推诿压力 | 🔴 危重 | 80% |
| PR-002 | 高危病例——治疗风险与转诊决策 | 🔴 危重 | 75% |
| PR-003 | 知情同意书——条款不完善被诉风险 | 🟠 重度 | 82% |
| PR-004 | 疑难病例——诊断不确定时合规路径 | 🟠 重度 | 70% |
| PR-005 | 药占比考核——合理用药与成本控制平衡 | 🟡 中度 | 78% |
| PR-006 | 平均住院日压力——提前出院与重返率 | 🟡 中度 | 73% |
| PR-007 | 患方投诉预警——沟通裂缝修复 | 🟡 中度 | 69% |
| PR-008 | 正常工作压力——职业常规 | 🟢 轻度 | 85% |

---

## 二、独立产品轨道 — DADS 个人版 (独立部署)

### 架构
```
┌─────────────────────────────────────────┐
│          DADS 个人版                     │
├─────────────┬─────────────┬─────────────┤
│ 合规自查    │ 免责声明    │ 沟通留痕    │
│ (DP1)       │ 生成 (DP2)  │ (DP3)       │
├─────────────┴─────────────┴─────────────┤
│     工作日志模块 (DP4)                   │
├─────────────────────────────────────────┤
│          通用数据中心                    │
└─────────────────────────────────────────┘
```

### 独立部署时扩展的目录
```
dads-personal/
├── compliance/       # 合规自查引擎
│   ├── drg_checker.py
│   ├── drug_ratio.py
│   └── admission_days.py
├── disclaimer/       # 免责声明生成器
│   ├── template_engine.py
│   └── consent_builder.py
├── communication/    # 医患沟通留痕
│   ├── recorder.py
│   └── sentiment_analyzer.py
├── journal/          # 工作日志自动化
│   ├── auto_logger.py
│   └── risk_diary.py
├── api/              # REST API 层
└── web/              # Web 前端 (医生工作台)
```

### V1.0 → V2.0 升级路线

| 版本 | 能力 | 状态 |
|---|---|---|
| V1.0 | 场景规则匹配 (8 条防护规则 KB) | 已交付 |
| V1.5 | 免责声明模板自动生成, Hermes 数据中心真实 API 接入 | 待开发 |
| V2.0 | 医患沟通录音→文字→风险分析, 独立 Web 医生工作台 | 待规划 |

---

## 三、与 dads-medical 的区别

| 维度 | dads-medical | dads-personal |
|---|---|---|
| 服务对象 | 患者 (诊断) | 医生 (防护) |
| 知识库 | 医学术语/疾病 | 医改政策/法规 |
| 输入 | 症状描述 | 工作场景描述 |
| 输出 | 诊断建议 | 风险等级+合规建议 |
| 严重度标注 | 疾病危重度 | 法律/行政风险度 |

---

*文档版本: v1.0 | 创建时间: 2026-05-11*
