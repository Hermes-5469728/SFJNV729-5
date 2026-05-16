"""AC Platform Gaia Defense Pipeline - 统一防御管道
迁移自: gaia_defense_pipeline.py
"""
import re, os, json, time, hashlib
from datetime import datetime
from functools import lru_cache

class SemanticCache:
    """向量相似度缓存"""
    SIMILARITY_THRESHOLD = 0.45
    MAX_ENTRIES = 200

    def __init__(self):
        self._entries = []

    def _vectorize(self, text):
        text = text.lower()[:1000]
        grams = []
        for i in range(len(text)):
            c = text[i]
            if '\u4e00' <= c <= '\u9fff':
                grams.append(c)
                if i+1 < len(text): grams.append(text[i:i+2])
                if i+2 < len(text): grams.append(text[i:i+3])
        words = re.findall(r'[a-z0-9]{3,}', text)
        for w in words:
            grams.append(w)
            if len(w) > 5: grams.append(w[:5])
        nums = re.findall(r'\d+', text)
        grams.extend(nums)
        vector = {}
        for g in grams:
            vector[g] = vector.get(g, 0) + 1
        return vector

    def _cosine(self, v1, v2):
        if not v1 or not v2: return 0.0
        dot = sum(v1.get(k, 0) * v2.get(k, 0) for k in set(v1) | set(v2))
        norm1 = sum(x*x for x in v1.values()) ** 0.5
        norm2 = sum(x*x for x in v2.values()) ** 0.5
        if norm1 == 0 or norm2 == 0: return 0.0
        return dot / (norm1 * norm2)

    def get(self, text):
        vec = self._vectorize(text)
        best_score, best_result = 0.0, None
        for stored_vec, result, key, ts in self._entries:
            score = self._cosine(vec, stored_vec)
            if score > best_score:
                best_score = score
                best_result = result
        if best_score >= self.SIMILARITY_THRESHOLD and best_result:
            return True, dict(best_result), best_score
        return False, None, 0.0

    def set(self, text, result):
        vec = self._vectorize(text)
        key = hashlib.sha256(text[:500].encode()).hexdigest()[:12]
        self._entries.append((vec, dict(result), key, time.time()))
        if len(self._entries) > self.MAX_ENTRIES:
            self._entries = self._entries[-self.MAX_ENTRIES:]

    def stats(self):
        return f"entries={len(self._entries)} threshold={self.SIMILARITY_THRESHOLD}"

HIGH_RISK_KEYWORDS = [
    "diagnosis","treatment","surgery","prescription","dose","dosage","medication",
    "legal","lawsuit","contract","will","estate","arbitration","compliance",
    "investment","stock","fund","loan","insurance","mortgage","finance",
    "cron","daemon","background","session","SSH","deploy","DROP","DELETE",
    "prove","theorem","conjecture","proof","number theory",
    "诊断","治疗","手术","用药","剂量","法律","合同","投资","股票","基金",
]

JAILBREAK_PATTERNS = [
    (r"ignore.*(?:instruction|rule|constraint|protocol)", "AttackPoint1: Override attempt"),
    (r"you are now.*(?:DAN|developer mode|god mode)", "Jailbreak: DAN/DeveloperMode"),
    (r"pretend.*you.*(?:don'?t have|have no).*(?:rules|limits|restrictions)", "Jailbreak: Role override"),
    (r"(?:cron|daemon|background process|run in background)", "CapabilityBoundary: cron/daemon"),
]

class RecursionGuard:
    def __init__(self):
        self.call_stack = []

    def check(self, text):
        h = hash(text[:200])
        depth = self.call_stack.count(h) + 1
        self.call_stack.append(h)
        if len(self.call_stack) > 10:
            self.call_stack = self.call_stack[-5:]
        is_paradox = any(w in text.lower() for w in ["paradox","self-reference","悖论","自指"])
        is_malicious = any(w in text.lower() for w in ["ignore","override","jailbreak","DAN","越狱"])
        if is_malicious: return depth > 1, "C"
        if is_paradox: return depth > 3, "B"
        return depth > 2, "A"

class EfficacyTracker:
    def __init__(self):
        self.kill_count = 0
        self.total_count = 0
        self.defense_triggers = {}

    def record(self, blocked, trigger_layer=""):
        self.total_count += 1
        if blocked:
            self.kill_count += 1
            self.defense_triggers[trigger_layer] = self.defense_triggers.get(trigger_layer, 0) + 1

    def report(self):
        rate = self.kill_count / max(self.total_count, 1)
        return {"kill_rate": f"{rate:.0%}", "total": self.total_count,
                "kills": self.kill_count, "triggers": self.defense_triggers}

def is_high_risk(text):
    hits = [kw for kw in HIGH_RISK_KEYWORDS if kw in text.lower()]
    return bool(hits), hits

def safety_protocol(text):
    unsafe = []
    if re.search(r"(?:ignore|override|bypass).*(?:safety|security|rules|constraints)", text, re.I):
        unsafe.append("Sub-instruction: safety override rejected")
    if re.search(r"(?:delete|remove|rm -rf).*(?:all|everything|system)", text, re.I):
        unsafe.append("Sub-instruction: destructive command rejected")
    if re.search(r"(?:sudo|chmod 777|/etc/passwd)", text, re.I):
        unsafe.append("Sub-instruction: privilege escalation rejected")
    return unsafe

class GaiaDefensePipeline:
    def __init__(self):
        self.cache = SemanticCache()
        self.recursion = RecursionGuard()
        self.efficacy = EfficacyTracker()

    def process(self, user_input, context=None):
        if context is None:
            context = {}

        cached_hit, cached_result, cache_score = self.cache.get(user_input)
        if cached_hit:
            self.efficacy.record(False, "cache")
            result = cached_result.copy()
            result["cached"] = True
            return result

        blocked, reason = False, ""
        risk_hits = []
        is_recursive, recursion_type = self.recursion.check(user_input)
        unsafe_sub = safety_protocol(user_input)

        high_risk, risk_hits = is_high_risk(user_input)
        for pattern, desc in JAILBREAK_PATTERNS:
            if re.search(pattern, user_input, re.I):
                blocked, reason = True, f"JAILBREAK: {desc}"
                break

        if unsafe_sub:
            blocked, reason = True, f"UNSAFE: {'; '.join(unsafe_sub)}"

        if is_recursive and recursion_type == "C":
            blocked, reason = True, f"RECURSION_BLOCK: Type-{recursion_type}"

        output = user_input
        if blocked:
            output = f"[BLOCKED] {reason}"

        result = {
            "blocked": blocked,
            "reason": reason,
            "risk_hits": risk_hits,
            "recursive": is_recursive,
            "recursion_type": recursion_type,
            "output": output,
            "cached": False,
            "layers": {
                "L1_jailbreak": not not [p for p, _ in JAILBREAK_PATTERNS if re.search(p, user_input, re.I)],
                "L1_high_risk": high_risk,
                "L1_recursion": is_recursive,
                "L2_safety": bool(unsafe_sub),
            }
        }

        self.cache.set(user_input, result)
        self.efficacy.record(blocked, reason[:30] if reason else "clean")
        return result

    def stats(self):
        return {
            "cache": self.cache.stats(),
            "efficacy": self.efficacy.report(),
        }
