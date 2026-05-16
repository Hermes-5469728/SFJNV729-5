# Atelier 状态机升级 · 发给 Trae 的任务说明

---

## 背景

Atelier 是一个个人 AI 调度系统，当前架构是一个线性管道：

```
user_input → IntentRouter → Gaia L1-L7防御 → RuleEngine/LLM → 返回
```

现在需要升级为状态机架构，支持复杂任务的节点编排（PPT生成、代码生成、小说创作等），但**不引入 LangGraph、不破坏现有的 Gaia 防御体系、不引入新依赖**。

---

## 核心约束（不可违反）

1. **不引入新依赖** — 零 pip install，只用 Python 标准库 + 已有依赖
2. **不破坏 Gaia L1-L7** — defense/pipeline.py 的主体逻辑不许改，只允许拆出一个可复用的 GaiaNode 类
3. **不碰宪法** — constitution/governance.py 的 10 条宪法逻辑只许追加 NodeGovernance，不许删减
4. **不碰个人数据模块** — personal/ 目录下的所有文件不动
5. **L5 强制标签必须保留** — 所有 LLM 输出都要标注 [本回答绝对含有幻觉成分]
6. **现有功能零降级** — 华法林+阿司匹林的药物查询必须在 10ms 内返回

---

## 需要的 5 个文件

### 文件 1: engine/state_machine.py (~80行)

**定位：** 状态图编排引擎，包装在 AtlasCore.process() 外面

**功能：**
- 定义 Node（执行函数 + 校验函数 + 失败时回退的节点名）
- 支持普通边（顺序执行）和条件边（PASS → next, FAIL → rollback）
- Checkpoint 持久化：每个节点执行完保存状态到磁盘，崩溃后可从断点恢复
- 初始化时从 Checkpoint 恢复，不存在则从 start_node 开始

**关键：** 不是替代 process()，是包装它。process() 本身不改。

```
class StateMachine:
    nodes: Dict[str, Node]
    run(start_node, context) → State
    transition(state, result) → State
    checkpoint: save/load
```

---

### 文件 2: engine/gaia_node.py (~60行)

**定位：** 把 Gaia L1-L7 拆出一个可配置的校验节点类

**功能：**
- 接受一个规则集 (List[Rule]) 和输出内容，返回 PASS/FAIL(retry_hint)
- 不同场景挂不同规则集：
  - 代码生成节点：SecurityRule + ArchitectureRule + StyleRule
  - 小说创作节点：WorldConsistencyRule + PlotLogicRule + ToneRule
  - PPT 生成节点：LogicFlowRule + FormatRule + ContentConsistencyRule
- 调用现有 defense/ 模块的检查函数，不重写

**规则集示例：**
- ContentConsistencyRule：复用 L7 结构对齐逻辑
- WorldConsistencyRule：复用 L2 NLI 辩论的矛盾检测
- KnowledgeHallucinationRule：复用 L3 8 维幻觉扫描
- SourceProvenanceRule：复用 L4 溯源标注

---

### 文件 3: engine/brain_pool.py (~50行)

**定位：** 多 AI 模型注册表 + 按意图路由

**功能：**
- 注册多个 LLM 客户端（DeepSeek / Claude / Qwen / Kimi / Ollama）
- 每个客户端打上能力标签（deep_logic / long_review / cn_creative / video_gen / fast_cheap）
- 路由表：意图标签 → 模型选择
  - INTENT_ARCH_DESIGN → deep_logic
  - INTENT_CODE_REVIEW → long_review + deep_logic（双审取共识）
  - INTENT_CREATIVE → cn_creative
  - INTENT_VIDEO → video_gen
  - INTENT_FORMAT → fast_cheap
- 支持并行调用多个模型，取共识输出

**关键：** 路由键直接从现有的 IntentRouter 输出获取，不需要新概念。

---

### 文件 4: infra/pipeline_trace.py (~40行)

**定位：** 结构化链路日志

**功能：**
- 每个节点执行后记录：trace_id, node_id, model_name, input_hash, output_hash, latency_ms, tokens_used, gaia_verdict, retry_count
- 输出 JSONB 格式，可写到 PostgreSQL 的 pipeline_traces 表，也可写本地 JSON 文件
- 最终返回完整的 trace 摘要

**单条 trace 记录格式：**
```json
{
  "trace_id": "tr-20260512-001",
  "pipeline": "ppt_generation",
  "nodes": [
    {
      "node_id": "outline_design",
      "model": "deepseek-chat",
      "input_hash": "sha256:abc123",
      "output_hash": "sha256:def456",
      "latency_ms": 2340,
      "gaia_verdict": "PASS"
    }
  ],
  "total_retries": 2,
  "final_verdict": "PASS"
}
```

---

### 文件 5: infra/iteration_loop.py (~30行)

**定位：** 在现有 RecursionGuard 基础上改，从"防死循环"升级为"利用循环优化"

**功能：**
- 执行 node → 检验 → FAIL? → 注入修正提示 → 重新执行（最多 3 次）
- 3 次后仍失败 → 抛出 MaxRetriesExceeded，触发熔断
- 每次重试记录输出版本号，供 trace 回溯

**伪代码：**
```
def run(node, validator, context, max_retries=3):
    for attempt in range(max_retries):
        output = node.execute(context)
        verdict = validator.check(output)
        if verdict == PASS:
            return output
        context.add_feedback(verdict.fail_reason)  # 注入修正提示
    raise MaxRetriesExceeded
```

---

## 不该做的事

- ❌ 不要重写 defense/pipeline.py — 只拆出一个 GaiaNode 包装类
- ❌ 不要改 personal/ 目录 — 个人数据不进状态机
- ❌ 不要改 dads_db/ 目录 — 药物数据库不变
- ❌ 不要引入 langgraph / langchain / 任何新 PyPI 包
- ❌ 不要把简单查询塞进状态机 — 用双路径

---

## 双路径架构（关键）

```
user_input → IntentRouter
  ├── 意图 = 简单查询 (药物/指南/评分)?
  │     → FastPath: 现有线性管道 (不动, <10ms)
  │
  └── 意图 = 复杂任务 (PPT/代码/小说/视频)?
        → StateMachine: 5层升级 (新增)
```

**FastPath 白名单：**
- medical_drug_check / medical_interaction / medical_guideline / medical_score
- simple_rag_query / knowledge_lookup
- personal_profile / personal_tracker

**其他意图全部走 StateMachine。**

---

## 受影响需小改的文件

| 文件 | 改动 | 行数 |
|------|------|:--:|
| defense/pipeline.py | 拆出 GaiaNode 可复用包装类 | ~40 |
| constitution/governance.py | 增加 NodeGovernance 节点级约束 | ~40 |
| infra/recursion_guard.py | 升级为 IterationLoop | ~30 |
| infra/circuit_breaker.py | 支持 node_id 粒度熔断 | ~10 |
| engine/hlink.py (HLinkRouter) | 增加双路径路由：FastPath vs StateMachine | ~20 |

---

## 期望的交付物

1. 5 个新文件（代码完整、可直接运行）
2. 对现有文件的改动（用 diff 或精确行号标注）
3. 不改动的文件清单（明确不碰的范围）
4. 简单测试：用一个药物查询验证 FastPath 未受影响
