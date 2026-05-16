"""Personal Assistant — 核心引擎"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional

from .schemas import AssistantProfile, BehaviorRule
from .profile import ProfileStore, get_default_profile
from .rules import RuleEngine
from .memory import PersonalMemory
from .config import load_config, save_config


class PersonalAssistant:
    def __init__(self, user_id: str = "", db_path: str = ""):
        self._db_path = db_path
        self.user_id = user_id or "default"
        self._profiles = ProfileStore(db_path)
        self._rules = RuleEngine(db_path)
        self._memory = PersonalMemory(db_path)
        self._profile: AssistantProfile = self._load_profile()

    def _load_profile(self) -> AssistantProfile:
        p = self._profiles.get(self.user_id)
        if p:
            return p
        return get_default_profile()

    def get_profile(self) -> AssistantProfile:
        return self._profile

    def update_profile(self, overlay: AssistantProfile):
        self._profile = self._profile.merge(overlay)
        self._profiles.save(self.user_id, self._profile)

    def add_rule(self, rule: BehaviorRule) -> str:
        return self._rules.add(self.user_id, rule)

    def match_rules(self, query: str) -> list[BehaviorRule]:
        rules = self._rules.get_for_user(self.user_id)
        return self._rules.match(query, rules)

    def remember(self, topic: str, content: str, confidence: float = 1.0):
        self._memory.remember(self.user_id, topic, content, confidence=confidence)

    def recall(self, topic: str, limit: int = 5) -> list[dict]:
        return self._memory.recall(self.user_id, topic, limit)

    def apply_preferences(self, dispatch_result: dict) -> dict:
        pref = self._profile.preferences
        result = dict(dispatch_result)
        tone_val = pref.tone.value if hasattr(pref.tone, "value") else pref.tone
        length_val = pref.length.value if hasattr(pref.length, "value") else pref.length
        fmt_val = pref.format.value if hasattr(pref.format, "value") else pref.format
        result["_assistant"] = {
            "user_id": self.user_id,
            "tone": tone_val,
            "length": length_val,
            "format": fmt_val,
            "language": pref.language,
            "temperature": pref.temperature,
        }
        routing = self._profile.routing
        if routing.preferred_experts:
            result["_assistant"]["preferred_experts"] = routing.preferred_experts
        if routing.default_expert:
            result["_assistant"]["default_expert"] = routing.default_expert
        return result


class AssistantOrchestrator:
    def __init__(self, db_path: str = ""):
        self._db_path = db_path
        self._sessions: Dict[str, PersonalAssistant] = {}

    def for_user(self, user_id: str = "") -> PersonalAssistant:
        uid = user_id or "default"
        if uid not in self._sessions:
            self._sessions[uid] = PersonalAssistant(uid, self._db_path)
        return self._sessions[uid]

    def process(self, query: str, user_id: str = "", session_id: str = "") -> dict:
        uid = user_id or "default"
        sid = session_id or str(uuid.uuid4())
        pa = self.for_user(uid)
        profile = pa.get_profile()
        matched_rules = pa.match_rules(query)
        pa.remember("query", query, confidence=0.5)
        for rule in matched_rules:
            pa.remember("rule_match", f"{rule.name}: {query}", confidence=0.8)
        return {
            "assistant": True,
            "user_id": uid,
            "session_id": sid,
            "query": query,
            "profile": {
                "identity": profile.identity.__dict__,
                "preferences": {k: v.value if hasattr(v, "value") else v for k, v in profile.preferences.__dict__.items()},
            },
            "matched_rules": [{"id": r.rule_id, "name": r.name, "priority": r.priority.value} for r in matched_rules],
        }
