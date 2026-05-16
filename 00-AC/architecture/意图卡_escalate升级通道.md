# 意图卡 · escalate 升级通道

## 模块名
`escalate` — dispatch unclassified → orchestrator → 人工审核三级升级链

## 目标
将 dispatch 无法匹配的 `unclassified` 查询从"静默丢弃"升级为"逐级上报"，确保没有用户输入掉入真空。

## 背景
- **宪法规则**: AC 不决策，选择权在用户 — unclassified 时不能替用户决定"不重要"
- **猎鬼发现**: 架构审计 (2026-05-13) 第 3 项 — `escalate` 通道在架构文档中标注"已实现"但实际是空函数，`unclassified` 结果被静默丢弃，无日志、无上报、无兜底
- **为什么需要**: dispatch 的语义兜底 + 分类兜底已经覆盖大部分输入，但仍存在不可分类的查询（如歧义短词、非中文输入、纯符号）。当前 `jarvis_core.py` 的 `unclassified` 硬兜底是临时方案（直接返回人工审核提示），缺少持久化和追踪

## 输入
| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | `str` | 原始用户输入 |
| `dispatch_result` | `dict` | dispatch 返回的完整结果（含 status=unclassified） |
| `session_id` | `str` | 会话标识（用于关联上下文） |
| `retry_count` | `int` | 当前已重试次数（默认 0） |

## 输出
```python
{
    "escalation_id": str,        # 升级事件唯一 ID
    "level": int,                # 当前升级层级 (1=语义重试, 2=orchestrator, 3=人工)
    "status": str,               # pending / retrying / escalated / resolved / timeout
    "next_action": str,          # 建议的下一步操作
    "human_queue_position": int | None,  # 人工队列位置 (仅 L3)
    "created_at": str,           # ISO 时间戳
}
```

## 关键约束
1. **三级不跳级** — 必须按 L1→L2→L3 顺序，不可直接从 L1 跳到 L3
2. **L1 语义重试** — 用 dual_inference (t=0.7 发散模式) 重新解析 query，尝试提取隐含意图
3. **L2 orchestrator 接管** — 将 query 提交给 `orchestrator.plan()`，分解为子任务后再尝试匹配
4. **L3 人工审核** — 生成审核卡片写入手递文件 (`00-AC/handoffs/`)，附带上下文摘要和建议分类
5. **必须写入 `governance_events`** — 每级升级事件写入 `governance_events` 表 (event_type=`escalate_L1/L2/L3`)
6. **超时熔断** — L3 等待超过 24h 无人工响应，标记为 `timeout` 并关闭
7. **不自动决策** — escalate 通道只上报和建议，不替用户做最终分类

## 已知难点
1. **L2 orchestrator 的 PlanSteps 生成依赖 LLM** — 如果 orchestrator 本身也 unclassified，会形成死循环。需要 `max_escalation_depth=2`
2. **人工审核队列持久化** — 当前无消息队列，进程重启后队列丢失。需要写入 SQLite `escalation_queue` 表
3. **上下文丢失** — L2→L3 时，原始对话上下文可能已滚出。需要在升级时快照上下文摘要
4. **与 jarvis_core 的冲突** — `jarvis_core.py:chat()` 已有 unclassified 硬兜底。escalate 通道必须替换它，而非叠加

## 参考文件
- `core.py:dispatch()` — 当前 dispatch 入口，unclassified 返回路径
- `jarvis_core.py:chat()` — 步骤 4 的 unclassified 硬兜底 (待替换)
- `orchestrator.py:plan()` — L2 接管接口
- `dual_inference.py` — L1 语义重试的温差推理引擎
- `db_migration.py` — 需新增 `escalation_queue` 表迁移
