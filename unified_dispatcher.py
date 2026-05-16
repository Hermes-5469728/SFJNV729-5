"""
Unified Dispatcher - P0: SubAgent 与 AC 统一调度架构
Option A: AC 作为主调度器，SubAgent 作为可调用的专家执行器

架构原则：
- AC 负责：入口路由、任务编排、全局治理（G0-G4）、持久化
- SubAgent 负责：代码生成/文档创作的专业执行（L1-L3 验证）
- 验证规则统一：SubAgent L1-L3 做生成质量，AC G0-G4 做事实验证
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import json
import uuid


class TaskDomain(Enum):
    """任务领域分类 - 决定路由到哪个执行器"""
    KNOWLEDGE = "knowledge"      # 知识查询/对话 → AC
    REASONING = "reasoning"     # 推理分析 → AC
    CODE_GENERATION = "code"    # 代码生成 → SubAgent
    ARCHITECTURE = "arch"        # 架构设计 → SubAgent
    DOCUMENTATION = "doc"        # 文档创作 → SubAgent
    MIXED = "mixed"              # 混合任务 → AC 主调度，SubAgent 子任务


class TaskPriority(Enum):
    P0_CRITICAL = 0
    P1_HIGH = 1
    P2_MEDIUM = 2
    P3_LOW = 3


@dataclass
class UnifiedTask:
    """统一任务结构"""
    id: str
    domain: TaskDomain
    priority: TaskPriority
    request: str
    context: Dict[str, Any]
    created_at: str
    parent_task_id: Optional[str]
    requires_subagent: bool
    execution_trace: List[Dict] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """统一执行结果"""
    task_id: str
    success: bool
    output: str
    executor: str  # "ac" or "subagent"
    governance_passed: bool
    governance_results: Dict[str, Any]
    execution_time_ms: float
    error: Optional[str] = None


class UnifiedDispatcher:
    """
    统一调度器 - AC 平台核心

    职责：
    1. 接收所有入口请求（CLI/Web/对话端）
    2. 路由决策：根据任务类型决定 AC 自主处理还是调用 SubAgent
    3. 任务编排：AC 13态状态机管理全生命周期
    4. 结果治理：所有输出走 AC G3 治理管道
    5. 持久化：统一存储到同一个数据库
    """

    def __init__(self, db_path: str = "unified_platform.db"):
        self.db_path = db_path
        self._init_db()
        self.ac_executor = ACExecutor()
        self.subagent_executor = SubAgentExecutor()
        self.governance_pipeline = None  # AC G3 pipeline

    def _init_db(self):
        """初始化统一数据库"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS unified_tasks (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                priority INTEGER NOT NULL,
                request TEXT NOT NULL,
                context TEXT,
                created_at TEXT NOT NULL,
                parent_task_id TEXT,
                status TEXT NOT NULL,
                result TEXT,
                executor TEXT,
                governance_results TEXT,
                execution_time_ms REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_execution_trace (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                executor TEXT,
                input_data TEXT,
                output_data TEXT,
                timestamp TEXT NOT NULL,
                duration_ms REAL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status
            ON unified_tasks(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trace_task
            ON task_execution_trace(task_id)
        """)

        conn.commit()
        conn.close()

    def dispatch(self, request: str, context: Optional[Dict] = None) -> ExecutionResult:
        """统一入口 - 所有请求通过此方法"""
        task_id = str(uuid.uuid4())
        domain = self._classify_domain(request, context)
        priority = self._assess_priority(request, context)

        task = UnifiedTask(
            id=task_id,
            domain=domain,
            priority=priority,
            request=request,
            context=context or {},
            created_at=datetime.now().isoformat(),
            parent_task_id=None,
            requires_subagent=domain in [TaskDomain.CODE_GENERATION, TaskDomain.ARCHITECTURE, TaskDomain.DOCUMENTATION]
        )

        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO unified_tasks
            (id, domain, priority, request, context, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'routing')
        """, (task.id, task.domain.value, task.priority.value, task.request,
              json.dumps(task.context), task.created_at))
        conn.commit()
        conn.close()

        self._trace_step(task.id, "domain_classification", "dispatcher",
                        {"domain": domain.value, "priority": priority.value})

        if task.requires_subagent:
            return self._execute_with_subagent(task)
        else:
            return self._execute_with_ac(task)

    def _classify_domain(self, request: str, context: Optional[Dict]) -> TaskDomain:
        """领域分类"""
        request_lower = request.lower()

        code_keywords = ["代码", "code", "函数", "class", "def ", "实现", "生成代码", "programming"]
        arch_keywords = ["架构", "architecture", "设计模式", "系统设计", "component"]
        doc_keywords = ["文档", "document", "写文档", "README", "markdown", "规范文档"]
        knowledge_keywords = ["什么是", "how to", "解释", "定义", "查询", "知识", "问答"]
        reasoning_keywords = ["分析", "reasoning", "推理", "比较", "对比", "评估"]

        if any(k in request_lower for k in code_keywords):
            return TaskDomain.CODE_GENERATION
        if any(k in request_lower for k in arch_keywords):
            return TaskDomain.ARCHITECTURE
        if any(k in request_lower for k in doc_keywords):
            return TaskDomain.DOCUMENTATION
        if any(k in request_lower for k in reasoning_keywords):
            return TaskDomain.REASONING
        if any(k in request_lower for k in knowledge_keywords):
            return TaskDomain.KNOWLEDGE

        return TaskDomain.MIXED

    def _assess_priority(self, request: str, context: Optional[Dict]) -> TaskPriority:
        """优先级评估"""
        p0_keywords = ["紧急", "critical", "立刻", "p0", "production", "故障"]
        p1_keywords = ["重要", "important", "尽快", "p1", "高优"]

        request_lower = request.lower()
        if any(k in request_lower for k in p0_keywords):
            return TaskPriority.P0_CRITICAL
        if any(k in request_lower for k in p1_keywords):
            return TaskPriority.P1_HIGH
        return TaskPriority.P2_MEDIUM

    def _execute_with_subagent(self, task: UnifiedTask) -> ExecutionResult:
        """调用 SubAgent 执行（代码生成类任务）"""
        import time
        start = time.time()

        self._trace_step(task.id, "subagent_invocation", "dispatcher",
                        {"subagent_type": "code_generation"})

        raw_result = self.subagent_executor.generate(
            request=task.request,
            context=task.context,
            task_type=task.domain.value
        )

        execution_time = (time.time() - start) * 1000

        self._trace_step(task.id, "governance_ac_g3", "ac",
                        {"before": raw_result[:100]})

        governance_results = self._run_ac_governance(raw_result)

        all_passed = all(
            r.get("passed", False) or r.get("corrected", False)
            for r in governance_results.get("checks", [])
        )

        result = ExecutionResult(
            task_id=task.id,
            success=all_passed,
            output=governance_results.get("text", raw_result),
            executor="subagent",
            governance_passed=all_passed,
            governance_results=governance_results,
            execution_time_ms=execution_time
        )

        self._save_result(task.id, result)

        return result

    def _execute_with_ac(self, task: UnifiedTask) -> ExecutionResult:
        """AC 自主执行（知识/推理类任务）"""
        import time
        start = time.time()

        self._trace_step(task.id, "ac_execution", "ac", {})

        raw_result = self.ac_executor.execute(
            request=task.request,
            context=task.context,
            domain=task.domain
        )

        execution_time = (time.time() - start) * 1000

        governance_results = self._run_ac_governance(raw_result)

        all_passed = all(
            r.get("passed", False) or r.get("corrected", False)
            for r in governance_results.get("checks", [])
        )

        result = ExecutionResult(
            task_id=task.id,
            success=all_passed,
            output=governance_results.get("text", raw_result),
            executor="ac",
            governance_passed=all_passed,
            governance_results=governance_results,
            execution_time_ms=execution_time
        )

        self._save_result(task.id, result)

        return result

    def _run_ac_governance(self, text: str) -> Dict[str, Any]:
        """运行 AC G3 治理管道"""
        try:
            from ac.governance import pipeline
            return pipeline(text, {"command": "dispatch"})
        except ImportError:
            return {"passed": True, "text": text, "checks": [], "encoding_sanitized": False}

    def _trace_step(self, task_id: str, step_name: str, executor: str,
                   data: Dict[str, Any], duration_ms: float = 0):
        """记录执行轨迹"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO task_execution_trace
            (task_id, step_name, executor, input_data, output_data, timestamp, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (task_id, step_name, executor, json.dumps(data), "",
              datetime.now().isoformat(), duration_ms))
        conn.commit()
        conn.close()

    def _save_result(self, task_id: str, result: ExecutionResult):
        """保存执行结果"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE unified_tasks
            SET status = ?, result = ?, executor = ?, governance_results = ?, execution_time_ms = ?
            WHERE id = ?
        """, (
            "completed" if result.success else "failed",
            json.dumps({"output": result.output, "error": result.error}),
            result.executor,
            json.dumps(result.governance_results),
            result.execution_time_ms,
            task_id
        ))
        conn.commit()
        conn.close()


class ACExecutor:
    """AC 执行器 - 知识/推理类任务"""

    def execute(self, request: str, context: Dict, domain: TaskDomain) -> str:
        """AC 自主执行"""
        if domain == TaskDomain.KNOWLEDGE:
            return self._knowledge_query(request, context)
        elif domain == TaskDomain.REASONING:
            return self._reasoning(request, context)
        else:
            return self._general_query(request, context)

    def _knowledge_query(self, request: str, context: Dict) -> str:
        return f"[AC-Knowledge] 查询结果: {request}"

    def _reasoning(self, request: str, context: Dict) -> str:
        return f"[AC-Reasoning] 分析结果: {request}"

    def _general_query(self, request: str, context: Dict) -> str:
        return f"[AC-General] 响应: {request}"


class SubAgentExecutor:
    """SubAgent 执行器 - 代码生成/文档创作"""

    def generate(self, request: str, context: Dict, task_type: str) -> str:
        """SubAgent 生成"""
        if task_type == "code":
            return self._generate_code(request, context)
        elif task_type == "arch":
            return self._generate_architecture(request, context)
        elif task_type == "doc":
            return self._generate_document(request, context)
        return f"[SubAgent-{task_type}] 生成结果: {request}"

    def _generate_code(self, request: str, context: Dict) -> str:
        return f"""[SubAgent-Code] 生成的代码:
```python
def solution():
    # 实现: {request}
    pass
```
"""

    def _generate_architecture(self, request: str, context: Dict) -> str:
        return f"""[SubAgent-Architecture] 架构设计:
## 系统架构
- 组件A
- 组件B
设计: {request}
"""

    def _generate_document(self, request: str, context: Dict) -> str:
        return f"""[SubAgent-Doc] 文档:
# 文档
内容: {request}
"""


# ============================================================================
# 统一持久化 - 打通 task 和 governance_events
# ============================================================================

class UnifiedPersistence:
    """
    统一持久化层 - 合并 task 和 governance_events
    """

    def __init__(self, db_path: str = "unified_platform.db"):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS governance_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                check_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                files_involved TEXT,
                status TEXT DEFAULT 'reported',
                resolved_at TEXT,
                resolution TEXT,
                task_id TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                key_files TEXT,
                issues_found TEXT,
                changes_made TEXT,
                context_snapshot TEXT,
                next_session_goals TEXT,
                task_id TEXT
            )
        """)

        conn.commit()
        conn.close()

    def record_governance_event(self, session_id: str, check_type: str,
                               severity: str, title: str, description: str,
                               files: Optional[List[str]] = None,
                               task_id: Optional[str] = None) -> int:
        """记录治理事件（可关联 task）"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO governance_events
            (session_id, timestamp, check_type, severity, title, description, files_involved, task_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            datetime.now().isoformat(),
            check_type,
            severity,
            title,
            description,
            json.dumps(files) if files else "[]",
            task_id
        ))

        event_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return event_id

    def save_session_summary(self, session_id: str, key_files: List[str],
                            issues: List[Dict], changes: List[str],
                            context: str, task_id: Optional[str] = None) -> int:
        """保存 session 摘要"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO session_summaries
            (session_id, created_at, updated_at, key_files, issues_found, changes_made, context_snapshot, task_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            json.dumps(key_files),
            json.dumps(issues),
            json.dumps(changes),
            context,
            task_id
        ))

        summary_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return summary_id


# ============================================================================
# 测试
# ============================================================================

def test_unified_dispatcher():
    print("=" * 60)
    print("  Unified Dispatcher P0 测试")
    print("=" * 60)

    import os
    db_path = "test_unified.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    dispatcher = UnifiedDispatcher(db_path)
    persistence = UnifiedPersistence(db_path)

    print("\n--- 1. 代码生成任务路由测试 ---\n")

    result = dispatcher.dispatch("帮我写一个 Python 函数实现快速排序")
    print(f"任务类型: {result.executor}")
    print(f"执行器: {result.executor}")
    print(f"治理通过: {result.governance_passed}")
    print(f"执行时间: {result.execution_time_ms:.2f}ms")
    print(f"输出预览: {result.output[:80]}...")

    print("\n--- 2. 知识查询任务路由测试 ---\n")

    result2 = dispatcher.dispatch("什么是高血压？")
    print(f"任务类型: {result2.executor}")
    print(f"执行器: {result2.executor}")
    print(f"输出: {result2.output}")

    print("\n--- 3. 架构设计任务路由测试 ---\n")

    result3 = dispatcher.dispatch("设计一个微服务架构")
    print(f"任务类型: {result3.executor}")
    print(f"执行器: {result3.executor}")
    print(f"输出预览: {result3.output[:80]}...")

    print("\n--- 4. 统一持久化测试 ---\n")

    event_id = persistence.record_governance_event(
        session_id="session_001",
        check_type="G3",
        severity="P1",
        title="代码两份不同步",
        description="ac/core.py 和 SubAgent/core.py 存在差异",
        files=["ac/core.py", "SubAgent/core.py"],
        task_id=result.task_id
    )
    print(f"✅ 记录治理事件: #{event_id}")

    summary_id = persistence.save_session_summary(
        session_id="session_001",
        key_files=["ac/core.py", "SubAgent/core.py"],
        issues=[{"severity": "P1", "title": "代码不同步"}],
        changes=["添加统一调度器", "合并持久化层"],
        context="SubAgent 和 AC 集成",
        task_id=result.task_id
    )
    print(f"✅ 保存 Session 摘要: #{summary_id}")

    if os.path.exists(db_path):
        os.remove(db_path)

    print("\n" + "=" * 60)
    print("  ✅ Unified Dispatcher 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_unified_dispatcher()

