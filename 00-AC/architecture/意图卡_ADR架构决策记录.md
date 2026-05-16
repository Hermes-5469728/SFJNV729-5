# 意图卡 · ADR 架构决策记录

## 模块名
`adr` — Architecture Decision Record · 结构化架构决策存储与回溯

## 目标
将每一次架构决策（为什么选 A 不选 B、当时已知什么、放弃了什么）从对话记忆中抽取出来，写为不可销毁的 ADR 文档，建立完整的决策追溯链。

## 背景
- **宪法规则**: 宪法铁律第 7 条 — L5 强制标注。所有 AI 输出必须标注来源链和时间戳。但架构决策本身（为什么用 SQLite 而非 PostgreSQL、为什么选 Pydantic 而非 dataclass）当前只存在于对话历史中，不可检索、不防篡改、不防丢失
- **猎鬼发现**: 架构审计 (2026-05-13) 第 12 项 — 模块间无协议。更深层的问题是：连协议为什么不存在都没有记录。如果 3 个月后有人问"为什么要用 DeepSeek 免费层而不是本地 Ollama"，当前系统无法给出带追溯链的回答
- **为什么需要**: AC 系统的宪法已有 10+2 条修正案，但修宪程序、规则优先级、冲突裁决全在对话记忆中。R10（云服务中立性）是怎么加进宪法的？当时的 trade-off 是什么？没有 ADR，3 天后就忘了

## 输入
| 参数 | 类型 | 说明 |
|------|------|------|
| `title` | `str` | 决策标题（如 "ADR-003: 选择 SQLite 作为唯一数据库"） |
| `status` | `str` | proposed / accepted / deprecated / superseded |
| `context` | `str` | 决策背景：当时面临什么问题 |
| `decision` | `str` | 最终决定：选了哪个方案 |
| `alternatives` | `list[str]` | 被放弃的方案及其放弃原因 |
| `consequences` | `str` | 决策后果：得到了什么、牺牲了什么 |

## 输出
```python
{
    "adr_id": str,               # ADR-{序号} 如 ADR-001
    "title": str,
    "status": str,
    "context": str,
    "decision": str,
    "alternatives": list[str],
    "consequences": str,
    "created_at": str,           # ISO 时间戳
    "superseded_by": str | None, # 被哪个 ADR 取代
    "related_adrs": list[str],   # 关联的 ADR 编号
}
```

## 关键约束
1. **不可物理删除** — ADR 一旦写入，不可删除。状态改为 `deprecated` 或 `superseded` 但保留原文
2. **必须关联宪法规则** — 每个 ADR 标注关联的宪法条款（如 "关联: R10, R12"）
3. **必须写入 `ac_truth`** — ADR 是架构级真值，走 `guard.store_truth()` 入库
4. **存储双介质** — 同时写入 SQLite `ac_truth` 和 Markdown 文件 `00-AC/adr/ADR-{序号}.md`
5. **变更必须追溯** — ADR 被取代时，新 ADR 必须引用旧 ADR 编号，形成决策链
6. **与意图卡的关系** — 意图卡（Intent）是"我们要做什么"，ADR 是"为什么这样做"。一张意图卡可能对应多张 ADR

## 已知难点
1. **从对话中抽取 ADR** — 架构决策散落在多轮对话中，AI 需要能识别"这是一次架构决策"并自动提议 ADR 草稿。当前无自动化抽取机制
2. **ADR 冲突检测** — 如果 ADR-005 说"所有模块用 SQLite"，ADR-011 说"日志模块用文件存储"——这两者是否冲突？需要语义比较
3. **历史决策逆向补录** — 已有 15+ 个架构决策（为什么用 Pydantic、为什么用 ChromaDB、为什么要双实例推理），但都没有 ADR。需要人工补录或从 AGENTS.md + handoffs/ 中半自动提取
4. **与现有 ac_truth 的关系** — ac_truth 已有 105 条真值记录。ADR 是 `category="architecture_decision"` 的真值子集还是独立存储？需厘清

## 参考文件
- `guard.py:store_truth()` — 真值入库入口
- `ac_truth` 表 — 现有真值库
- `00-AC/handoffs/` — 每日交接（蕴含未记录的架构决策）
- `CORE_PHILOSOPHY.md` — 最近的决策（AI 协作协议 R12）
- `00-AC/architecture/` — 意图卡存放位置
