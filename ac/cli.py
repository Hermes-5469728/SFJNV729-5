#!/usr/bin/env python3
"""AC CLI · 便携式架构调度工具"""

import argparse
import json
import sys
import asyncio
from pathlib import Path

CLI_DIR = Path(__file__).resolve().parent  # ac/
REPO_ROOT = CLI_DIR.parent                  # repo root
sys.path.insert(0, str(REPO_ROOT))

from ac.guard import config_encoding, sanitize_text, flush_log, guard_exit, exit_fail, GuardExit, HeartbeatReporter, get_log

log = get_log()

config_encoding()

from ac.core import dispatch, annotate, status
from ac.seed import EXPERTS, PRIORITY_MAP
from ac.db import get_conn, _get_db_path, log_governance
from ac.governance import pipeline as gov_pipeline
from ac.collaborative_governor import (
    collaborative_governor,
    VerificationStatus,
    ContractStatus,
    ConcurrencyStatus,
    RiskLevel
)
from ac.orchestrator import Orchestrator, AgentSpec, TaskGraphManager
from ac.case_center import get_center, CaseCenter
from ac.aggregator import CrossSessionAggregator

# 导入Schema和自动修正器
from ac.schemas.orchestrator_schemas import (
    OrchestrateInput,
    OrchestrateOutput,
    VerifyInput,
    VerifyOutput,
    ContractInput,
    ContractOutput,
    StateInput,
    StateOutput,
    RiskInput,
    RiskOutput,
    LockInput,
    LockOutput,
    OrchStatusOutput
)
from ac.auto_corrector import auto_correct_validation_error
from pydantic import ValidationError
from assistant.schemas import Tone

_heartbeat = HeartbeatReporter()


@guard_exit
def cmd_dispatch(args):
    query = sanitize_text(args.input or sys.stdin.read().strip())
    if not query:
        exit_fail("error: 需要输入")
    # 案例检索
    cases = get_center().retrieve(query, top_k=2)
    if cases:
        log.info("命中 %d 条相似案例", len(cases))
        for c in cases:
            log.info("  [%.1f%%] %s (%s)", c["similarity"] * 100, c["goal"][:60], "成功" if c["success"] else "失败")
    config = {"paths": {"db_path": "ac_platform.db"}}
    conn = get_conn(config)
    result = dispatch(query, conn=conn)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.no_gov:
        print(output)
        conn.close()
        flush_log()
        return
    ctx = {"command": "dispatch", "query": query, "session_id": result.get("session_id", "")}
    try:
        gov_result = gov_pipeline(output, ctx)
    except Exception as e:
        print(output)
        log.warning("治理层异常: %s", e)
        gov_result = {"passed": True, "text": output, "checks": []}
    if not gov_result["passed"]:
        print(json.dumps({"status": "governance_failed", "session_id": result.get("session_id", ""), "governance": gov_result["checks"]}, ensure_ascii=False, indent=2))
        get_center().capture_failure(query, "dispatch", str(gov_result["checks"]), result=result, session_id=result.get("session_id", ""))
    else:
        print(gov_result["text"])
    try:
        log_governance(conn, result.get("session_id", ""), "dispatch", query, gov_result)
    except Exception as e:
        log.warning("日志写入失败: %s", e)
    finally:
        conn.close()
        flush_log()


@guard_exit
def cmd_annotate(args):
    output = sanitize_text(args.input or sys.stdin.read().strip())
    if not output:
        exit_fail("error: 需要输出内容")
    source = args.source.split(",") if args.source else None
    annotated = annotate(output, source_chain=source)
    if args.no_gov:
        print(annotated)
        flush_log()
        return
    ctx = {"command": "annotate", "source_chain": source}
    try:
        gov_result = gov_pipeline(annotated, ctx)
    except Exception as e:
        print(annotated)
        log.warning("治理层异常: %s", e)
        gov_result = {"passed": True, "text": annotated, "checks": []}
    if not gov_result["passed"]:
        print(f"━━━ 治理层警告 ━━━\n{annotated}\n\n⚠ 未通过 L5 校验:\n" + "\n".join(f"  [{c['checker']}] {c['message']}" for c in gov_result["checks"] if not c["passed"]))
    else:
        print(gov_result["text"])
    config = {"paths": {"db_path": "ac_platform.db"}}
    conn = get_conn(config)
    try:
        log_governance(conn, "", "annotate", output[:200], gov_result)
    except Exception as e:
        log.warning("日志写入失败: %s", e)
    finally:
        conn.close()
        flush_log()


def cmd_status(args):
    s = status()
    print(json.dumps(s, ensure_ascii=False, indent=2))
    flush_log()


@guard_exit
def cmd_seed(args):
    import sqlite3, uuid
    from datetime import datetime, timezone
    conn = get_conn({"paths": {"db_path": "ac_platform.db"}})
    existing = conn.execute("SELECT COUNT(*) FROM ac_experts").fetchone()[0]
    if existing > 0 and not args.force:
        print(f"ac_experts 已有 {existing} 行。使用 --force 覆盖。")
        conn.close()
        flush_log()
        return
    if args.force:
        conn.execute("DELETE FROM ac_experts")
        log.info("旧数据已清除")
    for e in EXPERTS:
        priority = e.get("priority", "P5")
        priority_num = PRIORITY_MAP.get(priority, 5)
        try:
            conn.execute("ALTER TABLE ac_experts ADD COLUMN priority VARCHAR(5) DEFAULT 'P5'")
        except sqlite3.OperationalError:
            pass
        conn.execute(
            "INSERT INTO ac_experts (expert_id, name, category, trigger_words, role_definition, rules, constraints, is_generic, version, created_at, updated_at, priority) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                e["name"],
                e["category"],
                e["trigger_words"],
                e["role_definition"],
                e["rules"],
                e["constraints"],
                1,
                "v2.3",
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
                e.get("priority", "P5"),
            ),
        )
    conn.commit()
    conn.close()
    print(f"已导入 {len(EXPERTS)} 个专家（L={sum(1 for e in EXPERTS if e['category']=='L')}, T={sum(1 for e in EXPERTS if e['category']=='T')}, M={sum(1 for e in EXPERTS if e['category']=='M')}, A={sum(1 for e in EXPERTS if e['category']=='A')}）")
    # 同步真值到案例库
    n = get_center().sync_truths()
    log.info("案例库同步完成: %d 条", n)
    flush_log()


def cmd_validate(args):
    print("运行 AC 验证...")
    try:
        from ac.qa.run_qa import main as run_qa
        run_qa()
    except Exception as e:
        exit_fail(f"QA 运行失败: {e}")
    flush_log()


def cmd_case(args):
    """案例中心管理"""
    center = get_center()
    if args.action == "sync":
        n = center.sync_truths()
        print(json.dumps({"synced": n}, ensure_ascii=False, indent=2))
    elif args.action == "stats":
        print(json.dumps(center.stats(), ensure_ascii=False, indent=2))
    elif args.action == "retrieve":
        cases = center.retrieve(args.query, top_k=args.top_k)
        print(json.dumps(cases, ensure_ascii=False, indent=2))
    elif args.action == "capture":
        r = center.capture_failure(args.query, args.command, args.error)
        print(json.dumps({"case_id": r.case_id, "success": r.success}, ensure_ascii=False, indent=2))
    flush_log()


# ========== 协同治理层命令 ==========

def cmd_verify(args):
    """端到端验证命令"""
    try:
        params = json.loads(args.params) if args.params else {}
        
        # Schema验证
        input_data = {
            "task_id": args.task_id,
            "type": args.type,
            "params": params
        }
        
        try:
            validated_input = VerifyInput(**input_data)
        except ValidationError as e:
            # 尝试自动修正
            corrected = asyncio.run(auto_correct_validation_error(e, input_data))
            if corrected:
                print(f"🔧 自动修正验证输入: {json.dumps(corrected, ensure_ascii=False)}")
                validated_input = VerifyInput(**corrected)
            else:
                exit_fail(f"验证输入不合法: {e}")
        
        result = asyncio.run(collaborative_governor.verify_task(
            validated_input.task_id, validated_input.type, validated_input.params
        ))
        
        # 输出验证
        output_data = {
            "task_id": result.task_id,
            "status": result.status.value,
            "message": result.message,
            "evidence": result.evidence,
            "latency_ms": result.latency_ms
        }
        VerifyOutput(**output_data)
        
        print(json.dumps(output_data, ensure_ascii=False, indent=2))
    except json.JSONDecodeError as e:
        exit_fail(f"参数解析失败: {e}")
    flush_log()


def cmd_contract(args):
    """契约校验命令"""
    try:
        output = json.loads(args.output) if args.output else {}
        
        # Schema验证
        input_data = {
            "agent_id": args.agent_id,
            "output": output
        }
        
        try:
            validated_input = ContractInput(**input_data)
        except ValidationError as e:
            corrected = asyncio.run(auto_correct_validation_error(e, input_data))
            if corrected:
                print(f"🔧 自动修正契约输入: {json.dumps(corrected, ensure_ascii=False)}")
                validated_input = ContractInput(**corrected)
            else:
                exit_fail(f"契约输入不合法: {e}")
        
        status, violations = collaborative_governor.validate_agent_output(
            validated_input.agent_id, validated_input.output
        )
        
        # 输出验证
        output_data = {
            "agent_id": validated_input.agent_id,
            "status": status.value,
            "violations": [v.__dict__ for v in violations]
        }
        ContractOutput(**output_data)
        
        print(json.dumps(output_data, ensure_ascii=False, indent=2))
    except json.JSONDecodeError as e:
        exit_fail(f"输出解析失败: {e}")
    flush_log()


def cmd_state(args):
    """状态管理命令"""
    try:
        data = json.loads(args.data) if args.data else None
        
        # Schema验证
        input_data = {
            "task_id": args.task_id,
            "agent_id": args.agent_id,
            "status": args.status,
            "data": data
        }
        
        try:
            validated_input = StateInput(**input_data)
        except ValidationError as e:
            corrected = asyncio.run(auto_correct_validation_error(e, input_data))
            if corrected:
                print(f"🔧 自动修正状态输入: {json.dumps(corrected, ensure_ascii=False)}")
                validated_input = StateInput(**corrected)
            else:
                exit_fail(f"状态输入不合法: {e}")
        
        result = collaborative_governor.update_task(
            validated_input.task_id, validated_input.agent_id, 
            validated_input.status, validated_input.data or {}
        )
        
        # 输出验证
        output_data = {
            "task_id": validated_input.task_id,
            "status": result.value,
            "version": 1
        }
        StateOutput(**output_data)
        
        print(json.dumps(output_data, ensure_ascii=False, indent=2))
    except json.JSONDecodeError as e:
        exit_fail(f"数据解析失败: {e}")
    flush_log()


def cmd_risk(args):
    """风险评估命令"""
    # Schema验证
    input_data = {"operation": args.operation}
    
    try:
        validated_input = RiskInput(**input_data)
    except ValidationError as e:
        corrected = asyncio.run(auto_correct_validation_error(e, input_data))
        if corrected:
            print(f"🔧 自动修正风险输入: {json.dumps(corrected, ensure_ascii=False)}")
            validated_input = RiskInput(**corrected)
        else:
            exit_fail(f"风险输入不合法: {e}")
    
    allowed, assessment = collaborative_governor.high_risk_interceptor.intercept(validated_input.operation)
    
    # 输出验证
    output_data = {
        "operation": validated_input.operation,
        "allowed": allowed,
        "risk_level": assessment.level.value,
        "reason": assessment.reason,
        "requires_confirmation": assessment.requires_confirmation,
        "alternatives": assessment.alternatives
    }
    RiskOutput(**output_data)
    
    print(json.dumps(output_data, ensure_ascii=False, indent=2))
    flush_log()


def cmd_complete(args):
    """完整任务完成流程（契约校验 + 端到端验证 + 状态更新）"""
    try:
        output = json.loads(args.output) if args.output else {}
        verification_spec = json.loads(args.verification) if args.verification else None
        
        result = asyncio.run(collaborative_governor.complete_task_with_validation(
            args.task_id, args.agent_id, output, verification_spec
        ))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except json.JSONDecodeError as e:
        exit_fail(f"参数解析失败: {e}")
    flush_log()


def cmd_lock(args):
    """资源锁管理命令"""
    # Schema验证
    input_data = {
        "action": args.action,
        "resource_id": args.resource_id,
        "holder_id": args.holder_id
    }
    
    try:
        validated_input = LockInput(**input_data)
    except ValidationError as e:
        corrected = asyncio.run(auto_correct_validation_error(e, input_data))
        if corrected:
            print(f"🔧 自动修正锁输入: {json.dumps(corrected, ensure_ascii=False)}")
            validated_input = LockInput(**corrected)
        else:
            exit_fail(f"锁输入不合法: {e}")
    
    if validated_input.action == "acquire":
        success = collaborative_governor.acquire_resource_lock(
            validated_input.resource_id, validated_input.holder_id
        )
    else:
        collaborative_governor.release_resource_lock(
            validated_input.resource_id, validated_input.holder_id
        )
        success = True
    
    # 输出验证
    output_data = {
        "action": validated_input.action,
        "resource_id": validated_input.resource_id,
        "holder_id": validated_input.holder_id,
        "success": success
    }
    LockOutput(**output_data)
    
    print(json.dumps(output_data, ensure_ascii=False, indent=2))
    flush_log()


# ========== Orchestrator 命令 ==========

def cmd_orchestrate(args):
    """多轮规划编排命令"""
    # Schema验证
    input_data = {
        "prompt": args.prompt,
        "agents": args.agent,
        "max_workers": 2
    }
    
    try:
        validated_input = OrchestrateInput(**input_data)
    except ValidationError as e:
        corrected = asyncio.run(auto_correct_validation_error(e, input_data))
        if corrected:
            print(f"🔧 自动修正编排输入: {json.dumps(corrected, ensure_ascii=False)}")
            validated_input = OrchestrateInput(**corrected)
        else:
            exit_fail(f"编排输入不合法: {e}")
    
    orchestrator = Orchestrator(max_active_workers=validated_input.max_workers)
    
    # 构建 Agent 池
    agent_pool = {}
    if validated_input.agents:
        for agent_id in validated_input.agents:
            agent_pool[agent_id] = AgentSpec(agent_id=agent_id, capabilities=["general"])
    else:
        # 默认 Agent 池
        agent_pool = {
            "backend_dev": AgentSpec(agent_id="backend_dev", capabilities=["backend", "database"]),
            "security_expert": AgentSpec(agent_id="security_expert", capabilities=["security", "encryption"]),
            "frontend_dev": AgentSpec(agent_id="frontend_dev", capabilities=["frontend", "ui"]),
            "qa_expert": AgentSpec(agent_id="qa_expert", capabilities=["testing", "validation"])
        }
    
    # 执行编排
    result = asyncio.run(orchestrator.orchestrate(validated_input.prompt, agent_pool))
    
    # 输出验证
    steps_output = []
    for step in result.plan:
        step_data = {
            "step_id": step.step_id,
            "status": step.status.value,
            "description": step.description,
            "assigned_agent": step.assigned_agent,
            "output": step.output
        }
        steps_output.append(step_data)
    
    output_data = {
        "session_id": result.session_id,
        "status": result.status.value,
        "total_steps": result.metrics.total_steps,
        "completed_steps": result.metrics.completed_steps,
        "failed_steps": result.metrics.failed_steps,
        "elapsed_seconds": result.metrics.elapsed_seconds,
        "steps": steps_output
    }
    OrchestrateOutput(**output_data)
    
    print(f"\n🎉 编排完成 ({result.status.value})")
    print(f"会话ID: {result.session_id}")
    
    if "final_summary" in result.shared_context:
        print("\n📋 任务摘要:")
        summary = result.shared_context["final_summary"]
        for step in summary["steps"]:
            content = step["output"].get("content", "") if isinstance(step["output"], dict) else str(step["output"])
            print(f"  - {step['step_id']}: {content[:50]}...")
    flush_log()


def cmd_orch_status(args):
    """查询编排状态"""
    manager = TaskGraphManager()
    graph = manager.load_graph(args.session_id)
    
    if graph:
        # 构建输出数据
        steps_output = [{
            "step_id": s.step_id,
            "status": s.status.value,
            "description": s.description,
            "assigned_agent": s.assigned_agent,
            "retry_count": s.retry_count
        } for s in graph.plan]
        
        output_data = {
            "session_id": graph.session_id,
            "status": graph.status.value,
            "root_prompt": graph.root_prompt,
            "metrics": {
                "total_steps": graph.metrics.total_steps,
                "completed_steps": graph.metrics.completed_steps,
                "failed_steps": graph.metrics.failed_steps,
                "elapsed_seconds": graph.metrics.elapsed_seconds,
                "retry_count": graph.metrics.retry_count,
                "hitl_interruptions": graph.metrics.hitl_interruptions
            },
            "steps": steps_output
        }
        
        # Schema验证
        OrchStatusOutput(**output_data)
        
        print(json.dumps(output_data, ensure_ascii=False, indent=2))
    else:
        print(f"未找到会话: {args.session_id}")
    flush_log()


def cmd_orch_list(args):
    """列出所有编排任务"""
    import sqlite3
    conn = sqlite3.connect("ac_platform.db")
    cursor = conn.cursor()
    cursor.execute('SELECT session_id, status, root_prompt, created_at FROM task_graphs ORDER BY created_at DESC')
    
    sessions = []
    for row in cursor.fetchall():
        sessions.append({
            "session_id": row[0],
            "status": row[1],
            "root_prompt": row[2][:50] + "..." if len(row[2]) > 50 else row[2],
            "created_at": row[3]
        })
    
    conn.close()
    print(json.dumps(sessions, ensure_ascii=False, indent=2))
    flush_log()


def cmd_assistant(args):
    """Personal Assistant 助手管理"""
    from assistant import (
        PersonalAssistant, AssistantProfile, Identity, Preferences, Tone,
        BehaviorRule, TriggerDef, TriggerMatch, Priority,
    )
    pa = PersonalAssistant(user_id=args.user_id)

    if args.action == "profile":
        profile = pa.get_profile()
        import dataclasses
        print(json.dumps(dataclasses.asdict(profile), ensure_ascii=False, indent=2))

    elif args.action == "update":
        overlay = AssistantProfile()
        if args.name:
            overlay.identity = Identity(user_id=args.user_id, name=args.name)
        if args.tone:
            try:
                overlay.preferences.tone = Tone(args.tone)
            except ValueError:
                exit_fail(f"不支持的语气: {args.tone}，可选: {[t.value for t in Tone]}")
        if args.language:
            overlay.preferences.language = args.language
        if args.auto_greeting is not None:
            overlay.preferences.auto_greeting = args.auto_greeting == "true"
        if args.expert:
            from assistant.schemas import DomainConfig, ExpertiseLevel
            overlay.knowledge.domains = [DomainConfig(domain=d, expertise=ExpertiseLevel.ADVANCED) for d in args.expert]
        pa.update_profile(overlay)
        print(json.dumps({"updated": True, "user_id": args.user_id}, ensure_ascii=False, indent=2))

    elif args.action == "remember":
        pa.remember(args.topic, args.content, confidence=args.confidence)
        print(json.dumps({"remembered": True, "topic": args.topic}, ensure_ascii=False, indent=2))

    elif args.action == "recall":
        memories = pa.recall(args.topic, limit=args.limit)
        print(json.dumps(memories, ensure_ascii=False, indent=2))

    elif args.action == "rule-add":
        rule = BehaviorRule(
            name=args.name or "untitled",
            triggers=[TriggerDef(match_type=TriggerMatch.CONTAINS, pattern=p) for p in args.trigger],
            response_template=args.template or "",
        )
        rule_id = pa.add_rule(rule)
        print(json.dumps({"rule_id": rule_id}, ensure_ascii=False, indent=2))

    elif args.action == "rule-list":
        from assistant.rules import RuleEngine
        re = RuleEngine()
        rules = re.get_for_user(args.user_id)
        output = [{"id": r.rule_id, "name": r.name, "priority": r.priority.value, "triggers": [t.pattern for t in r.triggers]} for r in rules]
        print(json.dumps(output, ensure_ascii=False, indent=2))

    elif args.action == "context":
        from assistant.context_loader import build_assistant_context
        print(build_assistant_context(args.user_id))

    flush_log()


def cmd_aggregate(args):
    """跨对话聚合面板"""
    agg = CrossSessionAggregator()
    if args.list_dates:
        dates = agg.get_date_range()
        print(json.dumps(dates, ensure_ascii=False, indent=2))
        flush_log()
        return
    if args.start:
        result = agg.aggregate_range(args.start, args.end)
    else:
        result = agg.aggregate_all(args.date)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    flush_log()


def main():
    parser = argparse.ArgumentParser(description="AC CLI · 架构调度与标注工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 原有命令
    dispatch_parser = subparsers.add_parser("dispatch", help="调度专家")
    dispatch_parser.add_argument("input", nargs="?", default="", help="输入文本")
    dispatch_parser.add_argument("--no-gov", action="store_true", help="跳过治理层")

    annotate_parser = subparsers.add_parser("annotate", help="L5标注")
    annotate_parser.add_argument("input", nargs="?", default="", help="输出内容")
    annotate_parser.add_argument("--source", default="", help="来源链（逗号分隔）")
    annotate_parser.add_argument("--no-gov", action="store_true", help="跳过治理层")

    status_parser = subparsers.add_parser("status", help="状态查询")

    seed_parser = subparsers.add_parser("seed", help="初始化专家数据")
    seed_parser.add_argument("--force", action="store_true", help="强制覆盖")

    validate_parser = subparsers.add_parser("validate", help="运行QA验证")

    # 协同治理层命令
    verify_parser = subparsers.add_parser("verify", help="端到端验证")
    verify_parser.add_argument("--task-id", required=True, help="任务ID")
    verify_parser.add_argument("--type", required=True, choices=["url", "database", "file"], help="验证类型")
    verify_parser.add_argument("--params", required=True, help="验证参数（JSON）")

    contract_parser = subparsers.add_parser("contract", help="契约校验")
    contract_parser.add_argument("--agent-id", required=True, help="Agent ID")
    contract_parser.add_argument("--output", required=True, help="输出数据（JSON）")

    state_parser = subparsers.add_parser("state", help="状态管理")
    state_parser.add_argument("--task-id", required=True, help="任务ID")
    state_parser.add_argument("--agent-id", required=True, help="Agent ID")
    state_parser.add_argument("--status", required=True, help="状态")
    state_parser.add_argument("--data", help="数据（JSON）")

    risk_parser = subparsers.add_parser("risk", help="风险评估")
    risk_parser.add_argument("--operation", required=True, help="操作命令")

    complete_parser = subparsers.add_parser("complete", help="完整任务流程")
    complete_parser.add_argument("--task-id", required=True, help="任务ID")
    complete_parser.add_argument("--agent-id", required=True, help="Agent ID")
    complete_parser.add_argument("--output", required=True, help="输出数据（JSON）")
    complete_parser.add_argument("--verification", help="验证配置（JSON）")

    lock_parser = subparsers.add_parser("lock", help="资源锁管理")
    lock_parser.add_argument("action", choices=["acquire", "release"], help="操作")
    lock_parser.add_argument("--resource-id", required=True, help="资源ID")
    lock_parser.add_argument("--holder-id", required=True, help="持有者ID")

    # Orchestrator 命令
    orch_parser = subparsers.add_parser("orchestrate", help="多轮规划编排")
    orch_parser.add_argument("--prompt", "-p", required=True, help="任务提示")
    orch_parser.add_argument("--agent", "-a", action="append", help="可用Agent（可多次）")

    orch_status_parser = subparsers.add_parser("orch-status", help="查询编排状态")
    orch_status_parser.add_argument("--session-id", required=True, help="会话ID")

    orch_list_parser = subparsers.add_parser("orch-list", help="列出编排任务")

    # 案例中心
    case_parser = subparsers.add_parser("case", help="案例中心管理")
    case_sub = case_parser.add_subparsers(dest="action")
    case_sync = case_sub.add_parser("sync", help="同步 ac_truth → ChromaDB")
    case_stats = case_sub.add_parser("stats", help="案例库统计")
    case_ret = case_sub.add_parser("retrieve", help="检索相似案例")
    case_ret.add_argument("--query", required=True, help="查询文本")
    case_ret.add_argument("--top-k", type=int, default=3, help="返回数量")
    case_cap = case_sub.add_parser("capture", help="手动捕获案例")
    case_cap.add_argument("--query", required=True, help="查询")
    case_cap.add_argument("--command", default="manual", help="命令")
    case_cap.add_argument("--error", required=True, help="错误信息")

    # 真值验证与存储（0.5层强制校验）
    case_ver = case_sub.add_parser("verify", help="审计真值验证状态")
    case_store = case_sub.add_parser("store", help="验证后入库")
    case_store.add_argument("--title", required=True, help="标题")
    case_store.add_argument("--content", required=True, help="内容")
    case_store.add_argument("--category", default="", help="分类")
    case_store.add_argument("--source", default="", help="来源")
    case_store.add_argument("--tags", default="", help="标签")

    # 助手管理
    asst_parser = subparsers.add_parser("assistant", help="Personal Assistant 管理")
    asst_sub = asst_parser.add_subparsers(dest="action")
    asst_parser.add_argument("--user-id", default="default", help="用户ID")

    asst_profile = asst_sub.add_parser("profile", help="查看画像")
    asst_profile.add_argument("--user-id", default="default", help="用户ID")

    asst_update = asst_sub.add_parser("update", help="更新画像")
    asst_update.add_argument("--user-id", default="default", help="用户ID")
    asst_update.add_argument("--name", help="名称")
    asst_update.add_argument("--tone", choices=[t.value for t in Tone], help="语气")
    asst_update.add_argument("--language", help="语言")
    asst_update.add_argument("--auto-greeting", type=str, choices=["true","false"], help="首次对话自动问候")
    asst_update.add_argument("--expert", action="append", help="专业领域（可多次）")

    asst_rem = asst_sub.add_parser("remember", help="写入记忆")
    asst_rem.add_argument("--user-id", default="default", help="用户ID")
    asst_rem.add_argument("--topic", required=True, help="主题")
    asst_rem.add_argument("--content", required=True, help="内容")
    asst_rem.add_argument("--confidence", type=float, default=1.0, help="置信度")

    asst_recall = asst_sub.add_parser("recall", help="查询记忆")
    asst_recall.add_argument("--user-id", default="default", help="用户ID")
    asst_recall.add_argument("--topic", required=True, help="主题")
    asst_recall.add_argument("--limit", type=int, default=5, help="数量")

    asst_rule = asst_sub.add_parser("rule-add", help="添加规则")
    asst_rule.add_argument("--user-id", default="default", help="用户ID")
    asst_rule.add_argument("--name", help="规则名称")
    asst_rule.add_argument("--trigger", required=True, action="append", help="触发词（可多次）")
    asst_rule.add_argument("--template", help="响应模板")

    asst_rlist = asst_sub.add_parser("rule-list", help="列出规则")
    asst_rlist.add_argument("--user-id", default="default", help="用户ID")

    asst_ctx = asst_sub.add_parser("context", help="输出对话前提文本")
    asst_ctx.add_argument("--user-id", default="default", help="用户ID")

    # 聚合面板
    aggregate_parser = subparsers.add_parser("aggregate", help="跨对话聚合面板")
    aggregate_parser.add_argument("--date", "-d", default=None, help="日期 YYYY-MM-DD")
    aggregate_parser.add_argument("--start", default=None, help="起始日期")
    aggregate_parser.add_argument("--end", default=None, help="结束日期")
    aggregate_parser.add_argument("--list-dates", action="store_true", help="列出有数据的日期")

    args = parser.parse_args()

    cmds = {
        "dispatch": cmd_dispatch,
        "annotate": cmd_annotate,
        "status": cmd_status,
        "seed": cmd_seed,
        "validate": cmd_validate,
        "verify": cmd_verify,
        "contract": cmd_contract,
        "state": cmd_state,
        "risk": cmd_risk,
        "complete": cmd_complete,
        "lock": cmd_lock,
        "orchestrate": cmd_orchestrate,
        "orch-status": cmd_orch_status,
        "orch-list": cmd_orch_list,
        "case": cmd_case,
        "aggregate": cmd_aggregate,
        "assistant": cmd_assistant,
    }

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if not _heartbeat.can_proceed():
        exit_fail(f"熔断器打开 ({_heartbeat.cb.state})，拒绝执行 {args.command}")
    try:
        _heartbeat.start(command=args.command)
        cmds[args.command](args)
        _heartbeat.stop()
    except GuardExit:
        _heartbeat.fail()
        raise
    except SystemExit:
        _heartbeat.stop()
        raise
    except Exception as e:
        _heartbeat.fail()
        exit_fail(f"{e}")
    finally:
        flush_log()


def cmd_case(args):
    """案例中心管理"""
    center = get_center()
    if args.action == "sync":
        n = center.sync_truths()
        print(json.dumps({"synced": n}, ensure_ascii=False, indent=2))
    elif args.action == "stats":
        print(json.dumps(center.stats(), ensure_ascii=False, indent=2))
    elif args.action == "retrieve":
        cases = center.retrieve(args.query, top_k=args.top_k)
        print(json.dumps(cases, ensure_ascii=False, indent=2))
    elif args.action == "capture":
        r = center.capture_failure(args.query, args.command, args.error)
        print(json.dumps({"case_id": r.case_id, "success": r.success}, ensure_ascii=False, indent=2))
    elif args.action == "verify":
        from ac.validator import validate_truth
        conn = get_conn({"paths": {"db_path": "ac_platform.db"}})
        rows = conn.execute("SELECT rowid, title, content, verified, tags FROM ac_truth ORDER BY rowid").fetchall()
        conn.close()
        results = {"L5": 0, "L2": 0, "L0": 0, "FAIL": 0}
        mislabeled = 0
        details = []
        for rowid, title, content, verified, tags in rows:
            vr = validate_truth(title, content)
            key = vr.level if vr.passed else "FAIL"
            results[key] += 1
            if verified == 1 and key != "L5":
                mislabeled += 1
                details.append({"rowid": rowid, "title": title[:40], "level": key, "score": vr.score})
        print(json.dumps({
            "total": len(rows),
            "L5_trusted": results["L5"],
            "L2_needs_review": results["L2"],
            "L0_assumption": results["L0"],
            "FAIL_no_source": results["FAIL"],
            "mislabeled_verified1_but_below_L5": mislabeled,
            "details": details[:10],
        }, ensure_ascii=False, indent=2))
    elif args.action == "store":
        title = args.title
        content = args.content
        from ac.validator import validate_truth
        vr = validate_truth(title, content)
        conn = get_conn({"paths": {"db_path": "ac_platform.db"}})
        import uuid, json as _json, datetime as _dt
        conn.execute(
            "INSERT INTO ac_truth (truth_id, title, category, source, content, truth_count, verified, tags, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), title, args.category or "unclassified", args.source or "manual",
             content, 1, 1 if vr.passed and vr.level == "L5" else 0,
             f"{args.tags or ''} [v{vr.level}:{vr.score:.1f}]",
             _dt.datetime.now(_dt.timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()
        print(_json.dumps({
            "stored": True, "title": title[:40],
            "verified": 1 if vr.passed and vr.level == "L5" else 0,
            "validation": {"level": vr.level, "score": vr.score, "checks": vr.checks},
        }, ensure_ascii=False, indent=2))
    flush_log()


if __name__ == "__main__":
    main()
