# 意图卡 · SQL 语义守卫

## 模块名
`KnowledgeService._verify_sql_plan()` + `_fallback_scan()` + `_log_hijack_attempt()`

## 目标
在执行层拦截云服务商对本地 SQL 查询的隐式改写（LIKE → 向量搜索 / ANN / embedding），确保声称"纯本地"的操作确实零远程调用。

## 背景
- **宪法规则**: R10 · 云服务中立性验证 — 任何隐式增强视为架构欺诈
- **猎鬼发现**: 某云 SQLite 驱动在 `EXPLAIN QUERY PLAN` 中注入 `USING VECTOR INDEX`，将普通 LIKE 搜索改写为向量检索，数据在用户不知情的情况下被送往云端节点
- **为什么需要**: 本地 SQLite 的 `ac_truth` 是 AC 唯一知识真值源。如果查询被静默代理到云端，R10 第 2 条直接触发猎鬼

## 输入
| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | `str` | 用户搜索文本（如 "布洛芬"） |
| `sql` | `str` | 即将执行的 SQL 语句（供 EXPLAIN QUERY PLAN 分析） |

## 输出
```python
{
    "clean": bool,           # True = 执行计划不含劫持关键词
    "plan": str,             # EXPLAIN QUERY PLAN 输出 (截断至 500 字符)
    "hijacked_keywords": list[str],  # 检测到的劫持关键词
}
```
检测到劫持时：
1. `_log_hijack_attempt()` 写入 `ac_guard_log` (guard=`sql_plan_guard`)
2. 自动降级为 `_fallback_scan()` — 纯 SQLite 参数化查询，无任何优化路径
3. 触发 ArchGuard `sql_integrity` FAIL

## 关键约束
1. **禁止调用外部 API** — 守卫本身不能产生网络请求，否则自指悖论
2. **必须对接 `ac_guard_log`** — 每次劫持检测写入不可销毁审计日志
3. **必须对接 ArchGuard 第 7 项** — `_check_sql_integrity()` 在每次全量扫描中重验
4. **`PRAGMA query_only = ON`** — 所有守卫连接强制只读
5. **降级路径不可绕过** — `_fallback_scan()` 用纯 SQLite `?` 参数化查询，不走任何 ORM/驱动优化层

## 已知难点
1. **假阳性风险** — 如果未来 ChromaDB 本地 embedding 的 EXPLAIN 输出中包含相似关键词，守卫可能误判。需要持续更新 `HIJACK_KEYWORDS` 白名单
2. **逃逸检测** — 云服务商可能使用不在关键词库中的改写手段（如 `FTS5` 全文索引、`R*Tree` 空间索引）。当前依赖关键词匹配，非行为沙箱
3. **ChromaDB 调用本身不受控** — `_search_chroma()` 仍走 `chromadb` 库，如果 chromadb 的 PersistentClient 在某版本静默切换为云端模式，守卫无法检测

## 参考文件
- `knowledge_service.py:57-95` — 守卫实现
- `tests/test_sql_hijack.py` — 15 项 CI/CD 熔断断言
- `archguard.py:_check_sql_integrity()` — ArchGuard 第 7 项
- `00-AC/evidence/constitution_R10_cloud_neutrality.md` — R10 宪法原文
