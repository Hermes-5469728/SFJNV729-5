# CoPilot DADS v19.4 · 极致详细架构 · 中文注释版

> 对齐 ARCHITECTURE.md · 同级粒度 · 子体视角
> 母体 CoPilot → 子体 DADS · 全部模块展开到底

---

## 一、DADS宪法 · 四条底层认知

1. 查药≠猜药。规则引擎查本地txt——不是LLM推测。确定性>覆盖率。
2. 全离线≠落后。医院内网拔了网线——这是设计约束·不是技术限制。
3. 溯源=可信。每条答案标出处——打开源文件就能核实。不靠背书。
4. DADS是工具·不是医生。不诊断·不开药·不替人做决定。输出末尾强制标注。

---

## 二、核心目标（3条）

1. 查对药 — 31种药·120组相互作用·17条指南·3秒返回
2. 不出错 — 规则引擎零幻觉·LLM部分强制标注·不编数据
3. 零门槛 — exe双击即用·不需要Python·不需要网络·不需要注册

---

## 三、母体-子体 BDD行为契约

> 源自母体宪法第1条。母体优先级 > 子体（含独立/未独立/系统内）。DADS通过第8审查员(契约审查员)执行此协议。

**核心约束:**
- 数据收集权永远平级·母体无权单方面提取子体数据
- 子体离线期间母体不能访问子体数据·同步必须用户手动触发
- 子体核心功能(药物核查)全程离线可用
- 任何架构提案须附带 Given-When-Then + SHOULD_NEVER 验证
- 详情见母体 ARCHITECTURE.md 第五节 + bdd_method.md

---

## 四、四层架构 · 逐层展开

### 第一层 · 本地数据层 · dads_db/

```
drugs.txt          90+种药    药名|类别|别名|指南来源|日期
interactions.txt   120+组     A药|B药|级别|机制|建议|来源|日期
guidelines.txt     17条      疾病|指南来源|要点|证据等级|日期
safety.txt         40+种     药名|妊娠分类|哺乳|肝损|肾损|来源
policy_drg.json    DRG规则   编码陷阱·违规模式·因果链
policy_reality.json 薪酬数据  工分制·工时·倦怠·医院财务
drg_rules.json     分组规则

原则: 全部txt/json·人类可读·药房主任能打开·每行可git diff
```

### 第二层 · 规则引擎 · 确定性·零幻觉·<5ms

```
drug_lookup()         精确匹配+别名模糊(90+别名)
interaction_check()   O(n²)交叉检查·120组数据库全量匹配
guideline_search()    关键词检索·17条A级指南
crcl_adjustment()     29种药·4级分层(标准/减量/慎用/禁忌)
clinical_scores()     9个评分(CHA2DS2·HAS-BLED·CURB-65·GCS·Wells·Child-Pugh·TIMI·ABCD²)
drg_predict()         DRG入组预测·编码陷阱提示

→ 全部规则引擎·零LLM·零幻觉·<5ms响应
→ 结果标注[VERIFIED]
```

### 第三层 · 检索增强 · 离线TF-IDF·<50ms

```
TfidfVectorizer    char_wb·1-3gram·2000维
cosine_similarity  top-k=5
260条chunk         90药物+120相互作用+17指南+2FHIR+31安全
→ 全离线·零下载·sklearn预安装·<50ms
→ DADSVectorStore 零依赖numpy版·258条索引·哈希致敬
```

### 第四层 · LLM生成 · 可选·有API时启用

```
DADSBrain 3-Tier:
  Tier 1: Ollama本地 (零网络) 
  Tier 2: DashScope Qwen-Plus / DeepSeek API
  Tier 3: 纯规则引擎 (零LLM·零网络)
temperature=0.3·max_tokens=1024·3次指数退避(1s/2s/4s)
→ 无API时自动退化为纯规则引擎
→ 离线模式提示"当前离线·仅本地检索结果"
```

---

## 四、桌面应用 · CoPilot-DADS.exe

**文件: dads_desktop.py · 500行 · 打包后11MB(离线)/45MB(联网)**

**7个标签:**

标签1 · 💊 药物核查
  正则提取(drug+剂量+单位+频次+途径) → 别名模糊(90+别名) → 每药频率/途径提取
  → O(n²)相互作用交叉检查 → 孕妇/肝损安全提醒 → 肾排泄药物提醒

标签2 · 📋 SOAP训练
  S(主观)/O(客观)/A(评估)/P(计划)四栏
  高血压/糖尿病两种预设模板 → 一键加载
  导出到剪贴板

标签3 · 📖 指南速查
  17条实时搜索 · 每条标注来源+证据等级
  全部A级证据(100%)

标签4 · 🧮 计算工具
  体重剂量(mg/kg) · CrCl(Cockcroft-Gault·自动肾功能分级)
  BSA(Mosteller公式) · 4个临床评分(勾checkbox→出分)

标签5 · 🔧 数据管理
  密码认证(dads2026) → 添加药物/相互作用/指南 → 写入txt
  即时生效

标签6 · 📂 数据库浏览
  4个子标签: 药物库·相互作用库·指南库·安全数据库
  实时搜索过滤·显示记录数

标签7 · 🤖 AI问答(仅联网版)
  先查本地数据库 → 有API Key→DashScope生成 → 无API→仅本地检索

**打包: PyInstaller -F --noconsole · 零依赖 · 便携式**
**降级: 无API Key时AI问答退化为纯本地模式**

---

## 五、前端 · Streamlit版

**文件: medical_app.py · 640+行 · :8500**

6个标签 + 侧边栏 + 顶部栏

标签1 · 💊 药物核查
标签2 · 📋 SOAP训练
标签3 · 📖 指南速查
标签4 · 🧮 计算工具
标签5 · 🔧 数据管理
标签6 · 👤 个人定制 (偏好·寄生笔记·上传·学习路线·进度)

特性: 中英双语切换·4用户(SHA256)·游客模式·全离线·可选AI
CrCl默认值记忆·药物查询追踪·临床评分频率统计

---

## 六、审查体系 · 8重地狱评审团

**文件: core/dads_reviewer.py · 367行**

| 审查员 | 盯什么 | 检查项 |
|--------|--------|:---:|
| 临床主任 | 免责风险 | 剂量建议·诊断性语言·过度确信·AI暴露 |
| 懂王患者 | 隐私+信任 | 隐私暴露·用药偏见·数据推理·费用暗示 |
| 合规判官 | 溯源+审计 | [VERIFIED]缺失·LLM来源·敏感人群 |
| 老旧硬件 | 离线+性能 | 云端依赖·重型依赖·Win7兼容 |
| 医保判官 | 收费+合规 | 高成本药物·DRG陷阱·运行成本 |
| 脏数据沼泽 | 格式+质量 | 日期不一致·非结构化·系统孤岛 |
| 算法偏见 | 公平+可解释 | 黑箱算法·人群偏见·性能分层 |
| 契约审查员 | BDD契约 | SILENT_PULL·OFFLINE_ACCESS·MOTHER_WRITE |

---

## 七、母体-子体 BDD行为契约

> BDD 不是 DADS 的审查功能——是母体-子体之间的宪法级协议。独立于 8 重地狱但在 DADS 中通过第 8 审查员执行。

**宪法第1条:** 任何影响母体-子体数据流或控制流的改动，必须附带 Given-When-Then 场景 + SHOULD_NEVER 反向验证。
**知识文档:** agents/hermes/bdd_method.md
**执行代理:** 契约审查员(第8席)·6种违背模式自动检测→SILENT_PULL/OFFLINE_ACCESS/MOTHER_WRITE等→发生即BLOCK
**核心约束:** 子体数据归子体所有·母体无权单方面提取·同步必须用户手动触发·子体核心功能全程离线可用

---

## 八、个人化引擎

**文件: core/dads_personal.py · 430行**

```
10.2 偏好: load/save_dads_prefs() — CrCl默认·常用药物排名·语言·字号·时间模式
10.3 寄生笔记: parse_parasitic_note() — [ENTITY][SOURCE][STEP‑1..4][IX][GAP]→自动同步
10.4 锚点: set_oath()·add_milestone()·check_oath_drift()
10.5 Interrupter: get_current_time_block()·check_interrupter() — 4时段切换
10.6 学习追踪: generate_weekly_report()·get_knowledge_gaps(7科室扫描)
10.7 输出模式: format_drug_result() — 简明/学习/教学三模式
10.8 学习路线+上传: process_uploaded_file()·generate_study_plan()·get_personal_db_stats()
```

---

## 九、LLM抽象层 · 三层大脑

**文件: core/dads_llm.py · 120行**

```
DADSBrain:
  Tier 1: Ollama本地 (qwen2:7b·subprocess调用·零网络)
  Tier 2: DashScope/DeepSeek API (需.env Key)
  Tier 3: 纯规则引擎 (零LLM·零网络·零依赖)
  自动降级: ollama → api → rule
  ask() — 统一接口·自动选择可用tier
```

---

## 十、向量存储 · 零依赖RAG

**文件: core/dads_vector.py · 180行**

```
DADSVectorStore:
  _hash_ngram()     — 1‑3gram哈希致敬(零依赖·numpy可选加速)
  index_dads_db()   — 索引drugs+interactions+guidelines+safety→258条
  search()           — top‑k=5余弦相似度·<50ms
  save/load_cache() — pickle缓存·重建<2秒
```

---

## 十一、防御管道

### 母体Gaia (942行)

```
L1 输入检测    8攻击点·6越狱·46高危词意图路由
L2 NLI辩论     多裁判规则引擎·矛盾检测·Meta-Judge
L3 术中审查    8维幻觉扫描(Type1‑8)·P0/P1/P2分级
L4 TRACE溯源   5标签·输出防火墙
L5 强制标注    中英双语·永久无例外
L6 物理验证    DADS四库完整性·文件/日志/git
L7 结构对齐    模块结构·循环依赖·架构评分
```

### DADS轻量防御

```
规则引擎直接返回 → 跳过L2‑L6(数据来自已验证本地文件)
LLM生成内容 → L1攻击检测 + L5强制标注 → 8重地狱审查
全部输出末尾 → 强制中英双语幻觉标注(无例外)
```

---

## 十一、数据流 · 完整路径

```
用户输入
  │
  ├─ Interrupter时间守护检查
  ├─ 规则引擎·精确匹配
  │   命中 → 返回·[VERIFIED:+文件名]
  ├─ 规则引擎未命中 → 向量检索
  │   命中 → 返回·[SOURCE:dads_db]
  ├─ 向量检索未命中 → DADSBrain
  │   Ollama→API→RuleEngine自动降级
  ├─ 回答生成后 → 8重地狱审查
  │   BLOCK→阻断  FAIL→标记  WARN→警告  PASS→通过
  └─ L5强制标注 → 追踪记录 → 返回用户
```

---

## 十二、母体与子体区别

| 维度 | 母体 CoPilot | 子体 DADS‑RAG |
|------|------------|----------|
| 定位 | AI安全壳·通用 | 药物工具·垂直 |
| 防御 | L1‑L7全量(942行) | 8重地狱+L1+L5 |
| 数据 | 无内置·靠LLM+DADS | dads_db/本地txt |
| LLM依赖 | 强依赖·每次对话 | 弱依赖·离线可运行 |
| 用户 | AI开发者·个人 | 医护·医学生 |
| 分发 | 需要Python+API | 一个exe+文件夹 |
| 联网 | 必须 | 不需要 |

---

## 十三、当前数据规模

```
90+种药 · 90+别名 · 120+组相互作用 · 20+条A级指南
40+种安全数据 · 29种CrCl规则 · 9个临床评分
258条RAG索引 · 20条ADR · 10个测试文件
8个审查员 · 51节真值数据集 · 15条可验证URL
代码总量: 3500+行 · 投入: 9天 · ¥147
```

---

## 十四、部署与交付

```
桌面    CoPilot-DADS.exe (11MB离线) + 联网版 (45MB)
Streamlit medical_app.py :8500 · copilot_app.py :8502
审查    python core/triple_review.py
分发    CoPilot-DADS-安装包.zip (44.7MB)
```
