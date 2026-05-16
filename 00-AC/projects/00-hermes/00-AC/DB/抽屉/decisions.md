# decisions · 决策日志表

> 每次做重大选择, 记一行
> 数据文件: DB/data/decisions.md

| decision_id | timestamp | option_a | option_b | choice | reason | emotion | outcome_30d | outcome_90d | lesson |
|------------|-----------|----------|----------|--------|--------|---------|-------------|-------------|--------|
| | | | | | | | | | |

---

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| decision_id | VARCHAR | ✓ | DEC-{YYYYMMDD}-{序号} |
| timestamp | DATETIME | ✓ | 决策时间 |
| option_a | TEXT | ✓ | 选项 A |
| option_b | TEXT | ✓ | 选项 B |
| choice | VARCHAR | ✓ | 选择了 A 还是 B |
| reason | TEXT | ✓ | 当时为什么这么选 |
| emotion | TEXT | ✓ | 当时的情绪状态 |
| outcome_30d | TEXT | | 30 天后的实际结果 |
| outcome_90d | TEXT | | 90 天后的实际结果 |
| lesson | TEXT | | 从中学会了什么 |

---

## 已有决策

| DEC-001 | 2026-05-01 | 先学架构 | 先学代码 | 架构 | 非科班, 自顶向下更适合 | 兴奋但不自信 | 15 定义 + 全仓代码完成 | — | 架构驱动 > 代码驱动 |
