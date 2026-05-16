# DADS → AC Platform · 演进溯源

> 从 CoPilot DADS（医疗 AI）到 AC Platform（通用调度平台）的架构演进映射

---

## 一、概念对应表

| DADS（v19.4） | AC Platform | 演进说明 |
|---------------|-------------|---------|
| 母体 CoPilot | 1 · 核心平台 | 统一入口 + 治理管道 |
| 子体 DADS-RAG | N · 独立模块 | 可插拔子模块 |
| 宪法 6 条 | AGENTS.md 关键不变量 | 底层认知/约束不可覆盖 |
| Gaia Defense (L1-L7) | Governance Pipeline | 多层检查从 7 层简化为 4 层 |
| L5 强制标注 | L5 标注模块 | 保留，格式从医学版泛化 |
| 8 Agent 子人格 | 24 Expert Dispatch | 从硬编码到 trigger 匹配 |
| TraceAnnotator(L4) | Governance 溯源检查 | 标签机制保留 |
| PhysicalVerifier(L6) | EAV 锚点比对 | 从文件存在性到事实核验 |
| BDD 行为契约 | Collaborative Governor 契约验证 | 从医疗约束到通用接口契约 |
| 本地 TXT 数据库 | ac_platform.db | 从纯文本到 SQLite 结构化 |
| 双模态（医疗/私人） | 双流（流A/流B） | 从领域划分到复杂度划分 |
| TF-IDF 检索 | Case Center ChromaDB | 从传统检索到向量检索 |
| 宿舍规则引擎 | Orchestrator 状态机 | 从静态规则到动态编排 |
| v19.0 → v19.4 / 9天 | 当前版本 | 迭代方法论延续 |

---

## 二、DADS 独有 · AC 未覆盖

以下 DADS 能力尚未在 AC 中实现：

| 能力 | DADS 实现 | 是否值得加入 AC |
|------|-----------|---------------|
| 离线 exe 部署 | PyInstaller 打包，双击即用 | 是 — CLI 目前依赖 Python 环境 |
| 药物剂量计算 | CrCl / CHA2DS2-VASc 评分引擎 | 视需求定（医学专用） |
| DRG 违规检测 | 医保编码规则引擎 | 视需求定（医学专用） |
| 8 重地狱内容审查 | 多维度安全过滤 | 是 — 可补充 AC 的 security check |
| 四视角代码审计 | 架构/安全/性能/可维护性 | 是 — 可补充 QA 模块 |

---

## 三、AC 独有 · DADS 没有

| 能力 | AC 实现 |
|------|---------|
| 多轮编排 (Orchestrator) | 13 态状态机 + 依赖树调度 |
| HITL 人在回路 | 中断/确认/选择/审核 |
| 13 态状态机 | CREATED → COMPLETED 全生命周期 |
| 自动回滚 | 逆序依赖清理 |
| 熔断器 + 心跳 | 系统自我保护 |
| EAV 锚点引擎 | 确定性事实核验 |
| 24 专家系统 | P1-P5 优先级匹配 |
| 真值知识库 | 90 条已验证知识 |

---

## 四、文件索引

```
00-AC/docs/references/
├── DADS_ARCHITECTURE.md        ← 母体宪法 + L1-L7 详细展开
├── DADS_极致详细架构.md         ← 子体视角，四层架构逐层到底
├── DADS_母体子体制度.md         ← Tier 0-3 继承模型（1+N 起源）
├── DADS_架构与代码.md           ← 函数级模块展开
├── DADS_宣言.md                 ← 项目声明 + 投入产出统计
├── DADS_已知不足.md             ← 诚实问题清单
├── DADS_BDD方法.md              ← BDD 行为驱动开发方法论
└── DADS_RAG现状.md              ← RAG 检索现状评估

00-AC/DataCenter/truth_datasets/
└── 三明医改真值数据集.md         ← 医学真值数据，可导入 ac_truth
```

---

## 五、关键启示

1. **1+N 不是想出来的，是磨出来的** — DADS 的母体-子体制度在 v19.0-v19.4 九天内迭代成型
2. **治理管道从 7 层减到 4 层** — 说明 AC 做了合理的抽象泛化
3. **从 TF-IDF 到向量检索** — 检索精度提升但依赖从本地文件变为 ChromaDB 服务
4. **DADS 花了 ¥147.41 / 19.8 亿 tokens** — 说明整个体系的实际训练/调试成本
5. **已知不足文档本身就是 AC 的 TODO** — 测试覆盖、边界情况、时效性等问题同样适用于 AC
