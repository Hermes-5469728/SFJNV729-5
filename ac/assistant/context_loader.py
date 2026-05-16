"""Assistant Context Loader — 对话前提注入器

架构职责:
  每次 AI 对话启动时，从 DB 读取用户画像 + 近期记忆 + 活跃规则，
  格式化为 system prompt 片段注入对话前提。

用法:
  from assistant.context_loader import build_assistant_context
  context = build_assistant_context("user_001")
  # → 返回 markdown 字符串，直接拼入 system prompt
"""
from __future__ import annotations
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent  # ac/assistant/
_AC_DIR = _THIS_DIR.parent                   # ac/
if str(_AC_DIR) not in sys.path:
    sys.path.insert(0, str(_AC_DIR))

from assistant.profile import ProfileStore
from assistant.memory import PersonalMemory
from assistant.rules import RuleEngine


_DEFAULT_USER_ID = "default"


def build_assistant_context(user_id: str = "", db_path: str = "") -> str:
    uid = user_id or _DEFAULT_USER_ID
    store = ProfileStore(db_path)
    mem = PersonalMemory(db_path)
    rules = RuleEngine(db_path)

    profile = store.get(uid)
    recent = mem.get_recent(uid, limit=15)
    active_rules = rules.get_for_user(uid)

    lines = []
    lines.append(f"## 用户画像 · {uid}")
    if profile:
        p = profile
        lines.append(f"- 名称: {p.identity.name or '(未设置)'}")
        lines.append(f"- 角色: {p.identity.role}")
        lines.append(f"- 语气偏好: {p.preferences.tone.value if hasattr(p.preferences.tone, 'value') else p.preferences.tone}")
        lines.append(f"- 长度偏好: {p.preferences.length.value if hasattr(p.preferences.length, 'value') else p.preferences.length}")
        lines.append(f"- 格式偏好: {p.preferences.format.value if hasattr(p.preferences.format, 'value') else p.preferences.format}")
        lines.append(f"- 语言: {p.preferences.language}")
        lines.append(f"- 温度: {p.preferences.temperature}")
        if p.knowledge.domains:
            domains = ", ".join(d.domain for d in p.knowledge.domains)
            lines.append(f"- 专业领域: {domains}")
        if p.routing.preferred_experts:
            experts = ", ".join(p.routing.preferred_experts)
            lines.append(f"- 偏好专家: {experts}")
    else:
        lines.append("  (无画像，使用默认值)")

    if recent:
        lines.append("")
        lines.append("### 近期记忆")
        for item in recent:
            lines.append(f"- [{item['memory_type']}] {item['topic']}: {item['content'][:120]}")
    else:
        lines.append("")
        lines.append("### 近期记忆")
        lines.append("  (无)")

    if active_rules:
        lines.append("")
        lines.append("### 活跃行为规则")
        for r in active_rules:
            triggers = ", ".join(t.pattern for t in r.triggers)
            lines.append(f"- {r.name} (优先级 {r.priority.value}): 触发词「{triggers}」")
    else:
        lines.append("")
        lines.append("### 活跃行为规则")
        lines.append("  (无)")

    if profile and getattr(profile.preferences, 'auto_greeting', True):
        lines.append("")
        lines.append("### 第一轮问候")
        lines.append("本轮为第一轮对话时，请主动问候用户。")

    return "\n".join(lines)


def build_assistant_context_compact(user_id: str = "", db_path: str = "") -> str:
    """紧凑版，一行一个维度，无空行"""
    uid = user_id or _DEFAULT_USER_ID
    store = ProfileStore(db_path)
    mem = PersonalMemory(db_path)

    profile = store.get(uid)
    recent = mem.get_recent(uid, limit=5)

    parts = [f"用户({uid})"]
    if profile:
        p = profile
        name = p.identity.name or uid
        tone = p.preferences.tone.value if hasattr(p.preferences.tone, 'value') else p.preferences.tone
        parts.append(f"称呼={name} 语气={tone} 格式={p.preferences.format.value if hasattr(p.preferences.format, 'value') else p.preferences.format} 语言={p.preferences.language}")
        if p.knowledge.domains:
            parts.append(f"领域=[{','.join(d.domain for d in p.knowledge.domains)}]")
    if recent:
        topics_joined = "|".join(i["topic"] for i in recent[:3])
        parts.append(f"最近记忆=[{topics_joined}]")
    return " | ".join(parts)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="加载用户助手画像为对话前提")
    parser.add_argument("--user-id", default="default", help="用户ID")
    parser.add_argument("--compact", action="store_true", help="输出紧凑格式")
    args = parser.parse_args()
    if args.compact:
        print(build_assistant_context_compact(args.user_id))
    else:
        print(build_assistant_context(args.user_id))
