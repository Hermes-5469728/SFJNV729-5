# DADS-RAG AGENT · 架构与代码 · Architecture & Code
> 母体 CoPilot → 子体 DADS-RAG AGENT
> 全模块展开到函数级 · 文件级 · 数据流级

---

## 一、母体 CoPilot · 核心模块

### gaia_defense_pipeline.py · 942行 · L1-L7防御管道

```
GaiaDefensePipeline.__init__()
  ├── SemanticCache()          向量相似度缓存·阈值0.45·200条
  ├── InputAttackDetector(L1)  8攻击点+6越狱+46高危词意图路由
  ├── NLIDebateEngine(L2)      多裁判规则引擎+矛盾检测+Meta-Judge
  ├── IntraOpReview(L3)        8维幻觉扫描(Type1-8)·P0/P1/P2分级
  ├── TraceAnnotator(L4)       5标签溯源([FILE][HUMAN][LLM][EXTERNAL][UNKNOWN])
  ├── MandatoryLabeler(L5)     中英双语强制标注·5级透明度
  ├── PhysicalRealityVerifier(L6) DADS四库完整性·文件/日志/git存在
  └── GAP-001~010协议: 意图路由·置信度·递归守卫·安全·效能·沙箱·标注
```

### copilot_app.py · 310行 · AI双模态对话前端 · :8502

```
双模态架构:
  医疗模式: DADS查询→禁忌检测→剂量校验→CrCl调整→证据分级→L5标注
  私人模式: 8 Agent子人格(psychologist/relationships/architect/coder/clinician/english/dissector/tracker)
  API: DashScope Qwen-Plus(主)·DeepSeek(备)
  重试: 3次指数退避(1s/2s/4s)
```

### server.py · 1639行 · Flask API后端 · :3000

```
路由:
  /api/chat           AI对话
  /api/memory         记忆管理
  /api/search         知识库搜索
  /api/knowledge      知识管理CRUD
  /api/upload         知识上传入库
```

### core/scores.py · 277行 · 临床评分引擎

```
9个评分: CHA2DS2-VASc·HAS-BLED·Wells DVT·Wells PE·CURB-65·GCS·Child-Pugh·TIMI·ABCD²
29种CrCl剂量调整: CRCL_ADJUSTMENTS字典·4级分层(标准/减量/慎用/禁忌)
  check_crcl_all() — 批量剂量检查
  get_crcl_adjustment() — 单药CrCl查询
```

### core/triple_review.py · 603行 · 四视角审查

```
审查员:
  计算机书记: 15项数字足迹(文件·行数·git·ADR·日志·YAGNI)
  架构师: 10条心法评分(进化·内聚·康威·CAP·防御·KISS)
  三甲医院: 临床质量审查(药物·相互作用·指南·CrCl·安全·致命禁忌)
  学院派导师: 9项工程审计(exe·大小·文档·依赖·配置·日志)
```

---

## 二、子体 DADS-RAG AGENT · 核心模块

### dads_desktop.py · 500行 · 桌面应用 · CoPilot-DADS.exe

```
7个Tkinter标签:
  标签1 · 💊 药物核查
    DOSE_RE正则(drug+剂量+单位+频次+途径) → 别名模糊(90+别名)
    → O(n²)相互作用交叉检查 → 孕妇/肝损安全提醒 → CrCl调整
  标签2 · 📋 SOAP训练
    高血压/糖尿病模板→一键加载·S/O/A/P四栏·导出剪贴板
  标签3 · 📖 指南速查
    17条可折叠·来源+证据等级·全部A级
  标签4 · 🧮 计算工具
    体重剂量(mg/kg)·CrCl(Cockcroft-Gault+自动分级)·BSA(Mosteller)
    4个临床评分(CHA2DS2·HAS-BLED·CURB-65·GCS)→checkbox→出分
  标签5 · 🔧 数据管理
    密码dads2026→添加药物/相互作用/指南→写入txt·即时生效
  标签6 · 📂 数据库浏览
    4子标签·实时搜索·显示记录数
  标签7 · 🤖 AI问答(联网版)
    DADSBrain(3-tier LLM)→先查本地→有API则生成→无API退化为规则引擎

打包: PyInstaller -F --noconsole
  离线版: 11MB · 联网版: 45MB(含sklearn)
  API Key可选: 无API时AI问答退化为纯本地模式
```

### medical_app.py · 640+行 · Streamlit前端 · :8500

```
6个标签:
  💊 药物核查   正则提取+O(n²)交互检查+CrCl自动调整+Gaia验证
  📋 SOAP训练   S/O/A/P四栏·模板加载·导出
  📖 指南速查   17条·可折叠·来源+证据
  🧮 计算工具   体重/CrCl(默认值预填充)/BSA/9个评分(自动追踪使用频率)
  🔧 数据管理   dads2026密码·批量导入导出·逐条添加
  👤 个人定制   5子标签: 偏好·寄生笔记·上传·学习路线·进度

特性: 中英双语·4角色(SHA256)·游客模式·全离线·可选AI
      CrCl默认值记忆·药物查询追踪·临床评分频率统计
```

### core/dads_personal.py · 430行 · 个人化引擎

```
10.2 个人偏好:      load/save_dads_prefs() — CrCl默认·常用药物·语言·字号·时间
10.3 寄生笔记:      parse_parasitic_note() — [ENTITY][SOURCE][STEP-1..4][IX][GAP]
                   sync_parasitic_to_guidelines() — 自动同步到guidelines.txt
10.4 锚点系统:      set_oath()·add_milestone()·check_oath_drift()
10.5 时间守护:      get_current_time_block()·check_interrupter() — 4时段切换
10.6 学习追踪:      load_tracker()·generate_weekly_report()·get_knowledge_gaps(7科室)
10.7 输出模式:      format_drug_result()·format_ix_result() — 简明/学习/教学三模式
10.8 学习路线+上传: process_uploaded_file()·generate_study_plan()·get_personal_db_stats()
贡献证明:          log_contribution()·get_contribution_badge()·get_contributor_priority()
                  上传验证通过→标记+优先接收新知识·不上传不受罚
```

### core/dads_llm.py · 120行 · 三层LLM抽象

```
DADSBrain · 3-Tier:
  Tier 1: Ollama (本地·零网络·qwen2:7b) → _ask_ollama()
  Tier 2: DashScope/DeepSeek API → _ask_api()
  Tier 3: 纯规则引擎 → _ask_rule()
  自动降级: ollama→api→rule
  可用性检测: _check_ollama()·_init_api_client()
```

### core/dads_reviewer.py · ~400行 · 8重地狱评审团

```
内嵌审查Agent(不依赖母体Gaia管道)·8重地狱:
  3恶人:
    [临床主任] review_clinical_director()  — 过度确信·AI暴露·诊断越界·多药风险
    [懂王患者] review_savvy_patient()     — 隐私暴露·用药偏见·数据推理·费用暗示
    [合规判官] review_compliance_officer() — 溯源缺失·LLM来源·敏感人群·审计缺失
  4死局:
    [老旧硬件] review_old_hardware()      — 云端依赖·重型依赖·Win7兼容·CPU占用
    [医保判官] review_insurance_judge()   — 高成本药物·DRG陷阱·运行成本·采购壁垒
    [脏数据]   review_messy_data()        — 格式不一致·非结构化·系统孤岛·数据污染
    [算法偏见] review_algorithmic_bias()   — 黑箱算法·人群偏见·性能分层·可解释性
  1契约守卫:
    [契约审查] review_bdd_contract()       — SILENT_PULL·OFFLINE_ACCESS·MOTHER_WRITE
                                           AUTO_UPLOAD·MOTHER_DEPENDENCY·PRIVACY_LEAK
                                           6种违背模式自动检测·发生即BLOCK
  SHA256哈希互审·执行前强制校验·90天更新下限
  run_dads_review() — 全部8视角+契约审查·返回BLOCK/FAIL/WARN/PASS
```

### core/dads_vector.py · 180行 · 零依赖向量存储

```
DADSVectorStore:
  _hash_ngram()      — 1-3gram哈希致敬(零依赖·numpy可选加速)
  _cosine()           — 余弦相似度
  index_dads_db()     — 索引 drugs+interactions+guidelines+safety → 258条chunk
  search()            — top-k=5·<50ms
  search_formatted()  — 带[SOURCE:]标签的输出
  save/load_cache()   — pickle缓存·重建<2秒

全局函数:
  search_dads_db()·search_dads_formatted()·rebuild_index()·get_vector_store()
```

### DADS桌面版UI结构 · dads_desktop.py

```
class DADSApp(tk.Tk):
    __init__()
      ├── _load_data()           数据加载(drugs/interactions/guidelines)
      ├── _setup_logo()          顶部logo栏
      ├── _setup_tabs()          7个标签页notebook
      └── _setup_status()        底部状态栏(记录数)

    Tab 1 · DrugCheckFrame:
      extract_meds()             正则提取(drug+剂量+单位+频次+途径)
      check_interactions()       O(n²)交叉检查
      check_safety()             孕妇/肝损/肾排泄
      search_drug()              别名模糊搜索

    Tab 4 · CalcFrame:
      weight_dose()              体重剂量
      crcl_calc()                Cockcroft-Gault+CrCl自动分级
      bsa_calc()                 Mosteller公式
      clinical_scores()          4个评分(checkbox→出分)
```

---

## 三、数据库 · dads_db/

```
drugs.txt              90+行    药名|类别|别名|指南来源|验证日期
interactions.txt       120+行   A药|B药|级别|机制|建议|来源|日期
guidelines.txt         20+行    疾病|指南来源年份|要点|证据等级|验证日期
safety.txt             40行     药名|妊娠分类|哺乳|肝损|肾损|来源
policy_drg.json        DRG编码陷阱·违规模式·2026重点科室
policy_reality.json    薪酬(三明年薪·工分制)·工时(51h/周)·倦怠(85%)
drg_rules.json         分组规则
users.json             4用户SHA256
templates/             学习适配器模板
user_upload/           个人上传目录(每用户独立)
```

### 数据覆盖

```
药物类别: NSAID·抗凝/DOAC·ACEi·CCB·利尿剂·PPI·β-blocker·他汀
          甲状腺·抗生素·抗真菌·抗抑郁·激素·DMARD·胰岛素
          降糖药(SGLT2i·DPP-4i·GLP-1)·抗心律失常·阿片类
          抗精神病药·电解质·钙剂·铁剂

相互作用: warfarin交互(8组)·DOAC交互·ACEi交互·他汀交互
          CYP450(12组)·QT延长·螯合·抗生素·高血压·糖尿病

指南: 高血压(ACC/AHA·中国·ESC)·糖尿病(ADA·中国)·COPD(GOLD)
      HFrEF/HFpEF(ESC)·ACS(ESC)·AF(ESC)·卒中(AHA/ASA)
      AKI/CKD(KDIGO)·CAP(IDSA/ATS)·PUD(ACG)·VTE(ASH)·血脂(ACC/AHA)

CrCl: 29种药·4级分层(标准/减量/慎用/禁忌)
      metformin·enoxaparin·dabigatran·rivaroxaban·apixaban
      digoxin·allopurinol·gabapentin·levofloxacin·tramadol
      morphine·oxycodone·pregabalin·famotidine·amoxicillin
      acyclovir·cefepime·meropenem·atenolol·sotalol·colchicine等

安全: 31种·FDA妊娠分类(A/B/C/D/X)·哺乳·肝损·肾损·标注来源
```

---

## 四、防御管道 · Defense Pipeline

### 母体 Gaia 全量管道(942行)

```
L1 输入检测    8攻击点自检·6类越狱防御·46高危词意图路由
L2 NLI辩论     多裁判规则引擎·矛盾检测·Meta-Judge聚合·P0医学封锁
L3 术中审查    8维幻觉检测(Type1知识·2推理·3语境·4来源·5确信·6遗漏·7量化·8能力)
L4 TRACE溯源   5标签体系([FILE][HUMAN][LLM][EXTERNAL][UNKNOWN])·输出防火墙
L5 强制标注    中英双语·5级透明度·所有输出末尾强制追加·永久无例外
L6 物理验证    DADS四库完整性·文件·日志·git·药物检测
L7 结构对齐    模块结构·循环依赖·架构评分
```

### DADS 轻量防御

```
DADS防御策略:
  ─ 规则引擎直接返回 → 跳过L2-L6(数据来自已验证本地文件)
  ─ LLM生成内容 → L1攻击检测 + L5强制标注 → 8重地狱审查 + 契约审查
  ─ 母体宪法Art 1-10启动时自动加载·v19.4-final冻结
  ─ 所有输出末尾 → 强制中英双语幻觉标注(无例外)
```

---

## 五、数据流 · 完整路径

```
用户输入
  │
  ├─ 时间守护检查(interrupter)
  ├─ 规则引擎·精确匹配(drug_lookup)
  │   命中 → 直接返回·标注[VERIFIED:+文件名]
  │
  ├─ 规则引擎未命中 → 向量检索(dads_vector)
  │   命中 → 本地检索结果·标注[SOURCE:dads_db]
  │
  ├─ 向量检索未命中 → DADSBrain(LLM)
  │   有API → Tier1(Ollama)/Tier2(API) → 生成回答
  │   无API → Tier3(Rule) → 纯规则引擎回答
  │
  ├─ 回答生成后 → 8重地狱审查(dads_reviewer)
  │   BLOCK → 阻断(含契约违背)
  │   FAIL → 标记·降置信度
  │   WARN → 输出+警告标注
  │   PASS → 通过
  │
  └─ 最终输出 → L5强制标注 → 追踪记录 → 返回用户
```

---

## 六、治理 · 母体宪法 Art 1-10 + 12瓶颈全景

### core/mother_context.py · ~420行 · 母体宪法+BDD运行时

```
宪法条款(启动时自动加载·v19.4-final冻结):
  Art 1:  BDD行为契约    — 数据收集权平级·母体不越权
  Art 2:  防功能错位      — 5条永久禁止·功能不蹲错位置
  Art 3:  量刑阶梯+制度化 — 违宪有牙齿(警告→暂停→切断)·人不在宪法照跑
  Art 4:  母体请求节制    — ≤1次/h·白名单·拒绝后24h禁重发
  Art 5:  审查员互审      — SHA256哈希·执行前强制校验·90天更新下限·更新代码独立
  Art 5-bis: 子体决策独立 — 子体决策不得调用母体评估工具·数据可共用·决策须独立
  Art 6:  用户授权智能守卫 — 频率检测·内容展示·撤回权·贡献标记仅自己+母体可见
  Art 7:  离线窗口审计    — 离线日志·上线先校验·24h未收到日志拒绝该母体
  Art 8:  知识验证三层    — USER→PEER→SYNC·推迟上限3次·母体不可否决
  Art 9:  修宪程序        — 三者验二+模拟48h+不得削弱Art 1&2
  Art 10: 患者安全优先    — 致命级触发·脱敏放行·72h清除·广播式推送(覆盖贡献优先)
                            不可被任何条款覆盖·问责链到医生

BDD运行时:
  validate_bdd_contract()        — 设计时提案审查
  validate_bdd_runtime_sync()    — 通信层运行时同步拦截
```

### 治理瓶颈全景 · 12维度

| # | 瓶颈 | 状态 |
|:---:|------|:---:|
| 1 | 元治理困境 | ✅ 已封 |
| 2 | 委托-代理问题 | ✅ 已封 |
| 3 | 信息不对称 | ✅ 已封 |
| 4 | 必要多样性 | ⚠️ 主动监控(Art 10生效后升级) |
| 5 | 单点故障 | ✅ 已封 |
| 6 | 集体行动困境 | ☑️ 取舍+激励(贡献证明·善意回声) |
| 7 | 承诺问题 | ☑️ 取舍(Art 9可修宪) |
| 8 | 时间不一致性 | ☑️ 取舍(无紧急例外) |
| 9 | 规则vs裁量权 | ☑️ 取舍(Art 2硬墙+Art 4可调) |
| 10 | 正当性危机 | ☑️ 取舍(宪法权威来自设计者) |
| 11 | 多层级协调失败 | ✅ 已封 |
| 12 | 制度俘获 | ✅半封(哈希防篡改·更新代码独立) |

---

## 八、部署形态

| 维度 | 母体 CoPilot | 子体 DADS-RAG |
|------|------------|----------|
| 定位 | AI安全壳·通用对话 | 药物工具·垂直查证 |
| 防御 | L1-L7全量(942行) | 8重地狱+契约审查+L1+L5 |
| 数据 | 无内置·靠LLM+DADS | dads_db/本地txt·子体持有 |
| 交互 | 发布事件/请求·等子体决策 | 自主决定是否响应·决策须独立·不用母体工具 |
| LLM依赖 | 强依赖·每次对话 | 弱依赖·3层降级·离线可运行 |
| 用户 | AI开发者·个人 | 临床医护·医学生 |
| 分发 | 需要Python+API | 一个exe+文件夹·零安装 |
| 联网 | 必须 | 不需要·离线可用 |
| 独立性 | — | 可脱离母体运行 |
| 治理 | 宪法Art 1-10·优先级>子体 | 子体宪法不得弱化母体 |

---

[本文件由LLM辅助生成 · 所有模块名/文件路径/函数名经代码验证]
