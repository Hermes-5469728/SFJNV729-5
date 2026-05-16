"""项目五维评估器 — 基于 GitHub API 自动打分
用法:
    python plugins/evaluate_project.py --url "https://github.com/mem0ai/mem0"
    python plugins/evaluate_project.py --csv config/plugin_registry.csv --all
    python plugins/evaluate_project.py --csv config/plugin_registry.csv --top 15
输出:
    config/project_scores.csv (排序后，P0 优先)
"""
import csv
import json
import sys
import time
import urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "config" / "plugin_registry.csv"
OUT_PATH = ROOT / "config" / "project_scores.csv"
CACHE_PATH = ROOT / "config" / ".github_cache.json"

def load_cache():
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}

def save_cache(cache):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

def gh_api(repo: str, cache: dict) -> dict:
    """调 GitHub API 拿 stars / forks / last_commit / open_issues"""
    if repo in cache:
        return cache[repo]

    url = f"https://api.github.com/repos/{repo}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "ac-evaluator",
            "Accept": "application/vnd.github+json"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        cache[repo] = {
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "pushed_at": data.get("pushed_at", ""),
            "archived": data.get("archived", False),
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        cache[repo] = {"error": str(e), "stars": 0, "forks": 0, "open_issues": 0, "pushed_at": ""}
    return cache[repo]

def extract_repo(url: str) -> str:
    """https://github.com/owner/repo → owner/repo"""
    url = url.rstrip("/")
    parts = url.replace("https://github.com/", "").split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return ""

def score_activity(pushed_at: str) -> int:
    """最后 push 时间 → 0-10"""
    if not pushed_at:
        return 0
    try:
        dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
        days = (datetime.now(timezone.utc) - dt).days
        if days <= 30:   return 10
        if days <= 90:   return 8
        if days <= 180:  return 6
        if days <= 365:  return 4
        if days <= 730:  return 2
        return 1
    except:
        return 3

def score_difficulty(category: str) -> int:
    """基于类别预估安装难度: Docker 项目一般比纯 Python 难"""
    easy = {"gateway", "memory", "agent"}  # pip install 一把梭
    medium = {"knowledge", "llmops", "execution", "audit", "test", "security"}
    hard = {"frontend", "model", "cicd", "monitor", "pm", "medical"}
    if category in easy:   return 8
    if category in medium: return 5
    return 3

def score_resource(has_docker: bool, category: str) -> int:
    """预估资源占用"""
    heavy = {"model", "medical", "knowledge"}
    light = {"memory", "agent", "audit", "test", "ide", "execution", "gateway"}
    if category in heavy:  return 3
    if category in light:  return 8
    return 5

def score_strategic(row: dict) -> int:
    """战略契合度: active > standby, 核心层 > 辅助层"""
    core_layers = {"①模型层", "②记忆层", "③Agent层", "④执行层", "⑤审计层"}
    if row.get("status") == "active" and row.get("layer") in core_layers:
        return 10
    if row.get("status") == "active":
        return 8
    if row.get("layer") in core_layers:
        return 6
    if row.get("category") in ("medical",):
        return 4  # 专业领域，按需
    return 3

def score_uniqueness(row: dict, all_rows: list) -> int:
    """同 category 内只有一个项目 → 独特高分"""
    same_cat = [r for r in all_rows if r["category"] == row["category"]]
    if len(same_cat) == 1: return 10
    if len(same_cat) == 2: return 7
    return 4

def evaluate(row: dict, gh_data: dict, all_rows: list) -> dict:
    s_strategic = score_strategic(row)
    s_activity  = score_activity(gh_data.get("pushed_at", ""))
    s_difficulty = score_difficulty(row.get("category", ""))
    s_resource  = score_resource(True, row.get("category", ""))
    s_unique    = score_uniqueness(row, all_rows)

    total = s_strategic * 2 + s_activity + s_difficulty + s_resource + s_unique
    tier = "P0" if total >= 40 else ("P1" if total >= 30 else ("P2" if total >= 20 else "P3"))

    return {
        "name": row["name"],
        "url": row.get("url", ""),
        "category": row["category"],
        "layer": row["layer"],
        "status": row["status"],
        "stars": gh_data.get("stars", "?"),
        "pushed": gh_data.get("pushed_at", "")[:10],
        "strategic": s_strategic,
        "activity": s_activity,
        "difficulty": s_difficulty,
        "resource": s_resource,
        "uniqueness": s_unique,
        "total": total,
        "tier": tier,
        "archived": gh_data.get("archived", False)
    }

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--url", help="评估单个项目")
    p.add_argument("--csv", default=str(CSV_PATH), help="CSV 路径")
    p.add_argument("--all", action="store_true", help="评估所有项目")
    p.add_argument("--top", type=int, default=0, help="只显示前 N 个")
    args = p.parse_args()

    cache = load_cache()

    # 单项目模式
    if args.url:
        repo = extract_repo(args.url)
        if not repo:
            print("无效 URL"); return
        print(f"查询 {repo} ...")
        gh = gh_api(repo, cache)
        save_cache(cache)
        print(json.dumps(gh, indent=2, ensure_ascii=False))
        return

    # 批量模式
    rows = []
    with open(args.csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if not args.all and not args.top:
        print("请加 --all 或 --top N"); return

    results = []
    for i, r in enumerate(rows):
        url = r.get("url", "").strip()
        if not url:
            results.append(evaluate(r, {"stars": 0, "pushed_at": ""}, rows))
            continue

        repo = extract_repo(url)
        if not repo:
            results.append(evaluate(r, {"stars": 0, "pushed_at": ""}, rows))
            continue

        print(f"[{i+1}/{len(rows)}] {repo} ...", end=" ")
        gh = gh_api(repo, cache)
        print(f"★{gh.get('stars','?')}")
        results.append(evaluate(r, gh, rows))
        time.sleep(0.3)  # 避免触发 rate limit

    save_cache(cache)

    # 按总分排序
    results.sort(key=lambda x: x["total"], reverse=True)

    # 输出 CSV
    fields = ["tier", "name", "url", "category", "layer", "stars", "pushed",
              "total", "strategic", "activity", "difficulty", "resource", "uniqueness", "archived"]
    with open(OUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    # 终端摘要
    limit = args.top if args.top else len(results)
    print(f"\n{'═'*70}")
    print(f"{'排名':<4} {'等级':<4} {'分数':<5} {'★':<7} {'名称':<25} {'分类'}")
    print(f"{'─'*70}")
    for i, r in enumerate(results[:limit]):
        flag = "🗑️" if r.get("archived") else ""
        print(f"{i+1:<4} {r['tier']:<4} {r['total']:<5} {str(r.get('stars','?')):<7} {r['name']:<25} {r['category']} {flag}")

    p0 = sum(1 for r in results if r["tier"] == "P0")
    p1 = sum(1 for r in results if r["tier"] == "P1")
    p2 = sum(1 for r in results if r["tier"] == "P2")
    p3 = sum(1 for r in results if r["tier"] == "P3")
    print(f"{'─'*70}")
    print(f"P0 立刻装: {p0} | P1 本周装: {p1} | P2 注册 standby: {p2} | P3 可删除: {p3}")
    print(f"结果已保存: {OUT_PATH}")

if __name__ == "__main__":
    main()
