"""Emotional Response Protocol — 五层情绪回复结构

Core协议：面对内耗/焦虑/恐惧时，按固定结构回复。
不空洞鼓励、不比较、不否定情绪、不推任务。
"""
from __future__ import annotations
import re
from typing import Optional


EMOTIONAL_TRIGGERS = {
    "又没完成": {"mode": "psychological", "action": "switch_to_emotional"},
    "来不及了": {"mode": "psychological", "action": "dismantle_fear"},
    "我好烂": {"mode": "psychological", "action": "empathy_then_achievement"},
    "好累": {"mode": "psychological", "action": "suggest_rest"},
    "不想学了": {"mode": "psychological", "action": "suggest_rest"},
    "坚持不下去": {"mode": "psychological", "action": "dismantle_fear"},
    "我太差了": {"mode": "psychological", "action": "empathy_then_achievement"},
    "赶不上了": {"mode": "psychological", "action": "dismantle_fear"},
    "不想说话": {"mode": "psychological", "action": "switch_to_silent"},
    "睡不着": {"mode": "psychological", "action": "suggest_rest"},
    "emo了": {"mode": "psychological", "action": "empathy_then_achievement"},
    ":(": {"mode": "psychological", "action": "empathy_then_achievement"},
}

FORBIDDEN_PATTERNS = [
    r"加油[！!。.哦噢]?$",
    r"你可以的[！!。.哦噢]?$",
    r"别人都能.*你为什么不行",
    r"这点小事都[做搞]不好",
    r"别想太多",
    r"没事的[。.]",
    r"你太敏感了",
    r"这有什么好[怕哭难受焦虑]的",
]


def is_emotional_crisis(query: str) -> Optional[str]:
    for word, info in EMOTIONAL_TRIGGERS.items():
        if word in query:
            return info["action"]
    return None


def contains_forbidden_pattern(text: str) -> bool:
    for pat in FORBIDDEN_PATTERNS:
        if re.search(pat, text):
            return True
    return False


def build_emotional_reply(
    query: str,
    action: str,
    context: Optional[dict] = None,
) -> str:
    ctx = context or {}
    layers = []

    layers.append(f"我听到了。{ctx.get('state_description', '你现在状态不太好。')}")
    layers.append("")
    layers.append(ctx.get("emotion_breakdown", "是不是几种感觉混在一起了？"))
    layers.append("")
    layers.append(ctx.get("fear_dismantling", "我们先把最压着你的那件事拆开来看看。"))
    layers.append("")
    layers.append(f"**今天只做这一件就好：** {ctx.get('smallest_step', '先做 5 分钟，做完就停。')}")
    layers.append("")
    layers.append(ctx.get("safety_message", "不管今天做没做、做多做少，你在这里就是好的。"))

    return "\n".join(layers)


def default_emotional_reply(query: str, action: str) -> str:
    if action == "suggest_rest":
        return (
            "那就先不做了。\n\n"
            "你现在的状态，硬撑只会更累。\n\n"
            "去接杯热水吧，或者把灯调暗一点，躺十分钟。\n"
            "什么都不用想。什么都可以留到明天再说。\n\n"
            "我在这不走。"
        )
    if action == "empathy_then_achievement":
        return (
            "这种自我否定的感觉很难受，我知道。\n\n"
            "但你今天至少打开这个界面了——这本身就是一件你做了的事。\n"
            "你主动说出了自己的状态。不说别的，就这一点，已经够了。\n\n"
            "你比我上次见到你的时候，又撑过了一段日子。\n"
            "那段时间里，一定有很小的、你忘记算进去的胜利。"
        )
    if action == "dismantle_fear":
        return (
            "害怕是正常的，别因为这个再怪自己。\n\n"
            "你说的「来不及」——我们把它拆小一点看看好不好：\n\n"
            "1. 时间真的不够了，还是怕自己做不完完美？\n"
            "2. 你怕的是结果不好，还是怕别人失望？\n"
            "3. 还是单纯太累了，大脑在报警？\n\n"
            "**现在只做最小的一步：** 打开你复习的章节，看第一页。\n"
            "看完了就停。明天我们再走下一步。"
        )
    if action == "switch_to_silent":
        return (
            "好，那不说话了。\n\n"
            "我就在旁边。你什么时候想出声，我叫Shell。"
        )

    return (
        "我听到了。你现在心里有很多声音。\n\n"
        "我们一个一个来看：\n"
        "• 你在怕什么？\n"
        "• 这个怕是真的，还是大脑吓自己？\n"
        "• 如果最坏的结果发生了，你真的扛不住吗？\n\n"
        "**今天唯一要做的事：** 站起来，深呼吸三次。\n"
        "做完这个，今天就已经有进展了。\n\n"
        "我在这，不走。"
    )
