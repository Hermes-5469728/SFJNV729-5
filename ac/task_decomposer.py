"""
绝对颗粒度 · 任务原子化拆解器
AC Platform v2.0 · 编排核心组件

原则：
- 一个函数 = 一个不可再分的逻辑原子
- 输入/输出均通过 Pydantic 契约校验
- 零隐藏状态，纯函数式
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum

# ─── 契约定义（每个结构都是一个独立原子）─────────────────────────

class TaskType(str, Enum):
    """任务类型 · 不可再分的最小分类单元"""
    FACT_CHECK = "fact_check"
    DRUG_INTERACTION = "drug_interaction"
    ADVERSE_EVENT = "adverse_event"
    DOSAGE_VERIFY = "dosage_verify"
    LITERATURE_SEARCH = "literature_search"
    GUIDELINE_LOOKUP = "guideline_lookup"

class AtomicTask(BaseModel):
    """原子任务 · 不可再拆的执行单元"""
    type: TaskType
    query: str = Field(..., min_length=1, max_length=500)
    context: dict = Field(default_factory=dict)
    urgency: Literal["routine", "urgent", "emergency"] = "routine"
    idempotency_key: Optional[str] = None  # 幂等保证

class DecomposeResult(BaseModel):
    """拆解结果 · 原子任务集合"""
    atoms: list[AtomicTask]
    original_query: str
    strategy: Literal["sequential", "parallel"] = "parallel"

# ─── 原子化拆解器（每个步骤一个纯函数）─────────────────────────

def extract_drug_entities(query: str) -> list[str]:
    """原子1：抽取药物实体（仅做实体识别，不做任何其他事）"""
    drugs = []
    known = ["阿司匹林", "华法林", "青霉素", "布洛芬", "二甲双胍"]
    for drug in known:
        if drug in query:
            drugs.append(drug)
    return drugs

def detect_intent(query: str, drugs: list[str]) -> list[TaskType]:
    """原子2：意图检测（仅输出任务类型，不产生具体任务）"""
    intents = []
    if drugs:
        intents.append(TaskType.DRUG_INTERACTION)
    if any(word in query for word in ["副作用", "不良反应", "出血"]):
        intents.append(TaskType.ADVERSE_EVENT)
    if any(word in query for word in ["剂量", "用量", "mg"]):
        intents.append(TaskType.DOSAGE_VERIFY)
    if not intents:
        intents.append(TaskType.GUIDELINE_LOOKUP)
    return intents

def build_atomic_tasks(
    query: str,
    drugs: list[str],
    intents: list[TaskType]
) -> list[AtomicTask]:
    """原子3：根据实体和意图，组装不可再分的原子任务"""
    tasks = []
    for intent in intents:
        task = AtomicTask(
            type=intent,
            query=query if not drugs else f"{query} (药物: {', '.join(drugs)})",
            context={"drugs": drugs},
        )
        tasks.append(task)
    return tasks

def optimize_execution_strategy(
    tasks: list[AtomicTask]
) -> Literal["sequential", "parallel"]:
    """原子4：执行策略优化（仅决策串/并行）"""
    if len(tasks) <= 2:
        return "parallel"
    if any(t.type == TaskType.DRUG_INTERACTION for t in tasks):
        return "sequential"
    return "parallel"

# ─── 主编排函数（组合原子，无副作用）─────────────────────────

def decompose(query: str) -> DecomposeResult:
    """
    任务拆解主入口
    组合上述原子函数，严格按顺序执行，绝不跨步骤混合逻辑。
    """
    drugs = extract_drug_entities(query)
    intents = detect_intent(query, drugs)
    atoms = build_atomic_tasks(query, drugs, intents)
    strategy = optimize_execution_strategy(atoms)

    return DecomposeResult(
        atoms=atoms,
        original_query=query,
        strategy=strategy,
    )

# ─── 契约校验式调用示例 ─────────────────────────────────────
if __name__ == "__main__":
    raw = "患者服用阿司匹林和华法林后出现牙龈出血，请问如何处理？"
    result = decompose(raw)
    print(result.model_dump_json(indent=2))
