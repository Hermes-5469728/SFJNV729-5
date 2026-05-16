"""Personal Assistant — 个人定制化助手模块 · 绝对颗粒度

8 维度颗粒度：
  identity    — 用户身份（ID/别名/角色/组/租户）
  preferences — 偏好（语气/长度/格式/语言/温度/详细度）
  behavior    — 行为（触发规则/响应模板/降级策略/升级）
  knowledge   — 知识（领域/专业度/来源黑白名单）
  memory      — 记忆（会话/长期/衰减/向量）
  safety      — 安全（优先级映射/敏感过滤/治理要求）
  scheduling  — 调度（时间窗口/频率限制/冷却）
  routing     — 路由（偏好专家/覆盖/旁路）

使用方式:
  from assistant import create_assistant, AssistantOrchestrator

  pa = create_assistant("user_001")
  pa.update_profile(overlay_profile)
  pa.add_rule(my_rule)

  orb = AssistantOrchestrator()
  result = orb.process("帮我查一下", user_id="user_001")
"""
from __future__ import annotations

from .core import PersonalAssistant, AssistantOrchestrator
from .profile import ProfileStore, make_profile
from .rules import RuleEngine
from .memory import PersonalMemory
from .schemas import (
    AssistantProfile, Identity, Preferences,
    Tone, ResponseLength, Format, ExpertiseLevel,
    BehaviorRule, TriggerDef, TriggerMatch,
    DomainConfig, KnowledgeProfile, MemoryConfig,
    SafetyConfig, SchedulingConfig, RoutingConfig, Priority,
)
from .config import load_config, save_config, list_configs


def create_assistant(user_id: str = "", name: str = "", tone: Tone = Tone.CASUAL, db_path: str = "", expert_domains: List[str] | None = None) -> PersonalAssistant:
    """快速创建并初始化个人助手"""
    p = make_profile(user_id=user_id, name=name, tone=tone, expert_domains=expert_domains)
    pa = PersonalAssistant(user_id=user_id, db_path=db_path)
    pa.update_profile(p)
    return pa
