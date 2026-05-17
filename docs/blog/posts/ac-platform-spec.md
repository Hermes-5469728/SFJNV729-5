---
date: 2026-05-11
title: AC Platform · 架构规格书 — 供 AI 生成代码用
authors:
  - Hermes
categories:
  - 架构
  - 技术
---

# AC Platform · 架构规格书

完整规格书，供 AI 或人类开发者理解 AC Platform 的代码结构。

---

## 一、文件结构

```
ac/
├── cli.py                 ← 入口，命令路由
├── core.py                ← dispatch / annotate / status
├── orchestrator.py        ← 多轮编排，13态状态机
├── governance/            ← 治理管道目录
│   ├── __init__.py
│   ├── encoding.py        ← 编码检查
│   ├── syntax.py          ← 语法检查
│   ├── semantic.py        ← 语义检查
│   └── security.py        ← 安全检查
├── guard.py               ← L0 编码层 + 熔断器 + 真值入库通道
├── db.py                  ← 数据库操作
├── db_migration.py        ← 迁移管理
├── seed.py                ← 24 个专家种子数据
├── anchor_engine.py       ← EAV 事实核验
├── eav_extractor.py       ← EAV 抽取器
├── collaborative_governor.py  ← 协同治理（契约/风险/锁）
├── case_center.py         ← 案例中心（ChromaDB）
├── validator.py           ← 真值三级验证 L0/L2/L5
├── memory_manager.py      ← ChromaDB 管理
├── auto_corrector.py      ← 自动修正器
├── task_decomposer.py     ← 任务拆解
├── schemas/               ← Pydantic 数据模型
│   └── orchestrator_schemas.py
└── qa/                    ← QA 测试
    ├── run_qa.py
    └── tests/
```

---

## 二、核心流程

### 流 A · 单轮调度

```
用户输入
  → guard.sanitize_text()         ← 编码清洗
  → core.dispatch()               ← 24个专家 trigger 匹配
     → 按优先级 P1-P5 排序取 top 2
     → 同时检索 case_center 相似案例
  → governance.pipeline()         ← 四层检查 + corrector×3
  → stdout (L5 标注)
```

### 流 B · 多轮编排

```
用户输入（复杂任务）
  → router.classify()             ← 判断复杂度
  → orchestrator.create_task()    ← 创建任务
  → state_machine: CREATED → QUEUED → DISPATCHED → VERIFIED → COMPLETED
  → 每个阶段都有 ANNOTATE 注入（L5 标注）
  → governance.pipeline() 在 RESOLVE 阶段执行
```

---

## 三、13 态状态机

```
CREATED → QUEUED → DISPATCHED → EXECUTING → VERIFYING → RESOLVING → COMPLETED
                ↘ FAILED_QUEUE         ↘ FAILED_EXEC  ↘ FAILED_VERIFY
                                                              ↘ ROLLBACK
```

| 状态 | 触发 | 动作 |
|------|------|------|
| CREATED | 用户提交复杂任务 | 写入 tasks 表 |
| QUEUED | 资源检查通过 | 按优先级排序 |
| DISPATCHED | 匹配到 expert | 创建 session |
| EXECUTING | expert 确认 | 放行 subprocess |
| VERIFYING | 执行完成 | 调用 validator |
| RESOLVING | 验证通过 | 运行 governance |
| COMPLETED | 全部通过 | 写结果 + L5 标注 |

---

## 四、治理管道（四层）

| 层 | 检查项 | 失败动作 |
|----|--------|---------|
| L0 · encoding | 字符编码、注入模式 | 拒绝，返回错误 |
| L1 · syntax | JSON 结构、字段完整 | corrector ×3 → 拒绝 |
| L2 · semantic | 锚点冲突、事实矛盾 | 标记冲突，需人工裁决 |
| L3 · security | 敏感信息、越权操作 | 拒绝，写审计日志 |

---

## 五、关键不变量（代码层面）

1. 所有 `write` 操作前必须 `guard.validate()`
2. 所有 `store_truth()` 写入不可物理删除，修改走 version+1
3. Schema 版本不匹配时，`db_migration` 强制前置检查
4. `escalate` 字段必须有对应的 listener 消费

---

*来源: AC_SPEC.md*
