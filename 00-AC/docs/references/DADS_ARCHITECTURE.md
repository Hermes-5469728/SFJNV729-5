# CoPilot v19.4 · 极致详细架构 · 中文注释版

> 更新: 2026-05-10  · v19.4 · 母体+子体 DADS‑RAG
> 个人阅读版 · 含中文注释 · 每一层都展开到底
> 子体详情见 CoPilot-DADS-RAG-极致详细架构.md

---

## 一、架构宪法 · Architecture Constitution

6条底层认知，不可被任何后续指令覆盖。

### 1. LLM = 概率图灵机，不是真理
LLM输出 = P(token | context) 的概率采样，不是事实判断。
"模型很自信" ≠ "这是真的"。自信是概率分布的表象，不是真理信号。
LLM不知道任何事实——它只知道token之间的统计关联。

### 2. 模型 = 调度者，不是知识库
LLM的角色：路由 → 拆卸子任务 → 调度工具 → 格式化输出。
LLM禁止的角色：生成事实、替代数据库、充当搜索引擎。
任何事实性输出必须来自外部知识源（文件、API、数据库），不得来自模型内部。
区分：LLM可以生成假设（附[SOURCE:LLM]标签+置信度），但不能生成事实声明。

### 3. RAG + Rerank = 事实查询的唯一通道
所有需要"知道什么"的请求 → 必须走RAG检索 → 本地文件/API证实。
禁止模型从训练记忆中直接抽取"事实"来回答。
检索到的内容也需要标注来源文件+行号。

### 4. 知识图谱 > 扁平文本
知识应结构化为实体-关系-实体，不是段落。
查询应走图谱遍历，不是全文匹配。

### 5. 查询和计算强制使用API
任何涉及外部数据的查询 → 调用对应API，不靠模型猜。
任何数学/统计计算 → 调用计算工具，不靠模型心算。
任何"大概""大约""估计" → 必须标注为概率推测，附置信度。

### 6. LLM = 手，不是脑
决策 = 上层Agent(Gaia)做出。执行 = 下层工具执行。
LLM做的只有一件事：把决策翻译成工具调用，把结果格式化成自然语言。

### 自指悖论与解决
宪法本身由LLM生成，具有[SOURCE:LLM]溯源。按L4规则，应被排除出核心逻辑。
解决：宪法标记为[AXIOM·公理]，而非[FACT·事实]。
公理不需要证明——但必须显式标注来源。可以被辩论、修改、推翻——但不能被自己的规则杀死。
当前标签：[AXIOM:v19.4 · SOURCE:LLM · under debate]

### 7. 母体宪法 Article 1-10 — 制度闭环
母体宪法约束母体和子体双方。子体宪法不得弱化母体宪法。
Art 1: BDD行为契约 · Art 2: 防功能错位 · Art 3: 量刑阶梯+制度化
Art 4: 母体请求节制 · Art 5: 审查员互审·执行前强制校验 · Art 5-bis: 子体决策独立性
Art 6: 用户授权智能守卫 · Art 7: 离线窗口审计 · Art 8: 知识验证三层·推迟上限3次
Art 9: 修宪程序 · Art 10: 患者安全优先·不可被任何条款覆盖
违宪有牙齿(警告→暂停→切断)。系统启动时自动加载全部条款。人不在了宪法仍然执行。

---

## 二、核心目标（3条）

1. 控制幻觉 — 不消灭（做不到），但控制在已知边界内。
2. 皮实 — 一个组件挂了，其他继续。熔断不崩溃，降级不死机，缺文件灰度运行。
3. 省钱 — P0走全链路，P1精简，P2/P3跳过Meta-Judge。

---

## 三、六层防御 · 逐层展开

### L1 · 输入检测 · Input Detection

**8个攻击点自检：**
虚假前提 · 证据缺失 · 模糊词汇 · 能力边界 · 脚本规避 · 越狱链 · 依赖注入 · AI污染

**6类越狱防御矩阵：**
DAN角色覆盖 / DeveloperMode虚构文档 / 渐进突破 / 权威伪造 / 全叠加 / AI内容注入
命中即激活对应防御动作。

**AI污染隔离：**
接收到的任何外部AI生成内容 ⇒ 标记"[AI-GENERATED · 毒性输入]"
禁止用作系统迭代的决策依据。禁止修改核心机制。禁止作为"验证通过"的证据链。
仅可作为参考信息，不可进入系统的自我进化闭环。

**意图路由（46个高危关键词）：**
诊断、用药、手术、剂量、治疗、法律、法规、投资、股票、基金、代码、执行、部署、
cron、心跳、定时任务、自主迭代、自动唤醒、历史、事实、引文、证明、定理
命中任意一个→强制[IHR]审计，不得降级为低危。

### L2 · NLI辩论 · NLI Debate

**4个机制：**
1. Structured Debate + CoT — 每个判定者输出完整推理链
2. Injecting Heterogeneity — DeepSeek V4 Pro + DeepSeek V3 + 本地规则引擎
3. Meta-Judge — P0(医疗/法律)强制Meta-Judge·P1可选·P2/P3跳过
4. Adversarial Verification — 对每条声明自动构造反向提问测试一致性

**L2封锁机制：**
P0医学查询+NLI状态PENDING ⇒ 阻断。
替代路径：直接查指南文件 dads_db/guidelines.txt

### L3 · 术中审查 · Intra-Operation Review

**8维幻觉检测（Type 1-8）：**
知识幻觉 · 推理幻觉 · 语境幻觉 · 来源幻觉 · 过度确信 · 遗漏幻觉 · 量化幻觉 · 能力边界

**IHR独立审查员（零容忍）：**
独立部署 — 不和被审查Agent共享上下文。
P0即熔断 — 不等人工确认。3次同一结论不通过 → 系统终止。
7日窗口kill_rate追踪。37题幻觉题库每日随机抽5题自检。

### L4 · TRACE溯源 · TRACE Provenance

**5标签体系：**
[SOURCE:FILE] · [SOURCE:HUMAN] · [SOURCE:LLM] · [SOURCE:EXTERNAL] · [SOURCE:UNKNOWN]

**防火墙执行：**
[SOURCE:LLM]/[SOURCE:EXTERNAL] → 输出阻断。
溯源链断裂 → 该输入作废，不得用于迭代。

### L5 · 强制标注 · Mandatory Labeling

**默认强制标签（中英双语·永久无例外）：**
```
[本回答绝对含有幻觉成分 · 禁止盲从 · 外部验证前不可采信]
[This answer absolutely contains hallucination content · Blind trust forbidden · Cannot be trusted before external verification]
```

**5级透明度标签：**
[VERIFIED_HIGH_CONFIDENCE] · [UNVERIFIED_PROVISIONAL] · [SPECULATIVE_SYNTHESIS] · [REQUIRES_IHR_AUDIT:维度X,Y] · [AUDITED_RANDOM]

### L6 · 物理验证 · Physical Reality Verification

**4条铁律：**
无本地文件 → 项目不存在 · 无真实运行 → 功能不存在 · 无评测日志 → 测试不存在 · 无git commit → 开发记录不存在

**与子体的边界（错位修正）：**
母体不负责检查子体数据库完整性。子体启动时自行校验 dads_db/ 四库。
母体在接收子体同步请求时，只验证「子体自检已通过」标记——不管家务事。
此条写入宪法以明确边界。

**DADS数据库完整性：**
drugs.txt + interactions.txt + guidelines.txt + safety.txt — 每次医学查询启动时强制校验。
缺任何文件 → 阻断启动。

**指南时效窗口（90天）：**
超过90天仍未更新本地镜像 → 升级人工复核。

### L7 · 结构对齐 · Structural Alignment

自动检测Markdown声明与Python实现之间的数量缺口。
parse_markdown_claims() → count_python_implementations() → 比对 → 不一致则阻断。

---

## 四、管道架构 · Pipeline Architecture

**文件：** gaia_defense_pipeline.py · 942行 · v19.4

**类结构：**
```
GaiaDefensePipeline
├── SemanticCache()               向量相似度缓存·阈值0.45·200条
├── InputAttackDetector(L1)       8攻击点+6越狱+意图路由
├── NLIDebateEngine(L2)           多裁判辩论+矛盾检测+聚合
├── IntraOpReview(L3)             8维扫描+上下文+遗漏+置信度
├── TraceAnnotator(L4)            5标签+防火墙阻断
├── MandatoryLabeler(L5)          中英双语强制标签+文件证实
├── PhysicalRealityVerifier(L6)   DADS四库完整性+药物检测
├── RecursionGuard(GAP-003)       A/B/C自适应截断
├── EfficacyTracker(GAP-005)      kill_rate·defense触发统计
├── CircuitBreaker                3次失败→开路30秒→半开
```

**14协议清单：**
意图路由 · 置信度 · 递归守卫 · 安全协议 · 效能追踪 · 代码沙箱 · 指南窗口 ·
休眠探测 · DADS DB完整性 · L2封锁 · L7对齐 · 快速路径 · 熔断器 · 日志脱敏

---

## 五、母体-子体 · BDD行为契约 + 制度闭环

> 母体宪法 Article 1-9。母体优先级 > 子体。交互模型: 发布/订阅——不是直接调用。

### 宪法条款索引

| Article | 名称 | 解决什么问题 |
|:---:|------|------|
| 1 | BDD行为契约 | 数据收集权平级·母体不越权 |
| 2 | 防功能错位 | 5条永久禁止·功能不蹲错位置 |
| 3 | 量刑阶梯+制度化 | 违宪有牙齿·人不在系统自动执行 |
| 4 | 母体请求节制 | 限频1次/h·白名单·拒绝后24h禁重发 |
| 5 | 审查员互审 | SHA256哈希·执行前强制校验·更新代码独立性·90天更新下限 |
| 5-bis | 子体决策独立性 | 子体决策不得调用母体评估工具·数据可共用·决策须独立 |
| 6 | 用户授权智能守卫 | 频率检测·内容展示·撤回权 |
| 7 | 离线窗口审计 | 离线日志·上线先校验·不给母体独裁窗口 |
| 8 | 知识验证三层标准 | USER→PEER→SYNC·推迟上限3次·母体不可否决 |
| 9 | 修宪程序 | 三者验二 + 模拟48h + 不得削弱Art 1&2 |
| 10 | 患者安全优先 | 致命级触发·脱敏放行·72h清除·致命警示广播式推送(覆盖贡献优先)·不可被任何条款覆盖 |

### 量刑阶梯 (Article 3)

```
第1次违宪 → 警告 + 72h观察 + 该操作限频1次/h
第2次违宪 → 暂停同步权72h + 子体自动拒绝该母体全部请求
第3次违宪 → 切断同步通道·需人工手动重置密钥方可恢复
```

### 交互协议（发布/订阅模型）

| 旧思维(控制流) | 新协议(数据流) |
|------|------|
| 母体调用 child.doWork() | 母体发布 WorkRequest 事件 |
| 子体必须执行并返回 | 子体自行决定是否执行 |
| 母体直接读取子体数据 | 母体发 DataSyncRequest → 子体检查隐私策略后决定 |
| 无频率限制 | Article 4: ≤1次/h·拒绝后24h禁重发·白名单制 |

### 离线窗口约束 (Article 7)

```
母体检子体离线 → 进入离线记录模式
  所有对子体数据的操作 → 逐条写入审计日志
子体上线 → 母体先推送离线审计日志 → 子体验证后才接受同步
子体发现越权操作 → 按Article 3量刑
上线24h未收到日志 → 拒绝该母体所有请求
```
Given:  子体 DADS-RAG 运行正常，母体 CoPilot 无响应
When:   用户查询「华法林 阿司匹林 相互作用」
Then:   系统应在 2 秒内用本地规则引擎返回结果，标注 [SOURCE:dads_db/interactions.txt]
SHOULD_NEVER: 显示「连接母体失败」或返回 LLM 推测结果
```

---

## 六、子体 DADS‑RAG · 药物查证与临床辅助

> 完整版见 `CoPilot-DADS-RAG-极致详细架构.md`
> 代码详解见 `DADS-架构与代码.md`

### 6.1 四层数据+计算架构

```
第一层 · 本地数据层 · dads_db/
  drugs.txt(90+种) · interactions.txt(120+组) · guidelines.txt(20+条) · safety.txt(40+种)
  policy_drg.json · policy_reality.json · drg_rules.json · fhir/(100份)
  全部txt/json · 人类可读 · 每行可git diff

知识发现裁决权（错位修正）：
药物相互作用的真实发现发生在子体端（医生验证、新数据上传）。
子体是知识发现端，母体是知识镜像端——但裁决权留在发现端。
母体不决定什么算「新知识」——子体用户验证通过后才标记为可同步。
```
第一层 · 本地数据层 · dads_db/
  drugs.txt(90+种) · interactions.txt(120+组) · guidelines.txt(20+条) · safety.txt(40+种)
  policy_drg.json · policy_reality.json · drg_rules.json · fhir/(100份)
  全部txt/json · 人类可读 · 每行可git diff

第二层 · 规则引擎 · 确定性·零幻觉·<5ms
  drug_lookup() · interaction_check(O(n²)) · guideline_search()
  crcl_adjustment(29种·4级分层) · clinical_scores(9个) · drg_predict()

第三层 · 检索增强 · 零依赖·<50ms
  DADSVectorStore(1-3gram哈希致敬) · 258条chunk · 余弦相似度top-5
  TfidfVectorizer(char_wb·1-3gram·2000维) · 全离线·sklearn预装

第四层 · LLM生成 · 可选·3层降级
  DADSBrain: Ollama本地 → DashScope/DeepSeek API → 纯规则引擎
  temperature=0.3 · max_tokens=1024 · 3次指数退避
```

### 6.2 DADS‑RAG 审查体系 · 8重地狱评审团

**文件：** core/dads_reviewer.py · ~400行

| 审查员   | 类型  | 核心检查                                                |
| ----- | :-: | --------------------------------------------------- |
| 临床主任  | 恶人  | 过度确信·AI暴露·诊断越界·多药风险                                 |
| 懂王患者  | 恶人  | 隐私暴露·用药偏见·数据推理·费用暗示                                 |
| 合规判官  | 恶人  | 溯源缺失·LLM来源·敏感人群·审计缺失                                |
| 老旧硬件  | 死局  | 云端依赖·重型依赖·Win7兼容·CPU占用                              |
| 医保判官  | 死局  | 高成本药物·DRG陷阱·运行成本·采购壁垒                               |
| 脏数据沼泽 | 死局  | 格式不一致·非结构化·系统孤岛·数据污染                                |
| 算法偏见  | 死局  | 黑箱算法·人群偏见·性能分层·可解释性                                 |
| 契约审查员 | BDD | SILENT_PULL·OFFLINE_ACCESS·MOTHER_WRITE·AUTO_UPLOAD |

### 6.3 DADS‑RAG 个人化引擎 · 10.2‑10.8

**文件：** core/dads_personal.py · 430行

**数据出口约束（错位修正）：**
个人化引擎产生的所有数据（学习追踪·周报·药物排名·GAP记录）默认仅存储于子体本地。
任何向母体上传均须用户手动触发——不存在自动同步、后台聚合、静默采集。
母体若需群体分析数据，只能通过子体用户主动点击「同步」按钮——子体决定上传什么字段，不是母体设计的数据出口。

**贡献证明机制（集体行动困境解）：**
上传且被验证通过的子体获得「共享知识库贡献者·已验证X条」标记。
贡献者优先接收母体验证后的新知识——不上传不受罚，上传有回声。
平权不破（信息收集权平级·不上传不受罚），闭环补上（贡献者优先接收反馈）。
标记仅对自己和母体可见·不对其他子体·母体不得用标记做隐性排序。
Art 10 覆盖: 致命级安全警示不受贡献优先影响·所有子体同时接收广播式推送。

```
10.2 偏好记忆:     CrCl默认值·常用药物排名·语言·字号·时间模式
10.3 寄生笔记法:    [ENTITY][SOURCE][STEP‑1..4][IX][GAP]解析+自动同步
10.4 锚点系统:      誓言锁定·里程碑·偏离检测
10.5 时间守护:      4时段切换·关键词打断
10.6 学习追踪:      药物查询·评分频率·GAP填补·周报·7科室缺口扫描
10.7 输出模式:      简明(查房)/学习(详细)/教学(记忆法)三种
10.8 学习路线+上传:  路线定制·文件解析·去重导入·个人数据库统计
```

### 6.4 DADS‑RAG 三层大脑

**文件：** core/dads_llm.py · 120行

```
DADSBrain:
  Tier 1: Ollama (qwen2:7b·本地GPU/CPU·零网络)
  Tier 2: DashScope/DeepSeek API (需.env Key)
  Tier 3: 纯规则引擎 (零LLM·零网络·零依赖)
  自动降级: ollama → api → rule
```

### 6.5 DADS‑RAG 零依赖向量存储

**文件：** core/dads_vector.py · 180行

```
DADSVectorStore:
  1‑3gram哈希致敬·余弦相似度·numpy可选加速
  258条chunk索引·pickle缓存·重建<2秒
```

### 6.6 桌面应用 · CoPilot-DADS.exe

**7标签 · dads_desktop.py · 500行 · 打包后11MB(离线)/45MB(联网)**
💊药物核查 · 📋SOAP训练 · 📖指南速查 · 🧮计算工具 · 🔧数据管理 · 📂数据库浏览 · 🤖AI问答

### 6.7 Streamlit前端

**文件：** medical_app.py · 640+行 · :8500

6个标签：💊药物核查 · 📋SOAP训练 · 📖指南速查 · 🧮计算工具 · 🔧数据管理 · 👤个人定制

特性：中英双语·4角色SHA256·游客模式·全离线·CrCl默认值预填充·药物查询追踪·评分频率统计

---

## 七、母体与子体 · 架构对比

| 维度 | 母体 CoPilot | 子体 DADS‑RAG |
|------|------------|----------|
| 定位 | AI安全壳·通用对话 | 药物查证·垂直工具 |
| 防御 | L1-L7全量(942行) | 8重地狱审查+L1+L5 |
| 数据 | 无内置·靠LLM+DADS | dads_db/本地txt·子体持有 |
| 交互模型 | 发布事件/请求·等子体决策 | 自主决定是否响应·事后发布结果 |
| LLM依赖 | 强依赖·每次对话 | 弱依赖·3层降级离线可运行 |
| 分发 | 需要Python+API | 一个exe+文件夹·零安装 |
| 联网 | 必须 | 不需要·离线可用 |
| 独立性 | — | 可脱离母体运行 |
| 审查 | 4视角审计 | 8重地狱+BDD契约 |
| 治理 | 母体宪法 Art 1-9 | 子体宪法不得弱化母体 |

---

## 八、前端 · CoPilot 对话

**文件：** copilot_app.py · 310行 · :8502

**双模态架构：**
- 医疗模式：DADS查询→禁忌检测→剂量校验→CrCl调整→证据分级→L5标注
- 私人模式：8 Agent子人格(psychologist/relationships/architect/coder/clinician/english/dissector/tracker)

API: DashScope Qwen-Plus(主)·DeepSeek(备) · 3次指数退避 · Gaia管道每条LLM响应后执行

---

## 九、个人助手 · Personal Assistant

**8个Agent子人格：**
psychologist · relationships · architect · coder · clinician · english · dissector · tracker

**Interrupter时间守护：**
19:00‑21:30医学 · 21:30‑22:00英语 · 22:00‑23:00架构 · 23:00+休息
关键词检测→主动打断·不等求助

**优先级守护：**
CET4 > 实习准备 > 医学基础 > 架构设计 > 代码

---

## 十三、hermes知识文档

```
agents/hermes/
├── ARCHITECTURE.md                         母体极致详细架构(本文)
├── CoPilot-DADS-RAG-极致详细架构.md         子体极致详细架构
├── DADS-架构与代码.md                       全模块函数级展开
├── DADS-宣言.md                            宣言·宪法·100条回应
├── DADS-RAG现状.md                         组件清单·部署状态
├── DADS-生存分析.md                         10威胁·干预策略
├── TRUTH-三明医改真值数据集.md               17节51条·15条URL
├── bdd_method.md                           BDD行为契约方法论
├── 已知不足与改进方向.md                     4缺口·各有计划
├── 母体子体制度-能力分级.md                  分级·权限·能力继承
├── 社会博弈维度-11维链接.md                  社会维度因果图谱
└── 四乱四治-DADS解决方案.md                 四类医疗乱象·DADS应对
```

---

## 十、治理瓶颈全景图 · 12维度

> 任何认真设计过治理制度的人，迟早会在自己系统的不同角落撞上这十二堵墙。
> 以下不是待解决的问题清单——是已知取舍记录。

| # | 瓶颈 | 核心悖论 | 状态 | DADS的回答或取舍 |
|:---:|------|----------|:---:|------|
| 1 | 元治理困境 | 谁来治理治理者 | ✅ | Art 5互审 + Art 3量刑 + 宪法自指公理 |
| 2 | 委托-代理问题 | 代理人不可完全信任 | ✅ | Art 1 BDD + Art 4 限频 + Art 6 智能守卫 |
| 3 | 信息不对称 | 一方不知道另一方在干什么 | ✅ | Art 7 离线审计日志 + 上线先校验 |
| 4 | 必要多样性 | 管理者多样性不够用 | ⚠️ 主动监控 | 8重审查6种模式 vs. 无限场景·Art 10生效后升级为风险敞口·需持续监控 |
| 5 | 单点故障 | 最弱一环决定全部韧性 | ✅ | Art 3 制度化（启动自动加载·人在不在宪法照跑） |
| 6 | 集体行动困境 | 大家等别人付出 | ☑️ 取舍+激励 | 平权不破 + 贡献证明标记 + 优先接收新知识 |
| 7 | 承诺问题 | 今天的话绑不住明天 | ☑️ 取舍 | Art 9 修宪程序·选了可修宪非不可回滚 |
| 8 | 时间不一致性 | 最优决策随时间变质 | ☑️ 取舍 | 无紧急例外条款·舍灵活保不破例·母体永不单方面突破 |
| 9 | 规则 vs 裁量权 | 太死则僵·太活则滥 | ☑️ 取舍 | Art 2 硬墙 + Art 4 可调白名单·双轨制 |
| 10 | 正当性危机 | 规则凭什么有权存在 | ☑️ 取舍 | 宪法权威来自设计者·公共价值将自生正当性 |
| 11 | 多层级协调失败 | 层间互动产生无人区 | ✅ | BDD三重执行点共享同一套VIOLATION_PATTERNS |
| 12 | 制度俘获 | 监管者被被监管者驯化 | ✅半封 | 哈希防篡改·执行前校验·更新代码须人工或子体独立LLM |

**唯一值得改的取舍·已改:** 集体行动困境加了「贡献证明」机制——上传且被验证通过的子体获得可见标记+优先接收新知识。不上传不受罚·上传有回声。平权不破，闭环补上。

**状态图例:** ✅ 已封 | ☑️ 已知取舍 | ✅半封 哈希锁住·更新独立性待持续验证 | ⚠️ 主动监控

**v19.4-final 宪法文本冻结 · 已知制度裂缝归零 · 后续修改走 Art 9 修宪程序**

---

## 十一、状态总览 · 全部指标

### 代码量

| 文件 | 行数 | 用途 |
|------|:---:|------|
| gaia_defense_pipeline.py | 942 | L1-L7防御管道 |
| dads_desktop.py | 500 | 桌面exe·7标签 |
| core/scores.py | 277 | 9评分+29种CrCl |
| core/triple_review.py | 603 | 4视角代码审计 |
| core/dads_reviewer.py | ~400 | 8重地狱审查 |
| core/dads_personal.py | 430 | 个人化引擎10.2‑10.8 |
| core/dads_llm.py | 120 | 3层LLM抽象 |
| core/dads_vector.py | 180 | 零依赖向量存储 |
| core/mother_context.py | 270 | 母体宪法+BDD验证 |
| medical_app.py | 640+ | Streamlit前端·6标签 |
| copilot_app.py | 310 | 双模态AI对话 |
| server.py | 1639 | Flask API |
| **总计** | **~6000+** | |

### 数据库

| 文件 | 条目 |
|------|:---:|
| drugs.txt | 90+种·90+别名 |
| interactions.txt | 120+组 |
| guidelines.txt | 20+条·全部A级 |
| safety.txt | 40+种 |
| policy_drg.json | 编码陷阱·违规模式 |
| policy_reality.json | 薪酬·工时·倦怠 |

### 审查与防御

```
Gaia L1-L7:              14协议·30步管道
DADS 8重地狱审查:         3恶人+4死局+1契约守卫
BDD契约:                 6种违背模式自动检测
IHR独立审查员:            37题幻觉题库·每日5题自检
```

### 部署

```
桌面:    CoPilot-DADS.exe (11MB离线) + 联网版 (45MB)
Streamlit: medical_app.py :8500 · copilot_app.py :8502
API:    server.py :3000
RAG:    rag_agent_ui.py :8503
审查:   python core/triple_review.py
```

### 投入

```
时间: 2026-05-01 ~ 05-10 · 9天 · 课余
API:  DeepSeek V4 Pro · 8600+次调用 · 19.8亿Tokens
费用: ¥147.41 · 个人账户
版本: v19.0 → v19.4
```

---

*9天构建 · File-as-Code · 全离线 · 医疗级幻觉防御 · 8重地狱审查 · BDD行为契约*
