# energy_log · 能量账本

> 每天睡前记一笔
> 数据文件: DB/data/energy_log.md

| log_id | date | energy_level | charge_event | drain_event | notes |
|--------|------|-------------|-------------|-------------|-------|
| | | | | | |

---

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| log_id | VARCHAR | ✓ | EN-{YYYYMMDD} |
| date | DATE | ✓ | 日期 |
| energy_level | INT | ✓ | 1-10, 当天能量水平 |
| charge_event | TEXT | ✓ | 充电事件 (让能量升高的活动) |
| drain_event | TEXT | ✓ | 耗电事件 (让能量降低的活动) |
| notes | TEXT | | 备注 |

---

## 能量规则

```
每次专家激活:   -5 (调用 AI 需要心力)
自然恢复:       每小时 +2 (睡觉时 +5)
上限:           100
下限:           0 (0 时自动触发危机预案)

能量 < 20:      Manager 非侵入提示 "能量偏低, 建议休息"
能量 < 10:      Manager 不推新任务, 只回答被动查询
```

---

## 已有数据

(空 — 等 Hermes 填第一行)
