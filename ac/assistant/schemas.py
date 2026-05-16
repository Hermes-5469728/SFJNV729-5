"""Personal Assistant — 绝对颗粒度 Schema"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum


# ── Enums ──────────────────────────────────────────────

class Tone(str, Enum):
    NORMAL = "normal"
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    EMPATHETIC = "empathetic"
    CONCISE = "concise"

class ResponseLength(str, Enum):
    TERSE = "terse"
    NORMAL = "normal"
    DETAILED = "detailed"

class Format(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"

class ExpertiseLevel(int, Enum):
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4

class Priority(str, Enum):
    P1_SAFETY = "P1"
    P2_RIGHTS = "P2"
    P3_PSYCHOLOGY = "P3"
    P4_TECH = "P4"
    P5_GENERAL = "P5"

class TriggerMatch(str, Enum):
    EXACT = "exact"
    PREFIX = "prefix"
    SUFFIX = "suffix"
    CONTAINS = "contains"
    REGEX = "regex"
    SEMANTIC = "semantic"

class TimeWindow(str, Enum):
    MORNING = "06:00-12:00"
    AFTERNOON = "12:00-18:00"
    EVENING = "18:00-22:00"
    NIGHT = "22:00-06:00"
    ALL_DAY = "00:00-23:59"


# ── Identity ────────────────────────────────────────────

@dataclass
class Identity:
    user_id: str = ""
    name: str = ""
    aliases: List[str] = field(default_factory=list)
    role: str = "user"
    group: str = "default"
    tenant: str = "default"


# ── Preferences (8 dimensions × atomic values) ──────────

@dataclass
class Preferences:
    tone: Tone = Tone.NORMAL
    length: ResponseLength = ResponseLength.NORMAL
    format: Format = Format.MARKDOWN
    language: str = "zh-CN"
    temperature: float = 0.7
    verbosity: int = 5
    emoji_enabled: bool = False
    code_highlight: bool = True
    auto_correct: bool = True
    expert_auto_select: bool = True
    auto_greeting: bool = True


# ── Behavior ────────────────────────────────────────────

@dataclass
class TriggerDef:
    match_type: TriggerMatch = TriggerMatch.CONTAINS
    pattern: str = ""
    case_sensitive: bool = False

@dataclass
class BehaviorRule:
    rule_id: str = ""
    name: str = ""
    enabled: bool = True
    priority: Priority = Priority.P5_GENERAL
    triggers: list[TriggerDef] = field(default_factory=list)
    response_template: str = ""
    fallback_strategy: str = "pass"
    escalation: str = ""
    cooldown_seconds: int = 0


# ── Knowledge ───────────────────────────────────────────

@dataclass
class DomainConfig:
    domain: str = ""
    expertise: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    sources_whitelist: List[str] = field(default_factory=list)
    sources_blacklist: List[str] = field(default_factory=list)

@dataclass
class KnowledgeProfile:
    domains: list[DomainConfig] = field(default_factory=list)
    max_context_tokens: int = 4096
    truth_min_confidence: float = 0.6


# ── Memory ──────────────────────────────────────────────

@dataclass
class MemoryConfig:
    max_session_history: int = 100
    long_term_enabled: bool = True
    decay_days: int = 30
    topics_auto_extract: bool = True
    vector_search_enabled: bool = False


# ── Safety ──────────────────────────────────────────────

@dataclass
class SafetyConfig:
    priority_map: Dict[str, str] = field(default_factory=lambda: {
        "P1": "安全", "P2": "权益", "P3": "心理", "P4": "技术", "P5": "通用",
    })
    sensitivity_filters: List[str] = field(default_factory=list)
    governance_required: bool = True
    governance_skip_domains: List[str] = field(default_factory=list)


# ── Scheduling ──────────────────────────────────────────

@dataclass
class ScheduleSlot:
    day_of_week: int = -1
    time_window: TimeWindow = TimeWindow.ALL_DAY
    max_requests: int = 100
    cooldown_seconds: int = 1

@dataclass
class SchedulingConfig:
    slots: list[ScheduleSlot] = field(default_factory=lambda: [ScheduleSlot()])
    rate_limit: int = 60
    max_tokens_per_minute: int = 100000


# ── Routing ─────────────────────────────────────────────

@dataclass
class RoutingConfig:
    preferred_experts: List[str] = field(default_factory=list)
    expert_overrides: Dict[str, str] = field(default_factory=dict)
    bypass_experts: List[str] = field(default_factory=list)
    default_expert: str = "通用助手"


# ── Serialization helpers ────────────────────────────────

def _todict(obj) -> dict:
    """recursive dataclass → dict"""
    import dataclasses
    if dataclasses.is_dataclass(obj):
        return {k: _todict(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, list):
        return [_todict(i) for i in obj]
    return obj

def _fromdict(cls, data: dict):
    """dict → dataclass (handles nested + enum)"""
    import dataclasses
    if not data:
        return cls()
    field_types = {f.name: f.type for f in dataclasses.fields(cls)}
    kwargs = {}
    for k, v in data.items():
        if k not in field_types:
            continue
        ft = field_types[k]
        origin = getattr(ft, "__origin__", None)
        args = getattr(ft, "__args__", [])
        if origin is list and args:
            elem_type = args[0]
            if isinstance(elem_type, str):
                try:
                    elem_type = eval(elem_type)
                except: pass
            if dataclasses.is_dataclass(elem_type):
                kwargs[k] = [_fromdict(elem_type, item) for item in (v or []) if isinstance(item, dict)]
            else:
                kwargs[k] = v or []
        elif origin is dict:
            kwargs[k] = v or {}
        elif dataclasses.is_dataclass(ft):
            kwargs[k] = _fromdict(ft, v) if isinstance(v, dict) else ft()
        else:
            ft_resolved = ft
            if isinstance(ft_resolved, str):
                try:
                    ft_resolved = eval(ft_resolved)
                except: pass
            if isinstance(ft_resolved, type) and issubclass(ft_resolved, Enum):
                try:
                    kwargs[k] = ft_resolved(v) if v is not None else ft_resolved()
                except (ValueError, TypeError):
                    kwargs[k] = ft_resolved()
            else:
                kwargs[k] = v
    return cls(**kwargs)

def _resolve_enums(obj):
    """walk a reconstructed dataclass; ensure enum fields are enum, not str"""
    import dataclasses
    if not dataclasses.is_dataclass(obj):
        return
    for f in dataclasses.fields(obj):
        val = getattr(obj, f.name)
        ft = f.type
        if isinstance(ft, type) and issubclass(ft, Enum) and isinstance(val, str):
            try:
                setattr(obj, f.name, ft(val))
            except (ValueError, TypeError):
                pass
        if dataclasses.is_dataclass(ft):
            _resolve_enums(val)


# ── Full Profile ────────────────────────────────────────

@dataclass
class AssistantProfile:
    identity: Identity = field(default_factory=Identity)
    preferences: Preferences = field(default_factory=Preferences)
    behavior: list[BehaviorRule] = field(default_factory=list)
    knowledge: KnowledgeProfile = field(default_factory=KnowledgeProfile)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    scheduling: SchedulingConfig = field(default_factory=SchedulingConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)

    def to_dict(self) -> dict:
        return _todict(self)

    @classmethod
    def from_dict(cls, data: dict) -> AssistantProfile:
        p = _fromdict(cls, data)
        _resolve_enums(p)
        return p

    def merge(self, overlay: AssistantProfile) -> AssistantProfile:
        import copy, dataclasses
        merged = copy.deepcopy(self)
        o = overlay
        if o.identity.user_id: merged.identity = copy.deepcopy(o.identity)
        if o.preferences.tone != Tone.NORMAL: merged.preferences = copy.deepcopy(o.preferences)
        if o.behavior: merged.behavior = copy.deepcopy(o.behavior)
        if o.knowledge.domains: merged.knowledge = copy.deepcopy(o.knowledge)
        if o.memory.max_session_history != 100: merged.memory = copy.deepcopy(o.memory)
        if o.safety.governance_required: merged.safety = copy.deepcopy(o.safety)
        if o.routing.preferred_experts: merged.routing = copy.deepcopy(o.routing)
        return merged
