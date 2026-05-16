"""多模型调度器 — AC 指挥所有 AI 节点的核心"""
import json
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelTarget:
    provider: str
    model: str


class AIRouter:
    PROVIDERS = {
        "deepseek/V3": {
            "base": "https://api.deepseek.com/v1",
            "key": "{API_KEY}",
            "model": "deepseek-chat",
        },
        "deepseek/R1": {
            "base": "https://api.deepseek.com/v1",
            "key": "{API_KEY}",
            "model": "deepseek-reasoner",
        },
        "qwen/turbo": {
            "base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "key": "{API_KEY}",
            "model": "qwen-turbo",
        },
        "qwen/plus": {
            "base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "key": "{API_KEY}",
            "model": "qwen-plus",
        },
        "qwen/max": {
            "base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "key": "{API_KEY}",
            "model": "qwen-max",
        },
    }

    ROUTING_TABLE = [
        ({"intent": "CODE", "zh": False},       "deepseek/V3"),
        ({"intent": "CODE", "zh": True},         "qwen/plus"),
        ({"intent": "REASON", "complex": True},  "deepseek/R1"),
        ({"intent": "DOC",   "tokens": (0, 4096)},  "qwen/turbo"),
        ({"intent": "DOC",   "tokens": (4096, 64000)}, "qwen/plus"),
        ({"intent": "DOC",   "tokens": (64000, 999999)}, "qwen/turbo"),
        ({"intent": "LEGAL"},                    "qwen/max"),
        ({"intent": "MEDICAL", "precision": True}, "qwen/max"),
        ({"intent": "MEDICAL"},                  "qwen/plus"),
        ({"intent": "CHAT"},                     "qwen/turbo"),
    ]

    def classify(self, text: str) -> dict:
        zh_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        zh_ratio = zh_chars / max(len(text), 1)
        return {
            "intent": self._detect_intent(text),
            "zh": zh_ratio > 0.3,
            "tokens": len(text) // 2,
            "complex": any(kw in text for kw in ["算法", "推理", "证明", "优化", "分析原因"]),
            "precision": any(kw in text for kw in ["诊断", "处方", "法律", "合同", "合规"]),
        }

    def _detect_intent(self, text: str) -> str:
        code_kw = ["def ", "class ", "import ", "function", "代码", "bug", "写一个", "实现"]
        legal_kw = ["法律", "合规", "诉讼", "合同", "法规", "仲裁", "DRG", "推诿"]
        medical_kw = ["诊断", "症状", "用药", "处方", "手术", "疾病", "白血病", "感染"]
        reason_kw = ["为什么", "原因", "分析", "推理", "方案对比", "最优"]

        score = {"CODE": 0, "LEGAL": 0, "MEDICAL": 0, "REASON": 0}
        for kw in code_kw:
            if kw in text:
                score["CODE"] += 1
        for kw in legal_kw:
            if kw in text:
                score["LEGAL"] += 1
        for kw in medical_kw:
            if kw in text:
                score["MEDICAL"] += 1
        for kw in reason_kw:
            if kw in text:
                score["REASON"] += 1

        best = max(score, key=score.get)
        return best if score[best] > 0 else "CHAT"

    def route(self, text: str) -> str:
        ctx = self.classify(text)
        for conditions, target in self.ROUTING_TABLE:
            if self._match(ctx, conditions):
                return target
        return "qwen/turbo"

    def _match(self, ctx: dict, cond: dict) -> bool:
        for k, v in cond.items():
            if k == "tokens":
                lo, hi = v
                if not (lo <= ctx["tokens"] <= hi):
                    return False
            elif ctx.get(k) != v:
                return False
        return True

    def call(self, target: str, messages: list, stream: bool = False) -> str:
        cfg = self.PROVIDERS[target]
        body = {
            "model": cfg["model"],
            "messages": messages,
            "stream": stream,
            "max_tokens": 4096,
            "temperature": 0.3 if target == "qwen/max" else 0.7,
        }
        req = urllib.request.Request(
            f"{cfg['base']}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {cfg['key']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        elapsed = int((time.time() - t0) * 1000)
        content = data["choices"][0]["message"]["content"]
        self._log(target, messages, content, elapsed)
        return content

    def _log(self, target, messages, output, latency_ms):
        print(f"[AC] {target} | {len(messages)} msgs | {latency_ms}ms | {len(output)} chars")

    def dispatch(self, user_input: str) -> str:
        target = self.route(user_input)
        print(f"[AC] intent={self.classify(user_input)['intent']} → routed to {target}")
        return self.call(target, [{"role": "user", "content": user_input}])
