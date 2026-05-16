from typing import Any

import json
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from ac.db import get_conn, load_experts, log_schedule, get_stats
from ac.seed import PRIORITY_MAP
from ac.classifier_fallback import semantic_fallback, category_fallback

CONFIG_CACHE: dict[str, Any] = {}
_log = logging.getLogger("ac.core")


def load_config(path: str = "ac/config.toml") -> dict[str, Any]:
    from pathlib import Path
    try:
        import tomllib
    except ImportError:
        return _load_config_legacy()
    p = Path(path)
    if not p.exists():
        return _default_config()
    with open(p, "rb") as f:
        return tomllib.load(f)


def _default_config() -> dict[str, Any]:
    return {
        "user": {"name": "User", "mode": "free"},
        "defaults": {"lease_rounds": 3, "psychologist_lease": 5, "max_active_workers": 2},
        "priority_order": {"P1": "安全", "P2": "权益", "P3": "心理", "P4": "技术", "P5": "通用"},
    }


def _load_config_legacy() -> dict[str, Any]:
    return _default_config()


def _dual_infer(query: str) -> dict[str, Any] | None:
    """对实质性查询执行双实例推理，失败返回 None"""
    if len(query.strip()) < 10:
        return None
    try:
        from ac.dual_inference import get_dual
        dual = get_dual()
        return dual.infer(query)
    except Exception as e:
        _log.warning(f"dual_inference failed: {e}")
        return None


def _contract_verify(response: dict[str, Any]) -> dict[str, Any]:
    """契约校验，失败则返回原始 dict"""
    try:
        from ac.schema_contract import validate_dispatch
        validated = validate_dispatch(response)
        result = validated.model_dump()
        for k, v in response.items():
            if k not in result:
                result[k] = v
        return result
    except Exception:
        return response


def dispatch(query: str, session_id: str | None = None, conn: object | None = None) -> dict[str, Any]:
    config = load_config()
    own_conn = False
    if conn is None:
        conn = get_conn(config)
        own_conn = True
    experts = load_experts(conn)

    session = session_id or str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat()

    if not experts:
        if own_conn:
            conn.close()
        return _contract_verify({
            "session_id": session, "query": query[:100], "matched_experts": [],
            "matched": [], "status": "error", "governance_passed": False,
            "dispatch_mode": "error", "timestamp": ts,
            "message": "专家表为空。请先运行: python ac/cli.py seed",
        })

    query_lower = query.lower()

    matches = []
    for e in experts:
        triggers = [t.strip().lower() for t in e["trigger_words"].split(",") if t.strip()]
        for t in triggers:
            if t in query_lower or query_lower.startswith(t) or query_lower.endswith(t):
                priority = PRIORITY_MAP.get(e.get("priority", "P5"), 5)
                matches.append({"expert": e, "triggered_by": t, "priority": priority})
                break

    matched_result = []

    if not matches:
        # ── 第一层兜底：语义匹配 ──
        semantic = semantic_fallback(query, experts, threshold=0.15)
        if semantic:
            for s in semantic:
                e = s["expert"]
                entry = {
                    "name": e["name"], "category": e["category"],
                    "triggered_by": f"semantic:{s['method']}(score={s['score']})",
                    "priority": e.get("priority", "P5"),
                    "lease": e.get("lease") or 3,
                    "role": e["role_definition"],
                    "rules": e.get("rules", ""),
                    "constraints": e.get("constraints", ""),
                }
                matched_result.append(entry)
            modes = "+".join(r["name"] for r in matched_result[:2])
            log_schedule(conn, session, query, modes, "semantic_fallback")
        else:
            # ── 第二层兜底：分类级兜底 ──
            cats = category_fallback(query)
            log_schedule(conn, session, query, "+".join(cats), "category_fallback")
            if own_conn:
                conn.close()
            return _contract_verify({
                "session_id": session, "query": query[:100], "matched_experts": [],
                "matched": [], "status": "unclassified" if "unclassified" in cats else "category_fallback",
                "governance_passed": False, "dispatch_mode": "category_fallback",
                "timestamp": ts, "categories": cats,
            })
    else:
        # ── 关键词匹配正常走，支持多标签 ──
        matches.sort(key=lambda m: m["priority"])
        for m in matches:
            e = m["expert"]
            entry = {
                "name": e["name"], "category": e["category"],
                "triggered_by": m["triggered_by"],
                "priority": f"P{m['priority']}",
                "lease": e.get("lease") or config["defaults"].get(
                    "psychologist_lease" if e["name"] == "心理医生" else "lease_rounds", 3
                ),
                "role": e["role_definition"],
                "rules": e["rules"], "constraints": e["constraints"],
            }
            matched_result.append(entry)
        modes = "+".join(r["name"] for r in matched_result)
        log_schedule(conn, session, query, modes, "dispatch")
    if own_conn:
        conn.close()

    # ── 纵向打通：双实例推理 → 契约验证 → 返回 ──
    response = {
        "session_id": session,
        "query": query[:100],
        "matched_experts": matched_result,
        "matched": matched_result,
        "status": "matched",
        "governance_passed": True,
        "dispatch_mode": "direct",
        "timestamp": ts,
    }
    dual_result = _dual_infer(query)
    if dual_result is not None:
        response["dual_inference"] = dual_result
        if not dual_result.get("consistent", True):
            response["governance_passed"] = False
            response["dispatch_mode"] = "direct+conflict"
    return _contract_verify(response)


def annotate(output: str, source_chain: list[str] | None = None) -> str:
    config = load_config()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    chain = source_chain or ["AC dispatch"]
    ctx = config.get("user", {}).get("name", "User")

    lines = output.strip().split("\n")
    annotated = []
    for i, line in enumerate(lines):
        if line.strip():
            annotated.append(f"[L5|{ctx}|{timestamp}|src:{chain[-1]}] {line}")
        else:
            annotated.append(line)

    header = (
        "━━━ L5 强制标注 ━━━\n"
        f"来源链: {' → '.join(chain)}\n"
        f"生成时间: {timestamp}\n"
        f"用户: {ctx}\n"
        f"声明: 本输出已由 AC L5 标注。AI 内容可能包含幻觉，请物理验证后采信。\n"
        f"━━━━━━━━━━━━━━━━\n"
    )

    return header + "\n".join(annotated)


def status() -> dict[str, Any]:
    config = load_config()
    conn = get_conn(config)
    stats = get_stats(conn)
    total = sum(stats.values())

    from pathlib import Path
    scores_path = Path(__file__).resolve().parent / "q_scores.md"

    return {
        "system": "AC = (E, D, S, Q)",
        "version": "v2.3",
        "experts": {**stats, "total": total},
        "config": {"user": config.get("user", {}), "defaults": config.get("defaults", {})},
        "score_doc": scores_path.name if scores_path.exists() else "N/A",
    }
