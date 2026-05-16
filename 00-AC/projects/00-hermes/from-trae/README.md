# from-trae 使用规范

> 2026-05-12

## 工作流

```
Trae 对话结束 → 有价值输出
    │
    ├── 复制 Trae 回复全文
    ├── 保存为 from-trae/YYYY-MM-DD-简短描述.md
    │
    └── OpenCode 自动读取 → [SOURCE:TRAE] 标注 → 按原则决定是否入库
```

## 文件命名规范

`YYYY-MM-DD-关键词.md`

示例:
- `2026-05-12-langgraph-eval.md` — LangGraph 架构评估回复
- `2026-05-13-medical-crud-review.md` — 医疗模块 CRUD 代码审查

## 自动处理规则

当 OpenCode 检测到 from-trae/ 目录有新文件:
1. 读取全文
2. 标注 [SOURCE:TRAE]
3. 按原则判断: 我能否生成类似内容?
   - 能 → 仅参考
   - 不能 → 入库 cnt_references, ref_type="Trae对话"
