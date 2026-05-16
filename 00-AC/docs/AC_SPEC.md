# AC Platform · 架构规格书（供 AI 生成代码用）

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

### 流 A · 单轮调度（core.py dispatch）

```
用户输入
  → guard.sanitize_text()         ← 编码清洗
  → core.dispatch()               ← 24个专家 trigger 匹配
     → 按优先级 P1-P5 排序取 top 2
     → 同时检索 case_center 相似案例
  → governance.pipeline()         ← 四层检查 + corrector×3
  → stdout (L5 标注)
```

### 流 B · 多轮编排（orchestrator.py Orchestrator）

```
用户输入
  → guard.sanitize_text()
  → Orchestrator.orchestrate()
     → PLAN：拆解 PlanStep，分配 Agent
     → EXECUTE：异步并行执行，≤2 workers
     → VERIFY：验证 + 评分，<70 分重试
     → RESOLVE：全部完成或回滚
     → LOG：持久化到 task_graphs
  → governance.pipeline()
  → stdout
```

---

## 三、数据库（ac_platform.db）

### 核心表

| 表名 | 用途 | 关键字段 |
|------|------|---------|
| ac_experts | 24个专家注册 | expert_id, name, category(L/T/M/A), trigger_words, priority(P1-P5), role_definition |
| ac_schedule_log | 调度日志 | log_id, session_id, query_preview, matched_expert, response_mode |
| ac_governance_log | 治理审计 | id, session_id, command, passed, checks_json, corrected, encoding_events |
| ac_truth | 真值知识库 | truth_id, title, category, source, content, verified(0/1), tags |
| task_graphs | 编排任务图 | session_id, status, plan, metrics, shared_context |
| migration_history | 迁移审计 | version, name, applied_at, success |

### 真值入库通道（guard.py store_truth）

```python
def store_truth(title, category, source, content, tags="") -> dict:
    """唯一入库通道。强制 validate_truth，禁止直接 INSERT。"""
    # → validator.validate_truth() 三级验证
    # → 通过且 L5 级 → verified=1
    # → 否则 → verified=0
    # → commit/rollback 保护
```

### validate_truth 三级（validator.py）

```
L0（语法）：检查 unfalsifiable 模式、数据源数量、结构
L2（一致性）：当前是空壳（字符集交集减停用词，不做实质判断）
L5（可溯源）：检查来源 URL 或中文来源标签

评分公式：score = max(0, 1.0 - fail_count*0.4 - warn_count*0.15)
分级：L5≥0.85 | L2≥0.6 | L0<0.6
通过条件：0个 FAIL
```

---

## 四、EAV 事实核验（anchor_engine.py）

```python
class AnchorEngine:
    """EAV 三元组事实核验"""
    def match(self, text: str) -> dict:
        # 极性检测 positive/negative
        # EAV 抽取（R1-R8 正则规则）
        # 锚点库 anchor_db.json 比对
        # 对立词表检测（5 pairs）
        # 冲突 → HARD BLOCK
```

---

## 五、专家系统（seed.py）

24 个专家，4 个分类，5 级优先级：

```
P1（安全）：   危机预案 / 反诈骗 / 安全顾问 / 临床审查 / 幻觉审计
P2（权益）：   个人助手 / 劳动权益 / 法律顾问 / 技术合规
P3（心理）：   心理医生 / 情绪管理 / 人际关系 / 抗压教练
P4（技术）：   决策矩阵 / 偏差检测 / 苏格拉底审计官 / 风险评估
              架构审计 / 合伙挑刺 / 代码审查 / 数据治理 / 生活规划师
P5（通用）：   个人成长教练 / 时间管理
```

trigger 匹配逻辑（core.py dispatch）：
```python
# 对每个专家，遍历 trigger_words（逗号分隔）
# 子串匹配：trigger in query_lower
# 前缀匹配：query_lower.startswith(trigger)
# 后缀匹配：query_lower.endswith(trigger)
# 匹配后按 priority 排序，取前 2 个
```

---

## 六、三个待补模块的接口规格

### 6.1 幻觉审计 · governance/hallucination_auditor.py

```python
"""
位置：在 governance/ 下新建，作为治理管道的可插拔检查器
接口：与 governance/semantic.py 同一级
调用时机：dispatch 输出后、governance pipeline 中

需要实现：
  class HallucinationAuditor:
      def audit(self, text: str, context: dict = None) -> dict:
          \"\"\"逐句审计，返回：
          {
              "audited": True,
              "flagged": [
                  {"sentence": "...", "index": 0, "flag": "LOW_CONFIDENCE|NO_CITATION|CONTRADICTION|HALLUCINATION", "reason": "..."}
              ],
              "total_sentences": N,
              "score": 0.0-1.0,
              "confidence_detail": {...}
          }
          \"\"\"

集成方式：
  governance/pipeline.py 的 run() 函数中，
  在 semantic check 之后、security check 之前，
  调用 auditor.audit(text)，
  将结果合并到 checks 列表中。
  若 audit.score < 阈值（建议 0.5），在输出末尾追加 [幻觉审计] 标记。
"""
```

### 6.2 入库增强 · validator.py 升级 + dedup

```python
"""
L2 一致性检查当前是空壳，需要补：

  1. EAV 冲突检测：
     提取输入文本的 EAV 三元组，
     与 ac_truth 中同 category 的已有记录比对，
     发现矛盾 → FAIL

  2. 去重（deduplication）：
     INSERT 前检查 title/content 相似度，
     与已有记录余弦相似度 > 0.85 → 标记为重复，不插入。

  3. 评分公式可调参：
     当前是硬编码 fail_count*0.4 + warn_count*0.15，
     改为从 config 读取权重。
"""
```

### 6.3 分类兜底 · core.py dispatch 增强

```python
"""
当前 dispatch 在无 trigger 匹配时返回 no_match。
需要兜底分类器：

  1. 关键词兜底（轻量，无外部依赖）：
     按照分类 L/T/M/A 的通用关键词表，
     对无匹配输入做第二轮宽匹配。

  2. 语义兜底（可选，需要 embedding 模型）：
     将输入 embedding 后，
     与 ac_experts 的 trigger_words embedding 做余弦相似度，
     选择最接近的分类。

调用位置：core.py dispatch() 的 no_match 分支之后、返回之前。
"""
```

---

## 七、治理管道接口（governance/）

```python
# governance/pipeline.py 的核心接口

def run(text: str, context: dict = None) -> dict:
    """完整治理管道"""
    checks = []
    checks.append(encoding_check(text))    # governance/encoding.py
    checks.append(syntax_check(text))      # governance/syntax.py
    # ← 这里插入 hallucination_audit
    checks.append(semantic_check(text))    # governance/semantic.py
    checks.append(security_check(text))    # governance/security.py

    # corrector ×3
    for i in range(3):
        failed = [c for c in checks if not c["passed"]]
        if not failed:
            break
        for c in failed:
            corrected = auto_correct(c)
            checks.append(corrected)

    return {"passed": all(c["passed"] for c in checks), "checks": checks}
```

---

## 八、运行方式

```bash
# 调度
python cli.py dispatch "查询文本"

# 标注
python cli.py annotate "AI 输出内容"

# 状态
python cli.py status

# 真值入库
python cli.py case store --title "标题" --content "内容" --category "分类"

# 真值审计
python cli.py case verify
```
