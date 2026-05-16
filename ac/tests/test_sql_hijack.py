"""
第四关 · SQL 语义守卫熔断测试
验证: 知识检索不会被云服务商隐式改写为向量/embedding 查询
原则: 任何声称"纯本地"的操作，必须通过 EXPLAIN QUERY PLAN 零远程调用验证
"""

import os
import sys
import json
import sqlite3
from pathlib import Path

AC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AC_DIR.parent))

from ac.knowledge_service import KnowledgeService, HIJACK_KEYWORDS

DB = AC_DIR / "ac_platform.db"

PASS = 0
FAIL = 0


def check(desc, ok):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {desc}")
    else:
        FAIL += 1
        print(f"  [FAIL] {desc}")


def test_hijack_keywords_list_exists():
    kws = HIJACK_KEYWORDS
    check("HIJACK_KEYWORDS 列表非空", len(kws) > 0)
    check("HIJACK_KEYWORDS 含 vector", "vector" in kws)
    check("HIJACK_KEYWORDS 含 embedding", "embedding" in kws)


def test_sql_plan_is_clean():
    ks = KnowledgeService()
    plan = ks._verify_sql_plan("布洛芬", "SELECT * FROM ac_truth WHERE content LIKE '%布洛芬%'")
    check("EXPLAIN QUERY PLAN 执行成功", "plan" in plan)
    check("执行计划不含劫持关键词", plan["clean"])
    if not plan["clean"]:
        print(f"     ! 检测到: {plan['hijacked_keywords']}")
        print(f"     ! 计划: {plan['plan'][:200]}")


def test_search_returns_results():
    ks = KnowledgeService()
    results = ks.search("布洛芬", sources=["truth"], top_k=3)
    check("search 返回 dict", isinstance(results, dict))
    check("search 含 sources 键", "sources" in results)
    truth_results = results.get("sources", {}).get("truth", [])
    check("truth 结果非 None", truth_results is not None)
    check("truth 结果是 list", isinstance(truth_results, list))


def test_truth_table_is_pure_like_scan():
    conn = sqlite3.connect(str(DB))
    plan_rows = conn.execute(
        "EXPLAIN QUERY PLAN SELECT * FROM ac_truth WHERE content LIKE '%test%' LIMIT 3"
    ).fetchall()
    conn.close()
    plan_str = str(plan_rows).lower()
    hijacked = [kw for kw in HIJACK_KEYWORDS if kw in plan_str]
    check("原始 ac_truth 查询不含劫持关键词", len(hijacked) == 0)
    if hijacked:
        print(f"     ! 劫持关键词: {hijacked}")


def test_search_no_network_hook():
    import socket
    original_socket = socket.socket
    call_count = [0]

    def fake_socket(*args, **kwargs):
        call_count[0] += 1
        return original_socket(*args, **kwargs)

    socket.socket = fake_socket
    try:
        ks = KnowledgeService()
        ks.search("测试查询", sources=["truth"], top_k=5)
    finally:
        socket.socket = original_socket
    check("_search_truth 不产生网络调用", call_count[0] == 0)


def test_fallback_scan_works():
    ks = KnowledgeService()
    results = ks._fallback_scan("布洛芬", top_k=3)
    check("fallback_scan 返回 list", isinstance(results, list))


def test_log_hijack_writes():
    ks = KnowledgeService()
    ks._log_hijack_attempt("test_query", "SCAN TABLE ac_truth USING VECTOR INDEX", ["vector"])
    conn = sqlite3.connect(str(DB))
    row = conn.execute(
        "SELECT * FROM ac_guard_log WHERE guard='sql_plan_guard' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    check("劫持记录已写入 ac_guard_log", row is not None)
    if row:
        detail = json.loads(row[3]) if row[3] else {}
        check("记录含 query 字段", "query" in detail)
        check("记录含 keywords 字段", "keywords" in detail)


if __name__ == "__main__":
    print("=" * 60)
    print("第四关：SQL 语义守卫 · 云端改写熔断测试")
    print(f"数据库: {DB}")
    print(f"关键词库: {HIJACK_KEYWORDS}")
    print("=" * 60)
    print()

    test_hijack_keywords_list_exists()
    test_sql_plan_is_clean()
    test_search_returns_results()
    test_truth_table_is_pure_like_scan()
    test_search_no_network_hook()
    test_fallback_scan_works()
    test_log_hijack_writes()

    print()
    print("=" * 60)
    print(f"Result: {PASS} passed / {FAIL} failed / {PASS + FAIL} total")
    if FAIL == 0:
        print("SQL 语义守卫生效。所有查询零远程调用。")
    else:
        print(f"{FAIL} 项失败，存在云端改写风险！")
    print("=" * 60)

    sys.exit(0 if FAIL == 0 else 1)
