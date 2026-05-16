# Atelier SDK · 架构图 · 人话版

> 生成时间: 2026-05-12 · 抽屉: 00-hermes/SDK · 来源原则: ARCHITECTURE-HUMAN.md v1.1

---

## 一、SDK 的定位：连接两条轨道的胶水

```
 ┌──────────────────────────────────────────┐
 │          Atelier 两条并行轨道              │
 │                                          │
 │  轨道一: 独立项目 (Standalone)             │
 │  ┌────────────────────────────────┐      │
 │  │ AtlasCore v1.0                 │      │
 │  │ ├── DecisionEngine             │      │
 │  │ ├── InfoProcessor + RAG        │      │
 │  │ ├── Personal Assistant         │      │
 │  │ └── Creative Workshop          │      │
 │  │ 零网络 · 零依赖平台              │      │
 │  └───────────┬────────────────────┘      │
 │              │                           │
 │     ╔════════╧════════╗                  │
 │     ║   AC SDK 胶水层  ║                  │
 │     ║  只做翻译和透传   ║                  │
 │     ╚════════╤════════╝                  │
 │              │                           │
 │  轨道二: 平台 1+N (Platform)              │
 │  ┌────────────────────────────────┐      │
 │  │ ac_platform · FastAPI :8000     │      │
 │  │ ├── src/core/   (禁区)          │      │
 │  │ ├── src/modules/ (N模块)        │      │
 │  │ ├── src/shared/  (公共库)        │      │
 │  │ └── PostgreSQL (统一数据)        │      │
 │  └────────────────────────────────┘      │
 └──────────────────────────────────────────┘
```

**SDK 只做三件事:**

```
    独立项目                      SDK                       平台 1+N
    ────────                    ─────                      ────────
    发请求  ───→  翻译成 HTTP  ───→  路由到对应模块
    收结果  ←───  包装成对象   ←───  API 返回 JSON
    调能力  ───→  选择本地/远程  ───→  本地优先·远程兜底
```

---

## 二、SDK 内部分层

```
┌─────────────────────────────────────────────────────────────┐
│                      AC SDK v1.0                            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ L4: 应用层 · SDK 对外暴露的 API                       │   │
│  │   ACClient.medical.check_drugs("warfarin+aspirin")    │   │
│  │   ACClient.content.search("tdd")                     │   │
│  │   ACClient.personal.get_profile(user_id)             │   │
│  └────────────────────────┬────────────────────────────┘   │
│                           │                                 │
│  ┌────────────────────────┴────────────────────────────┐   │
│  │ L3: 路由层 · 智能路由 本地 vs 远程                    │   │
│  │   if offline:                                        │   │
│  │       → AtlasCore.engine.rules.interaction_check()   │   │
│  │   else:                                              │   │
│  │       → HTTP POST /api/v1/medical/interactions       │   │
│  │   rule: 本地 DADS 数据库优先, 平台 DB 兜底           │   │
│  └────────────────────────┬────────────────────────────┘   │
│                           │                                 │
│  ┌────────────────────────┴────────────────────────────┐   │
│  │ L2: 翻译层 · 对象 ↔ JSON 双向转换                     │   │
│  │   InteractionResult → Dict → JSON                    │   │
│  │   API Response → Dict → DrugSchema                   │   │
│  │   零逻辑 · 纯数据变换                                  │   │
│  └────────────────────────┬────────────────────────────┘   │
│                           │                                 │
│  ┌────────────────────────┴────────────────────────────┐   │
│  │ L1: 传输层 · HTTP 客户端 + 熔断 + 重试                │   │
│  │   requests.Session() / httpx.AsyncClient()           │   │
│  │   3次指数退避 · 30s 熔断 · 离线模式降级               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ═══════════════════════════════════════════════════════    │
│  │  Gaia 防御 · SDK 层不重复, 继承平台 L1-L7               │   │
│  │  所有远程响应自带 L5 强制标签                            │   │
│  │  本地规则引擎输出无需标签 (因为 0 LLM 参与)              │   │
│  ═══════════════════════════════════════════════════════    │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、SDK 模块映射

```
独立项目模块              SDK 方法                          平台 N 模块
──────────              ────────                         ──────────
DecisionEngine.router   → ACClient.query()               → POST /api/v1/query
InfoProcessor.retrieve  → ACClient.search()              → GET /api/v1/content/references?q=
ClinicalScores          → ACClient.medical.scores()      → GET /api/v1/medical/scores
DrugLookup              → ACClient.medical.drug()         → GET /api/v1/medical/drugs?name=
InteractionCheck        → ACClient.medical.interact()     → GET /api/v1/medical/interactions
GuidelineSearch         → ACClient.medical.guideline()    → GET /api/v1/medical/guidelines
CreativeCanvas          → ACClient.content.asset()        → POST /api/v1/content/assets
LearningTracker         → ACClient.personal.report()      → (本地仅存储, 不上传)
```

**红线: 不上传的数据 — 永久留在本地:**
- 个人学习追踪 → 仅 `dads_personal.py` 本地存储
- 临床笔记 → 仅用户手动触发同步
- 贡献标记 → 仅子体自行发布

---

## 四、SDK 调用流程 (以药物相互作用为例)

```
用户: "华法林和阿司匹林能一起吃吗?"

  ┌──────────┐
  │AtlasCore │
  │.process()│
  └────┬─────┘
       │
       ├──→ DecisionEngine.route()       检出: 医疗查询
       │
       ├──→ GaiaDefensePipeline.process() L1-L7 防御
       │       L1: 无攻击 → PASS
       │       L2: P0 医疗 → Meta-Judge
       │       L3: 8维扫描 → PASS
       │
       ├──→ ACClient.medical.interact("warfarin","aspirin")
       │       │
       │       ├── 本地可用? 
       │       │   YES → RuleEngine.interaction_check() 
       │       │         → "CONTRAINDICATED" [SOURCE:drugs.txt]  < 5ms
       │       │
       │       └── 本地不可用?
       │           → POST /api/v1/medical/interactions
       │           → {"drug_a":"warfarin","drug_b":"aspirin"}
       │           → Response: {severity:"CONTRAINDICATED", ...}
       │           → L5 标签自动附加 ←── 平台侧中间件
       │
       └──→ 返回结果 + SOURCE 标注 + L5 强制标签
```

---

## 五、Gaia 防御在 SDK 中的部署位置

```
                    ┌──────────────────────┐
用户输入            │ 独立项目 (本地)       │
    │               │                      │
    ├──→ L1 输入检测   │ 8类攻击 + 46关键词   │
    ├──→ L2 NLI 辩论   │ 3裁判 + Meta-Judge  │
    ├──→ L3 术中审查   │ 8维幻觉扫描          │
    ├──→ L4 溯源标注   │ [SOURCE:xxx] 打标    │
    │               │                      │
    │  ╔═══════════╧══════════════╗       │
    │  ║  需要远程数据?             ║       │
    │  ╚═══════════╤══════════════╝       │
    │               │                      │
    │  [NO] 本地规则引擎                    │
    │   → 直接返回, 零标签                  │
    │                                      │
    │  [YES] 走 SDK → 平台                 │
    │                      ┌───────────────┴──────────┐
    │                      │ 平台 1+N (远程)            │
    │                      │                          │
    │                      ├──→ L5 强制标注中间件       │
    │                      │    响应的 detail/message   │
    │                      │    自动注入 L5 中英双语     │
    │                      │                          │
    │                      ├──→ L6 物理验证              │
    │                      │    数据表是否存在           │
    │                      │                          │
    │                      └──→ L7 结构对齐              │
    │                          模型注册数 = 声明数      │
    └──────────────────────────────────────────────────┘
```

**原则:**
- L1-L4 在 SDK 调用前执行 (本地)
- L5-L7 在平台 API 层执行 (远程)
- 本地规则引擎输出 → 不标注 (0 LLM 参与, 无条件幻觉)
- 远程 API 输出 → 强制标注 (经过了 LLM 或数据库查询)

---

## 六、SDK 目录结构

```
ac_platform/
├── main.py
├── sdk/                          ← SDK 包, pip install 后可用
│   ├── __init__.py
│   ├── client.py                 ← ACClient 统一入口
│   ├── router.py                 ← L3 智能路由 (本地优先)
│   ├── transport.py              ← L1 HTTP 传输 + 熔断 + 重试
│   ├── translate.py              ← L2 对象 ↔ JSON 转换
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── medical.py            ← ACClient.medical.*
│   │   ├── content.py            ← ACClient.content.*
│   │   └── personal.py           ← ACClient.personal.*
│   └── config.py                 ← API_BASE_URL, TIMEOUT, 熔断参数
└── src/                          ← (不变, 已有目录)
```

---

## 七、核心类: ACClient

```python
class ACClient:
    """SDK 统一入口 · 智能路由本地/远程"""

    def __init__(self, base_url="http://localhost:8000",
                 offline_mode=False,
                 local_atlas=None):
        self.transport = HTTPTransport(base_url)    # L1
        self.translator = DataTranslator()           # L2
        self.router = SmartRouter(offline_mode)      # L3
        self.local_atlas = local_atlas or AtlasCore()

        # 子模块
        self.medical = MedicalModule(self)
        self.content = ContentModule(self)
        self.personal = PersonalModule(self)

    def query(self, user_input, context=None):
        """通用查询入口 · 走 Gaia 防御 → 路由 → 返回"""
        # L1-L4 防御
        defense = self.local_atlas.defense.process(user_input, context)
        if defense.get("blocked"):
            return {"blocked": True, ...}

        # L3 路由: 本地 or 远程
        intent = self.local_atlas.decision.router.route(user_input)

        if intent == "medical_drug_check":
            return self.medical.interact(user_input)
        elif intent == "knowledge_search":
            return self.content.search(user_input)
        else:
            return self.transport.post("/api/v1/query", {...})
```

---

## 八、SDK 与平台间的契约 (不变量)

```
1. SDK 不持有数据库连接 → 所有 CRUD 走平台 API
2. SDK 不做业务逻辑 → 只做路由 + 翻译 + 传输
3. 本地能力优先 → 离线可用是第一优先级
4. 远程响应必带 L5 标签 → 由平台中间件保证
5. 不上传数据永久本地 → personal 模块数据仅 SDK 本地
6. SDK 升级不破坏平台 → 接口版本化 /api/v1/ /api/v2/
7. 熔断不崩溃 → 平台挂了, SDK 降级到本地规则引擎
```

---

## 九、SDK vs LangGraph vs Dify 的定位

```
                        Dify                    LangGraph              AC SDK
                        ────                    ────────              ──────
定位                    业务人员搭流程            工程师搭系统            架构师自己的胶水
多AI调度                拖动节点配置              Python状态图            本地优先+远程兜底
防御集成                无                       需手动编码              继承 Gaia L1-L7
离线能力                弱                       弱                     强(本地规则引擎)
学习曲线                低                       中                     低(调用已有能力)
与你架构的匹配度         不适合                   适合但重              天然一体
```

---

## 十、下一步: SDK 最小实现

```
sdk/
├── __init__.py          import ACClient
├── client.py            50行 · 统一入口
├── router.py            70行 · 智能路由
├── transport.py         60行 · HTTP + 熔断
├── translate.py         40行 · JSON ↔ 对象
└── modules/
    ├── medical.py        80行 · 药物·相互作用·指南·评分
    └── content.py        50行 · 创意素材·参考资料
```

**总代码量:** ~350行 · 零新依赖 · 继承已有 Gaia

---

*AC SDK v1.0 Draft · 4 层结构 · 7 条不变量 · 2 个模块入口 · 零新依赖*
