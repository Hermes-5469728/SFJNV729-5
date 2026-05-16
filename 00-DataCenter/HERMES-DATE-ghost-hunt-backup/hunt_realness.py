"""
Hunt Realness — 动态契约验证
对比 CLI 输出 vs Server 端点输出
"""
import json, subprocess, sys, os

REPO = r"{PROJECT_ROOT}"
SERVER_URL = "http://127.0.0.1:8000"

QUERIES = [
    "焦虑",
    "Python性能优化",
    "数据库设计",
    "华法林相互作用",
]

def e(s):
    try:
        return s.encode("utf-8").decode("utf-8")
    except:
        return s

def call_cli(query):
    result = subprocess.run(
        [sys.executable, "cli.py", "dispatch", query, "--no-gov"],
        capture_output=True, text=True, timeout=30,
        cwd=REPO,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"}
    )
    for line in result.stdout.split("\n"):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {"error": "no JSON in stdout", "raw_stdout": result.stdout[:500]}

def call_endpoint(query):
    import requests
    try:
        r = requests.post(
            f"{SERVER_URL}/dispatch",
            json={"request": query},
            timeout=30,
        )
        data = r.json()
        # Server uses nested structure: status.success.data.result
        if data.get("status") == "success" and "data" in data:
            d = data["data"]
            return {
                "status": d.get("status"),
                "matched": (d.get("result") or {}).get("matched", []),
                "governance_passed": d.get("governance_passed"),
                "matched_experts": [m.get("name") for m in ((d.get("result") or {}).get("matched") or [])],
                "execution_time_ms": d.get("execution_time_ms"),
                "raw": data,
            }
        return {"error": "unexpected format", "raw": data}
    except Exception as ex:
        return {"error": str(ex)}

def verify():
    print("=" * 60)
    print("  全领域猎鬼 · 动态契约验证")
    print("=" * 60)
    all_pass = True

    for q in QUERIES:
        print(f"\n--- Query: {q} ---")
        cli = call_cli(q)
        srv = call_endpoint(q)

        cli_matched = cli.get("matched", [])
        if isinstance(cli_matched, list):
            cli_names = sorted([m.get("name", "") for m in cli_matched if isinstance(m, dict)])
        else:
            cli_names = []

        srv_matched = srv.get("matched_experts", [])
        if isinstance(srv_matched, list):
            srv_names = sorted(srv_matched)
        else:
            srv_names = []

        match = cli_names == srv_names

        print(f"  CLI matched:  {cli_names}")
        print(f"  Server matched: {srv_names}")
        print(f"  Governance passed (server): {srv.get('governance_passed')}")
        print(f"  Match: {'✅' if match else '❌'}")

        if not match:
            all_pass = False
            print(f"  CLI raw: {json.dumps(cli, ensure_ascii=False)[:200]}")
            print(f"  Server raw: {json.dumps(srv.get('raw', {}), ensure_ascii=False)[:200]}")

    print(f"\n{'=' * 60}")
    if all_pass:
        print("  ✅ 所有端点契约一致")
    else:
        print("  ❌ 存在契约不一致 — 鬼已确认")
    print(f"{'=' * 60}")
    return all_pass

if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
