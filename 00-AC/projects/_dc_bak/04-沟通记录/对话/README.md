# 对话真值提取系统 · Truth Extraction

## 规则

1. 每日输入数据存入 `YYYY-MM-DD/raw.md`
2. 从 raw 中提取真值 (关键事实/决策/洞察/纠正) → `YYYY-MM-DD/truth.md`
3. 只保留最近 **7 天**，超期自动清除
4. 真值格式：一句话一条，来源标注，不可含幻觉推测

---

## 真值提取标准

### 包含
- 明确事实陈述（带出处）
- 已确认的决策/结论
- 纠错记录（错误→正确）
- 可验证的技术数据

### 排除
- 推测/猜测
- 未经验证的 LLM 输出
- 主观感受
- 待确认事项

---

## 真值模板

```
# 真值记录 · YYYY-MM-DD

## 事实
- [ ] 事实描述 | 来源: xxx

## 决策
- [ ] 决策内容 | 原因: xxx

## 纠正
- [ ] 错误: xxx → 正确: xxx | 来源: xxx

## 数据
- [ ] 数值/参数 | 上下文: xxx
```

---

## 7 天清理

```powershell
$limit = (Get-Date).AddDays(-7)
Get-ChildItem "对话" -Directory |
    Where-Object { $_.Name -match '\d{4}-\d{2}-\d{2}' -and [datetime]$_.Name -lt $limit } |
    Remove-Item -Recurse -Force
```
