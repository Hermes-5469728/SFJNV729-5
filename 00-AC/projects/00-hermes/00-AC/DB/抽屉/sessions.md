# sessions · 调用记录表

> 每次专家被触发, 记一行
> 数据文件: DB/data/sessions/ (按 YYYY-MM 分文件)

| session_id | timestamp | expert_id | trigger_text | hit_correct | rating | upgraded_to | notes |
|-----------|-----------|-----------|-------------|-------------|--------|-------------|-------|
| | | | | | | | |

---

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | VARCHAR | ✓ | SES-{YYYYMMDD}-{序号} |
| timestamp | DATETIME | ✓ | 触发时间 |
| expert_id | VARCHAR | ✓ | 专家 ID, 关联 experts 表 |
| trigger_text | TEXT | ✓ | 用户触发时说的话 |
| hit_correct | BOOLEAN | ✓ | 是否命中了正确的专家 |
| rating | INT | | 1-5, 用完后的评分 |
| upgraded_to | VARCHAR | | 升级通道触发了谁 |
| notes | TEXT | | 备注 |

---

## 查询示例

```sql
-- 上周心理医生被唤醒几次
SELECT COUNT(*) FROM sessions
WHERE expert_id = 'EX002'
  AND timestamp >= date('now', '-7 days');

-- 评分最低的 3 个专家
SELECT expert_id, AVG(rating) FROM sessions
GROUP BY expert_id
ORDER BY AVG(rating) ASC LIMIT 3;
```
