"""
双实例温差推理引擎
用 temperature=0 和 temperature=0.7 各跑一次
结果一致 → 高可信，不一致 → 标记冲突
"""

import os
import json
import re
import hashlib
import requests
from datetime import datetime
from typing import Dict, Optional


class DualInference:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY 环境变量未设置")
        self.endpoint = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"
        self.history = []

    def infer(self, prompt: str, system_prompt: str = "") -> Dict:
        """执行双实例推理，返回一致性结果"""
        cold = self._call(prompt, system_prompt, temperature=0.0)
        warm = self._call(prompt, system_prompt, temperature=0.7)
        consistency = self._analyze(cold, warm)

        return {
            "cold": cold,
            "warm": warm,
            "consistent": consistency["consistent"],
            "conflict_type": consistency["conflict_type"],
            "details": consistency["details"],
            "cold_hash": hashlib.sha256(cold.encode()).hexdigest()[:16],
            "warm_hash": hashlib.sha256(warm.encode()).hexdigest()[:16],
            "timestamp": datetime.now().isoformat()
        }

    def _call(self, prompt, system_prompt, temperature):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        resp = requests.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 1024
            },
            timeout=60
        )
        if resp.status_code != 200:
            raise RuntimeError(f"API调用失败: {resp.status_code} {resp.text}")
        return resp.json()["choices"][0]["message"]["content"]

    def _analyze(self, cold: str, warm: str) -> Dict:
        """比较两个输出的一致性"""
        cold_nums = set(re.findall(r'\d+\.?\d*', cold))
        warm_nums = set(re.findall(r'\d+\.?\d*', warm))
        if cold_nums != warm_nums:
            return {"consistent": False, "conflict_type": "number_mismatch",
                    "details": f"数字不一致: cold={cold_nums-warm_nums}, warm={warm_nums-cold_nums}"}
        if len(cold) > 0 and len(warm) > 0:
            length_ratio = abs(len(cold) - len(warm)) / max(len(cold), len(warm))
            if length_ratio > 0.5:
                return {"consistent": False, "conflict_type": "structural",
                        "details": f"长度差异过大: {length_ratio:.2f}"}
        return {"consistent": True, "conflict_type": "none", "details": "完全一致"}


_dual = None

def get_dual() -> DualInference:
    global _dual
    if _dual is None:
        _dual = DualInference()
    return _dual
