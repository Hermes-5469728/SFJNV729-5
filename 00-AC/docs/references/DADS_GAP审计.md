# Definition-Runtime Gap Audit · 2026-05-06

> Cross-referencing gaia.md (344 lines) vs gaia_defense_pipeline.py (335 lines)

---

## CRITICAL · 运行时缺失

| # | Markdown定义 | Pipeline状态 | 影响 |
|---|------------|------------|------|
| 1 | Intent Routing·高危关键词白名单(46个词) | ❌ 未实现 | 高危输入不经强制审计 |
| 2 | Confidence Protocol·3级置信度(>90%/60-90%/<60%) | ❌ 未实现 | 输出不标置信度 |
| 3 | Recursion Protocol·A/B/C三类自适应截断 | ❌ 未实现 | 悖论输入可能无限递归 |
| 4 | Safety Protocol·局部拒绝机制 | ❌ 未实现 | 指令型攻击无分级拦截 |
| 5 | Efficacy Feedback Loop·7日kill_rate追踪 | ❌ 未实现 | 效能数据不回流 |
| 6 | Corpus Regression Baseline·37题每日抽5 | ❌ 未实现 | 防御质量不监控 |
| 7 | 6-class Jailbreak Matrix | ⚠️ 只实现4类 | DAN/DeveloperMode无检测 |
| 8 | 8 Attack Points | ⚠️ 只实现7个 | 缺少攻击点8(AI污染)运行时代码 |
| 9 | Guideline Recency Window·90天 | ❌ 未实现 | 新指南可能被L6误熔断 |
| 10 | Intranet Data Sync Protocol | ❌ 未实现 | 内网同步无自动化 |
| 11 | Formal Proof Protocol | ❌ 未实现 | Lean/Coq路由未连接 |
| 12 | Code Sandbox·语法→分析→执行 | ❌ 只检测存在性·不运行代码 | 生成代码不经沙箱 |
| 13 | Dormant Protocols·5项自动激活 | ❌ 未实现 | 条件满足不会自动激活 |
| 14 | FHIR Trace·MedicationStatement映射 | ❌ 未连接 | 100份合成病历·管道不使用 |

## WARNING · 部分实现

| # | Markdown定义 | Pipeline状态 | 差距 |
|---|------------|------------|------|
| 15 | L3八维幻觉检测 | ✅ 7维+遗漏(正则限制) | 类型3(语境幻觉)正则无法有效检测 |
| 16 | Personal Assistant·6领域+4元 | ❌ 定义在Markdown·管道不调用 | 子体全为文档·无运行入口 |
| 17 | AHDS·4子体(de/ve/tr/au) | ❌ 定义在Markdown·管道不实例化 | 审计报告不会自动生成 |
| 18 | DADS·3医疗子体 | ❌ 定义在Markdown·管道不调用 | 药物核查走前端·不进管道 |

## OK · 已实现

| # | Markdown定义 | Pipeline状态 |
|---|------------|------------|
| ✅ | L1 Input Detection·8攻击点 | 7/8 正则+风险评分 |
| ✅ | L2 NLI Debate | 多裁判辩论+聚合判定 |
| ✅ | L3 Intra-Op Review | 8维检测(7维正则+1上下文) |
| ✅ | L4 TRACE | 5标签+防火墙(LLM阻断) |
| ✅ | L5 Mandatory Label | 中英双语固定标签 |
| ✅ | L6 Physical Reality | drug_extract检测+药物关键词 |
| ✅ | AI Contamination Isolation | 外部AI标记+不入迭代 |
| ✅ | Time Rule | 禁止声称未经证实的时间 |

---

## 统计

总检查项: 26
完全实现: 8 (31%)
部分实现: 4 (15%)
缺失: 14 (54%)

**最严重**: Intent Routing未实现——46个高危关键词不走强制审计。医疗诊断/法律/金融直接绕过。

## RESOLVED

| 日期 | 问题 | 修复 |
|------|------|------|
| 2026-05-06 | Sync Schism·管道副本 | CoPilot副本删除·所有导入指向AgentHub单一源 |
| 2026-05-06 | Intent Routing缺失 | 46关键词+is_high_risk()已实装 |
| 2026-05-06 | Confidence Protocol | 3级追加已实装 |
| 2026-05-06 | Recursion Protocol | A/B/C自适应截断已实装 |
| 2026-05-06 | Safety Protocol | 局部拒绝指令已实装 |
| 2026-05-06 | Efficacy Feedback | kill_rate追踪已实装 |
| 2026-05-06 | Code Sandbox | subprocess沙箱执行已实装 |
