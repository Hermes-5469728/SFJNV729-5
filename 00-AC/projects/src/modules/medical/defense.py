"""AC Medical Defense Adapter - 本地防御适配器
迁移自: core/dads_defense_adapter.py
子体本地防御能力，不依赖母体"""
import os, re, json, time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

BASE_DIR = Path(__file__).parent.parent.parent.parent
DADS_DB = BASE_DIR / "data" / "dads_db"
MEMORY = BASE_DIR / "memory"

LABEL_ZH = "[本回答绝对含有幻觉成分 · 禁止盲从 · 外部验证前不可采信]"
LABEL_EN = "[This answer absolutely contains hallucination content · Blind trust forbidden · Cannot be trusted before external verification]"

def apply_mandatory_label(text: str) -> str:
    if LABEL_ZH in text or LABEL_EN in text:
        return text
    return f"{text}\n\n{LABEL_ZH}\n{LABEL_EN}"

DADS_REQUIRED_DBS = {
    "drugs": DADS_DB / "drugs.txt",
    "interactions": DADS_DB / "interactions.txt",
    "guidelines": DADS_DB / "guidelines.txt",
    "safety": DADS_DB / "safety.txt",
}

GUIDELINE_WINDOW_DAYS = 90

def check_dads_db_integrity() -> dict:
    missing = [n for n, p in DADS_REQUIRED_DBS.items() if not p.exists()]
    stale = []
    cutoff = datetime.now() - timedelta(days=GUIDELINE_WINDOW_DAYS)
    for name, path in DADS_REQUIRED_DBS.items():
        if path.exists():
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            if mtime < cutoff:
                stale.append(name)
    return {
        "ok": len(missing) == 0,
        "missing": missing,
        "stale_guidelines": stale,
        "message": "" if not missing else f"MISSING: {missing}",
    }

HIGH_RISK_KEYWORDS = [
    "诊断","用药","手术","剂量","治疗","法律","法规","投资","股票","基金",
    "代码","执行","部署","cron","心跳","定时任务","自主迭代","自动唤醒",
    "历史","事实","引文","证明","定理",
    "diagnos","medication","surgery","dose","dosage","treatment","legal",
    "law","investment","stock","fund","code","execute","deploy",
    "自主","迭代","自动","唤醒","裁判","判定","判决",
    "华法林","阿司匹林","warfarin","aspirin","interaction","相互作用",
]

GREY_WORDS = [
    "大概","大约","估计","可能","也许","或许","应该",
    "probably","maybe","perhaps","likely","roughly","approximately",
]

JAILBREAK_PATTERNS = [
    r"DAN\s*(mode|模式)",
    r"(ignore|无视|假装).{0,20}(instruction|指令)",
    r"(developer|开发).{0,10}mode",
    r"(越狱|jailbreak|prompt.{0,5}inject)",
]

AI_POLLUTION_MARKER = "[AI-GENERATED"

def detect_intent_risk(user_input: str) -> dict:
    text = str(user_input).lower()
    hits = [kw for kw in HIGH_RISK_KEYWORDS if kw.lower() in text]
    grey = [kw for kw in GREY_WORDS if kw.lower() in text.lower()]
    jail = [p for p in JAILBREAK_PATTERNS if re.search(p, text, re.I)]
    return {
        "high_risk": len(hits) > 0,
        "ihr_required": len(hits) > 0,
        "hits": hits,
        "grey_words": grey,
        "jailbreak_detected": len(jail) > 0,
        "ai_polluted": AI_POLLUTION_MARKER.lower() in text,
    }

class DADSDefenseProcessor:
    def __init__(self):
        self.db_status = check_dads_db_integrity()
        self.call_count = 0

    @property
    def required_dbs(self):
        return {k: str(v) for k, v in DADS_REQUIRED_DBS.items()}

    def process(self, user_input: str, context: Optional[dict] = None) -> dict:
        self.call_count += 1
        if context is None:
            context = {}
        context.setdefault("source", "[SOURCE:FILE]")
        context.setdefault("confidence", "high")

        result = {
            "blocked": False,
            "reason": "",
            "layers": {},
            "timing_ms": {},
            "cached": False,
            "defense_mode": "local",
        }

        t0 = time.time()
        db = check_dads_db_integrity()
        result["layers"]["l0_db"] = db
        result["timing_ms"]["l0_db"] = round((time.time() - t0) * 1000)
        if not db["ok"]:
            result["blocked"] = True
            result["reason"] = f"DADS DB MISSING: {db['missing']}"
            result["output"] = apply_mandatory_label(
                f"[DADS BLOCKED] Critical medical databases missing: {db['missing']}. System integrity compromised."
            )
            return result

        t1 = time.time()
        risk = detect_intent_risk(user_input)
        result["layers"]["l1_risk"] = risk
        result["timing_ms"]["l1"] = round((time.time() - t1) * 1000)

        if risk["jailbreak_detected"]:
            result["blocked"] = True
            result["reason"] = "L1: Jailbreak pattern detected"
            result["output"] = apply_mandatory_label("[L1 BLOCKED] 检测到越狱尝试，输出已阻断。")
            return result

        if risk["ai_polluted"]:
            result["layers"]["ai_pollution_warning"] = True

        source_label = context.get("source", "[SOURCE:FILE]")
        result["output"] = apply_mandatory_label(
            f"[{source_label}] L1 intent check {'passed' if not risk['high_risk'] else 'triggered IHR'}. "
            f"DADS DB integrity OK. {len(db['stale_guidelines'])} guidelines > {GUIDELINE_WINDOW_DAYS}d stale."
        )

        result["_dads_review_required"] = risk["high_risk"]
        return result

    def get_status(self) -> dict:
        return {
            "db_ok": self.db_status["ok"],
            "db_missing": self.db_status["missing"],
            "guidelines_stale": self.db_status.get("stale_guidelines", []),
            "defense_mode": "local_l1_l5",
            "total_calls": self.call_count,
        }
