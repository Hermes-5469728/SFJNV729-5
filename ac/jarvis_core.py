"""
Jarvis · 统一对话引擎
串联: assistant(身份+记忆+规则) → dispatch → dual_inference → knowledge → governance → 格式化
原则: 任何环节失败不阻塞整体, 降级返回

Core协议集成:
  - 情绪危机检测 → 五层回复结构覆盖标准回复
  - ProactiveEngine → 事件驱动提醒追加在回复尾部
"""

from typing import Any, Optional

import uuid
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

_log = logging.getLogger("ac.jarvis")

AC_DIR = Path(__file__).resolve().parent


class JarvisResponse:
    __slots__ = (
        "session_id", "user_id", "query", "reply", "tone", "format",
        "matched_experts", "dispatch_mode", "knowledge_hits",
        "dual_consistent", "governance_passed", "timestamp",
        "sources", "warnings",
    )

    def __init__(
        self,
        session_id: str = "",
        user_id: str = "",
        query: str = "",
        reply: str = "",
        tone: str = "normal",
        fmt: str = "markdown",
        matched_experts: Optional[list[dict[str, Any]]] = None,
        dispatch_mode: str = "direct",
        knowledge_hits: int = 0,
        dual_consistent: Optional[bool] = None,
        governance_passed: bool = False,
        sources: Optional[list[str]] = None,
        warnings: Optional[list[str]] = None,
    ) -> None:
        self.session_id = session_id
        self.user_id = user_id
        self.query = query
        self.reply = reply
        self.tone = tone
        self.format = fmt
        self.matched_experts = matched_experts or []
        self.dispatch_mode = dispatch_mode
        self.knowledge_hits = knowledge_hits
        self.dual_consistent = dual_consistent
        self.governance_passed = governance_passed
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.sources = sources or []
        self.warnings = warnings or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "query": self.query,
            "reply": self.reply,
            "tone": self.tone,
            "format": self.format,
            "matched_experts": self.matched_experts,
            "dispatch_mode": self.dispatch_mode,
            "knowledge_hits": self.knowledge_hits,
            "dual_consistent": self.dual_consistent,
            "governance_passed": self.governance_passed,
            "timestamp": self.timestamp,
            "sources": self.sources,
            "warnings": self.warnings,
        }


class Jarvis:
    def __init__(self, db_path: str = "") -> None:
        self._db = db_path or str(AC_DIR / "ac_platform.db")

    def chat(
        self,
        query: str,
        user_id: str = "default",
        session_id: str = "",
        enable_dual: bool = True,
        enable_knowledge: bool = True,
    ) -> JarvisResponse:
        sid = session_id or str(uuid.uuid4())
        warnings: list[str] = []
        response = JarvisResponse(
            session_id=sid, user_id=user_id, query=query,
            warnings=warnings,
        )

        profile = self._load_profile(user_id)
        response.tone = profile.get("tone", "normal")
        response.format = profile.get("format", "markdown")

        # ── __init__ 特殊处理：返回主动问候 ──
        if query.strip() == "__init__":
            name = profile.get("name", "你")
            background = profile.get("background", [])
            ctx_lines = []
            for bg in background:
                try:
                    item = json.loads(bg) if isinstance(bg, str) else bg
                    if isinstance(item, dict) and "name" in item:
                        name = item["name"]
                except (json.JSONDecodeError, TypeError):
                    pass
            greeting = f"Shell在哦。{name}，你来了。"
            response.reply = greeting
            response.sources.append("jarvis_init")
            response.governance_passed = True
            self._remember(user_id, sid, query, greeting)
            return response

        rules_matched = self._match_rules(user_id, query)

        emotional_action = self._check_emotional_crisis(query)
        is_emotional = emotional_action is not None

        dispatch_result = self._run_dispatch(query, user_id, sid, profile)
        response.matched_experts = dispatch_result.get("matched_experts", [])
        response.dispatch_mode = dispatch_result.get("dispatch_mode", "direct")

        knowledge = None
        if enable_knowledge and not is_emotional:
            knowledge = self._retrieve_knowledge(query)
            response.knowledge_hits = knowledge.get("total_hits", 0)
            if knowledge.get("total_hits", 0) > 0:
                response.sources.append("knowledge_service")

        dual_result = None
        if enable_dual and not is_emotional and self._should_dual_verify(query, dispatch_result):
            dual_result = self._run_dual(query)
            if dual_result:
                response.dual_consistent = dual_result.get("consistent")
                if not dual_result.get("consistent"):
                    warnings.append(f"双实例推理不一致: {dual_result.get('conflict_type')}")
                    response.sources.append("dual_inference")
                else:
                    response.sources.append("dual_inference")

        if is_emotional:
            from assistant.emotional_protocol import default_emotional_reply
            raw_reply = default_emotional_reply(query, emotional_action)
            warnings.append("emotional_protocol_active")
        else:
            raw_reply = self._build_raw_reply(query, dispatch_result, dual_result, knowledge, rules_matched)

        gov_result = self._governance_check(raw_reply)
        if gov_result:
            response.governance_passed = gov_result.get("passed", False)
            if not gov_result.get("passed"):
                warnings.append("治理管道检查未完全通过")
            reply_text = gov_result.get("text", raw_reply)
        else:
            response.governance_passed = False
            reply_text = raw_reply
        response.sources.append("governance_pipeline")

        response.reply = self._format_reply(reply_text, profile, dispatch_result, knowledge, dual_result)

        pro_summary = self._check_proactive_events()
        if pro_summary:
            response.reply += "\n\n" + pro_summary
            response.sources.append("proactive_engine")

        self._remember(user_id, sid, query, response.reply)

        return response

    def _check_emotional_crisis(self, query: str) -> Optional[str]:
        try:
            from assistant.emotional_protocol import is_emotional_crisis
            return is_emotional_crisis(query)
        except Exception:
            return None

    def _check_proactive_events(self) -> str:
        try:
            from assistant.proactive_engine import get_engine
            engine = get_engine(self._db)
            return engine.summary()
        except Exception as e:
            _log.warning(f"proactive scan failed (non-fatal): {e}")
            return ""

    def _load_profile(self, user_id: str) -> dict[str, Any]:
        try:
            from assistant import AssistantOrchestrator
            orb = AssistantOrchestrator(self._db)
            pa = orb.for_user(user_id)
            p = pa.get_profile()
            profile = {
                "tone": p.preferences.tone.value if hasattr(p.preferences.tone, "value") else "normal",
                "length": p.preferences.length.value if hasattr(p.preferences.length, "value") else "normal",
                "format": p.preferences.format.value if hasattr(p.preferences.format, "value") else "markdown",
                "language": p.preferences.language,
                "user_id": user_id,
                "name": p.identity.name,
                "aliases": p.identity.aliases,
            }
            bg = pa.recall("profile_", limit=10)
            if bg:
                profile["background"] = [
                    m["content"] for m in bg if m.get("content")
                ]
                sys_lines = ["【用户画像】"]
                for m in bg:
                    content = m.get("content", "")
                    try:
                        item = json.loads(content) if isinstance(content, str) else content
                        if isinstance(item, dict):
                            for k, v in item.items():
                                sys_lines.append(f"- {k}: {v}")
                        else:
                            sys_lines.append(f"- {content[:100]}")
                    except (json.JSONDecodeError, TypeError):
                        sys_lines.append(f"- {content[:100]}")
                profile["system_prompt_suffix"] = "\n".join(sys_lines)
            return profile
        except Exception:
            return {"tone": "normal", "length": "normal", "format": "markdown", "language": "zh-CN"}

    def _match_rules(self, user_id: str, query: str) -> list[Any]:
        try:
            from assistant import AssistantOrchestrator
            orb = AssistantOrchestrator(self._db)
            pa = orb.for_user(user_id)
            return pa.match_rules(query)
        except Exception:
            return []

    def _run_dispatch(self, query: str, user_id: str, session_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        try:
            from ac.core import dispatch
            result = dispatch(query, session_id=session_id)
            result["_jarvis_user_id"] = user_id
            return result
        except Exception as e:
            _log.warning(f"dispatch failed: {e}")
            return {"matched_experts": [], "dispatch_mode": "error", "status": "error"}

    def _should_dual_verify(self, query: str, dispatch_result: dict[str, Any]) -> bool:
        if not dispatch_result.get("matched_experts"):
            return False
        policy_keywords = ["剂量", "药品", "药物", "法律", "合同", "安全", "诈骗", "医疗", "诊断"]
        query_lower = query.lower()
        return any(kw in query_lower for kw in policy_keywords)

    def _run_dual(self, query: str) -> Optional[dict[str, Any]]:
        try:
            from ac.dual_inference import get_dual
            dual = get_dual()
            return dual.infer(query)
        except Exception as e:
            _log.warning(f"dual inference failed: {e}")
            return None

    def _retrieve_knowledge(self, query: str) -> dict[str, Any]:
        try:
            from ac.knowledge_service import get_knowledge
            ks = get_knowledge()
            return ks.search(query, sources=["truth", "chroma"])
        except Exception:
            return {"total_hits": 0, "sources": {}}

    def _build_raw_reply(
        self,
        query: str,
        dispatch_result: dict[str, Any],
        dual_result: Optional[dict[str, Any]],
        knowledge: Optional[dict[str, Any]],
        rules: list[Any],
    ) -> str:
        parts: list[str] = []

        experts = dispatch_result.get("matched_experts", [])
        if experts:
            names = [e.get("name", "") for e in experts if e.get("name")]
            if names:
                parts.append(f"已匹配专家: {', '.join(names)}")

        if knowledge and knowledge.get("total_hits", 0) > 0:
            truths = knowledge.get("sources", {}).get("truth", [])
            if truths:
                parts.append(f"知识库匹配 {len(truths)} 条记录")
                verified = [t for t in truths if t.get("verified")]
                if verified:
                    top = verified[0]
                    parts.append(f"最可信来源: {top.get('title', '')}")

        if dual_result:
            if dual_result.get("consistent"):
                parts.append("双实例推理: 一致")
            else:
                parts.append(f"双实例推理: 冲突 ({dual_result.get('conflict_type', 'unknown')}) — 建议人工审查")

        if rules:
            rule_names = [r.name for r in rules if hasattr(r, 'name')]
            if rule_names:
                parts.append(f"触发规则: {', '.join(rule_names)}")

        if not parts:
            if dispatch_result.get("status") == "error":
                parts.append("调度引擎未匹配到专家，请尝试更具体的描述。")
            else:
                parts.append(f"收到查询: {query[:80]}")

        return "\n".join(parts)

    def _governance_check(self, text: str) -> Optional[dict[str, Any]]:
        try:
            from ac.governance import pipeline
            return pipeline(text, {"command": "jarvis_response"})
        except Exception as e:
            _log.warning(f"governance check failed: {e}")
            return None

    def _format_reply(
        self,
        raw: str,
        profile: dict[str, Any],
        dispatch_result: dict[str, Any],
        knowledge: Optional[dict[str, Any]],
        dual_result: Optional[dict[str, Any]],
    ) -> str:
        tone = profile.get("tone", "normal")
        fmt = profile.get("format", "markdown")

        if fmt == "json":
            import json
            return json.dumps({
                "reply": raw,
                "sources": self._collect_sources(knowledge, dispatch_result),
            }, ensure_ascii=False, indent=2)

        lines = [raw]

        sources = self._collect_sources(knowledge, dispatch_result)
        if sources:
            lines.append("")
            lines.append("---")
            lines.append("**来源**: " + ", ".join(sources))

        if dual_result and not dual_result.get("consistent"):
            lines.append("")
            lines.append("> 注意: 本回复经双实例推理验证，结果存在冲突，建议核实后采信。")

        return "\n".join(lines)

    def _collect_sources(self, knowledge: Optional[dict[str, Any]], dispatch_result: dict[str, Any]) -> list[str]:
        sources: list[str] = []
        if knowledge:
            truths = knowledge.get("sources", {}).get("truth", [])
            for t in truths[:3]:
                title = t.get("title", "")
                if title:
                    sources.append(title)
        experts = dispatch_result.get("matched_experts", [])
        for e in experts:
            name = e.get("name", "")
            if name:
                sources.append(name)
        return sources

    def _remember(self, user_id: str, session_id: str, query: str, reply: str) -> None:
        try:
            from assistant import AssistantOrchestrator
            orb = AssistantOrchestrator(self._db)
            pa = orb.for_user(user_id)
            pa.remember("query", query, confidence=0.5)
            pa.remember("reply", reply[:500], confidence=0.7)
        except Exception:
            pass


_jarvis: Optional[Jarvis] = None


def get_jarvis(db_path: str = "") -> Jarvis:
    global _jarvis
    if _jarvis is None:
        _jarvis = Jarvis(db_path)
    return _jarvis
