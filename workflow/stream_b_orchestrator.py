"""workflow/stream_b_orchestrator.py
流 B · 多轮编排流
复杂路径：CLT → L0 → Orchestrator → PLAN → EXECUTE(多AI) → VERIFY → RESOLVE → Governance → CLT
适用于复杂任务，异步非阻塞，多轮多 Agent 协作完成。
"""

import sys, os, asyncio, uuid, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ac.orchestrator import Orchestrator, AgentSpec
from ac.governance import pipeline as gov_pipeline
from ac.guard import sanitize_text

DEFAULT_AGENT_POOL = {
    "backend_dev": AgentSpec(agent_id="backend_dev", capabilities=["backend", "database"]),
    "frontend_dev": AgentSpec(agent_id="frontend_dev", capabilities=["frontend", "ui"]),
    "security_expert": AgentSpec(agent_id="security_expert", capabilities=["security", "encryption"]),
    "qa_expert": AgentSpec(agent_id="qa_expert", capabilities=["testing", "validation"]),
    "architect": AgentSpec(agent_id="architect", capabilities=["architecture", "design"]),
}


def stream_b_process(
    prompt: str,
    session_id: str | None = None,
    agent_pool: dict | None = None,
    max_workers: int = 2,
    no_gov: bool = False,
) -> dict:
    """多轮编排流入口（同步包装）"""
    clean = sanitize_text(prompt)
    session_id = session_id or str(uuid.uuid4())
    pool = agent_pool or DEFAULT_AGENT_POOL

    orchestrator = Orchestrator(max_active_workers=max_workers)
    result = asyncio.run(orchestrator.orchestrate(clean, pool))

    output = {
        "stream": "B",
        "session_id": session_id,
        "status": result.status.value,
        "total_steps": result.metrics.total_steps,
        "completed_steps": result.metrics.completed_steps,
        "failed_steps": result.metrics.failed_steps,
        "elapsed_seconds": result.metrics.elapsed_seconds,
        "retry_count": result.metrics.retry_count,
        "hitl_interruptions": result.metrics.hitl_interruptions,
        "plan": [
            {
                "step_id": s.step_id,
                "description": s.description,
                "assigned_agent": s.assigned_agent,
                "status": s.status.value,
                "output": s.output,
            }
            for s in result.plan
        ],
    }

    if not no_gov:
        import json
        gov_result = gov_pipeline(
            json.dumps(output, ensure_ascii=False),
            {"command": "orchestrate", "session_id": session_id},
        )
        output["governance"] = gov_result

    return output
