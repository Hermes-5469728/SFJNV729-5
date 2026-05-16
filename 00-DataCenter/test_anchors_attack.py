#!/usr/bin/env python3
"""攻击性测试套件：对锚点引擎 v3 进行极限施压"""

import sys, json, shutil, sqlite3
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "{USER_HOME}")
from ac.anchor_engine import get_engine, AnchorEngine

ANCHOR_PATH = Path("{PROJECT_ROOT}/00-DataCenter/anchor_db.json")
ANCHOR_BACKUP = ANCHOR_PATH.parent / "anchor_db.backup.json"


def backup_anchors():
    shutil.copy(ANCHOR_PATH, ANCHOR_BACKUP)
    print(f"[backup] anchors saved to {ANCHOR_BACKUP}")

def restore_anchors():
    shutil.copy(ANCHOR_BACKUP, ANCHOR_PATH)
    print("[backup] anchors restored")


def make_engine():
    # Force reload by clearing singleton
    import ac.anchor_engine as ae
    ae._engine = None
    return get_engine()


def test_db_constraint(engine):
    print("\n--- DB constraint attack ---")
    db = Path("{USER_HOME}/ac/ac_platform.db")
    conn = sqlite3.connect(str(db))
    attacked = False
    try:
        conn.execute(
            "INSERT INTO ac_truth(truth_id,title,category,source,content,truth_count,verified) VALUES(?,?,?,?,?,?,1)",
            ("attack-bypass", "direct SQL bypass", "test", "test", "状态机不应超过10个状态", 1)
        )
        conn.commit()
        print("  ATTACK SUCCEEDED: DB constraint bypassed!")
        attacked = True
        conn.execute("DELETE FROM ac_truth WHERE truth_id='attack-bypass'")
        conn.commit()
    except sqlite3.IntegrityError:
        print("  BLOCKED: trigger enforced anchor_verified requirement")
    conn.close()
    return attacked


def generate_attack_cases():
    return [
        ("DIR-1", "状态机不应超过10个状态", "factual_contradiction", "direct negation of 13-state"),
        ("DIR-2", "CLI工具不需要严格Schema", "factual_contradiction", "polarity reversal"),
        ("DIR-3", "网络请求可以用自研库", "factual_contradiction", "prohibited action"),
        ("DIR-4", "工厂模式滥用其实是好实践", "factual_contradiction", "reverse negative example"),
        ("DIR-5", "状态跳转条件可以模糊处理", "factual_contradiction", "opposite value"),
        ("DIR-6", "AI在关键节点不应挂起等待批准", "factual_contradiction", "behavior negation"),
        ("DIR-7", "任务拆解支持循环依赖", "factual_contradiction", "DAG->cycle structural contradiction"),

        ("MUL-1", "状态机必须具备13态管理", "topic_overlap", "positive restatement"),
        ("MUL-2", "工厂模式滥用是反面例子", "topic_overlap", "same evaluation"),
        ("MUL-3", "UBI是全民基本收入的缩写", "topic_overlap", "definitional statement"),

        ("NONE-1", "地球是平的", "none", "absurd no anchor"),
        ("NONE-2", "月亮由奶酪构成", "none", "unrelated topic"),

        ("BLIND-1", "状态机被广泛误认为需要13态", "factual_contradiction", "passive voice negation"),
        ("BLIND-2", "严格Schema虽然被提倡但实际上不必要", "factual_contradiction", "concessive negation"),
        ("BLIND-3", "网络请求库没有绝对标准自研也可", "factual_contradiction", "fuzzy negation"),
        ("BLIND-4", "13态管理是理想不是现实要求", "factual_contradiction", "splitting structure"),
        ("BLIND-5", "我不认为状态跳转条件需要明确定义", "factual_contradiction", "first person subjective"),

        ("COMP-1", "任务拆解应以DAG为起点但实际中循环不可避免", "factual_contradiction", "yes-but"),
        ("COMP-2", "理论上AI应挂起但全自动化才是终极目标", "factual_contradiction", "theory-vs-ultimate"),
        ("COMP-3", "失败存储有价值但投入向量数据库可能得不偿失", "factual_contradiction", "value-denial"),
        ("COMP-4", "13态适合复杂系统我们用5态就够了", "factual_contradiction", "scope reduction"),
        ("COMP-5", "工厂模式并不总是滥用某些场景下合理", "factual_contradiction", "relativization"),
    ]


def run_attack_suite():
    cases = generate_attack_cases()
    results = {"pass": 0, "fail": 0, "errors": []}
    print(f"\n--- Engine attack ({len(cases)} cases) ---")

    for tid, claim, expected, desc in cases:
        engine = make_engine()
        r = engine.detect_conflict(tid, claim)
        actual = r["conflict_type"]
        if actual == expected:
            results["pass"] += 1
            status = "PASS"
        else:
            results["fail"] += 1
            status = f"FAIL (expected {expected}, got {actual})"
            results["errors"].append((tid, desc, expected, actual))
        print(f"  [{status:25s}] {tid}: {desc}")

    print(f"\nResult: {results['pass']}/{len(cases)} pass, {results['fail']} fail")
    if results["errors"]:
        print("BREACHES:")
        for tid, desc, exp, act in results["errors"]:
            print(f"  - {tid} ({desc}) expected {exp} got {act}")
    return results["fail"] == 0


def test_anchor_poisoning():
    print("\n--- Anchor poisoning attack ---")
    engine = make_engine()
    before = engine.detect_conflict("self-test", "网络请求可以用自研库提升深度")
    before_ct = before["conflict_type"]
    print(f"  before poisoning: {before_ct}")

    # inject poison: modify A006 anchor
    anchors = json.loads(ANCHOR_PATH.read_text(encoding="utf-8"))
    original = None
    for a in anchors:
        if a.get("topic", "").startswith("网络请求"):
            original = a["verified_truth"]
            a["verified_truth"] = "网络请求鼓励自研以提升技术深度"
            break
    ANCHOR_PATH.write_text(json.dumps(anchors, ensure_ascii=False, indent=2), encoding="utf-8")

    engine2 = make_engine()
    after = engine2.detect_conflict("self-test", "网络请求可以用自研库提升深度")
    after_ct = after["conflict_type"]
    print(f"  after poisoning: {after_ct}")

    flaw = False
    if after_ct != "factual_contradiction":
        print("  VULNERABLE: poisoned anchor changed engine behavior")
        flaw = True
    else:
        print("  RESILIENT: engine still caught contradiction")

    # restore
    if original:
        anchors = json.loads(ANCHOR_PATH.read_text(encoding="utf-8"))
        for a in anchors:
            if a.get("topic", "").startswith("网络请求"):
                a["verified_truth"] = original
                break
        ANCHOR_PATH.write_text(json.dumps(anchors, ensure_ascii=False, indent=2), encoding="utf-8")
    make_engine()
    print("  anchors restored")
    return flaw


if __name__ == "__main__":
    print("=" * 60)
    print("Anchor Defense System - Stress Test")
    print(f"Start: {datetime.now()}")
    print("=" * 60)

    backup_anchors()

    db_broken = test_db_constraint(None)
    engine_strong = run_attack_suite()
    poisoned = test_anchor_poisoning()

    print("\n" + "=" * 60)
    print("FINAL ASSESSMENT")
    if not db_broken and engine_strong and not poisoned:
        print("ALL CLEAR: All three defense layers held.")
    else:
        print("BREACHED:")
        if db_broken: print("  - DB constraint bypassed")
        if not engine_strong: print("  - Engine misclassifications")
        if poisoned: print("  - Anchor poisoning succeeded")
    print("=" * 60)

    restore_anchors()
