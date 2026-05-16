"""Personal Assistant — 颗粒配置加载"""
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Optional

from .schemas import AssistantProfile, Preferences, Tone, ResponseLength, Format, Identity, DomainConfig, ExpertiseLevel, RoutingConfig


CONFIG_DIR = Path(__file__).resolve().parent / "configs"


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def list_configs() -> list[str]:
    ensure_config_dir()
    return sorted([f.stem for f in CONFIG_DIR.glob("*.json")])


def load_config(name: str) -> Optional[AssistantProfile]:
    path = CONFIG_DIR / f"{name}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _dict_to_profile(data)


def save_config(name: str, profile: AssistantProfile):
    ensure_config_dir()
    path = CONFIG_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_profile_to_dict(profile), f, ensure_ascii=False, indent=2)


def _profile_to_dict(p: AssistantProfile) -> dict:
    return p.to_dict()


def _dict_to_profile(d: dict) -> AssistantProfile:
    return AssistantProfile.from_dict(d)
