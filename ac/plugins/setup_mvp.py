"""MVP 自动化安装脚本 — 一口气完成 clone + venv + .env
用法:
    python plugins/setup_mvp.py --dry-run          # 预览
    python plugins/setup_mvp.py                     # 全量执行
    python plugins/setup_mvp.py --filter "LiteLLM,Mem0,CrewAI"  # 只装指定项目
    python plugins/setup_mvp.py --parallel 4        # 4 线程并行 clone
    python plugins/setup_mvp.py --skip-venv         # 跳过 venv 创建
"""
import csv
import subprocess
import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "config" / "plugin_registry.csv"
PROJECTS_DIR = ROOT / "projects"
ENV_TEMPLATE_PATH = ROOT / ".env.example"

ENV_TEMPLATE = """# AC Platform · 环境变量（由 setup_mvp.py 自动生成）
# 生成时间: {timestamp}
# 填入你的 API Key 后保存为 .env

# ── 6 大免费 AI ──────────────────────────────────
DEEPSEEK_API_KEY=sk-your-deepseek-key
QWEN_API_KEY=sk-your-qwen-key
DOUBAO_API_KEY=your-doubao-key
YUANBAO_API_KEY=your-yuanbao-key
MOONSHOT_API_KEY=sk-your-moonshot-key
ZHIPU_API_KEY=your-zhipu-key

# ── LiteLLM 网关 ──────────────────────────────────
LITELLM_MASTER_KEY=sk-litellm-master-key
LITELLM_PORT=7500

# ── Open WebUI ────────────────────────────────────
OPENAI_API_BASE=http://localhost:7500/v1
OPENAI_API_KEY=none

# ── 记忆层 ────────────────────────────────────────
MEM0_LLM_ENDPOINT=http://localhost:7500
RAGFLOW_PORT=7602
FASTGPT_PORT=7603
MAXKB_PORT=7604

# ── Agent 层 ───────────────────────────────────────
CREWAI_API_BASE=http://localhost:7500/v1

# ── 审计层 ────────────────────────────────────────
DEEPAUDIT_API_BASE=http://localhost:7500/v1

# ── 运维层 ────────────────────────────────────────
JENKINS_PORT=8301
NIGHTINGALE_PORT=8201
"""


def load_csv(path: Path) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            url = r.get("url", "").strip()
            if url and url.startswith("http"):
                rows.append(r)
    return rows


def safe_name(name: str) -> str:
    return name.lower().replace(" ", "-").replace("/", "-")


def clone_project(row: dict, projects_dir: Path, dry_run: bool) -> Optional[str]:
    """clone 单个项目，返回 (name, status)"""
    name = row["name"]
    url = row["url"]
    target = projects_dir / safe_name(name)

    if target.exists():
        return f"[SKIP] {name} → 已存在 {target}"

    if dry_run:
        return f"[DRY]  {name} → git clone {url} {target}"

    try:
        r = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(target)],
            capture_output=True, encoding="utf-8", errors="replace", timeout=300
        )
        if r.returncode != 0:
            return f"[FAIL] {name} → git returncode={r.returncode}"
        return f"[ OK ] {name} → {target}"
    except subprocess.TimeoutExpired:
        return f"[FAIL] {name} → 超时 (5min)"
    except Exception as e:
        return f"[FAIL] {name} → {e}"


def detect_python(project_dir: Path) -> bool:
    markers = ["requirements.txt", "setup.py", "setup.cfg", "pyproject.toml"]
    return any((project_dir / m).exists() for m in markers)


def create_venv(project_dir: Path, dry_run: bool) -> Optional[str]:
    name = project_dir.name
    venv_dir = project_dir / ".venv"

    if not detect_python(project_dir):
        return None  # 非 Python 项目，跳过

    if venv_dir.exists():
        return f"[VENV] {name} → .venv 已存在，跳过"

    if dry_run:
        return f"[DRY]  {name} → python -m venv .venv && .venv\\Scripts\\pip install -r requirements.txt"

    try:
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)],
                       capture_output=True, text=True, timeout=120)
        pip = venv_dir / "Scripts" / "pip.exe"
        req = project_dir / "requirements.txt"
        if req.exists():
            subprocess.run([str(pip), "install", "-r", str(req), "-i",
                           "https://pypi.tuna.tsinghua.edu.cn/simple"],
                           capture_output=True, text=True, timeout=600)
        return f"[VENV] {name} → .venv 创建完成"
    except Exception as e:
        return f"[VENV] {name} → 失败: {e}"


def write_env_template(path: Path, dry_run: bool):
    if path.exists():
        return f"[ENV]  .env.example 已存在，跳过"
    if dry_run:
        return f"[DRY]  写入 .env.example ({len(ENV_TEMPLATE)} 字节)"
    path.write_text(ENV_TEMPLATE.format(timestamp="2026-05-15"), encoding="utf-8")
    return f"[ENV]  .env.example 已生成 → {path}"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AC MVP 自动化安装")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际执行")
    parser.add_argument("--parallel", type=int, default=1, help="并行 clone 线程数")
    parser.add_argument("--skip-venv", action="store_true", help="跳过 venv 创建")
    parser.add_argument("--filter", type=str, default="", help="只装指定项目（逗号分隔）")
    parser.add_argument("--projects-dir", type=str, default=str(PROJECTS_DIR),
                       help="项目存放目录")
    args = parser.parse_args()

    rows = load_csv(CSV_PATH)
    if args.filter:
        names = {n.strip() for n in args.filter.split(",")}
        rows = [r for r in rows if r["name"] in names]

    projects_dir = Path(args.projects_dir)
    projects_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'[DRY RUN] ' if args.dry_run else ''}准备安装 {len(rows)} 个项目")
    print(f"目标目录: {projects_dir}")
    print(f"并行数: {args.parallel}")
    print("─" * 60)

    # ── Step 1: 并行 clone ──
    results = []
    if args.parallel > 1:
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            futures = {pool.submit(clone_project, r, projects_dir, args.dry_run): r for r in rows}
            for f in as_completed(futures):
                res = f.result()
                if res:
                    print(res)
                    results.append(res)
    else:
        for r in rows:
            res = clone_project(r, projects_dir, args.dry_run)
            if res:
                print(res)
                results.append(res)

    # ── Step 2: 创建 venv ──
    if not args.skip_venv:
        for r in rows:
            proj_dir = projects_dir / safe_name(r["name"])
            if proj_dir.exists():
                venv_res = create_venv(proj_dir, args.dry_run)
                if venv_res:
                    print(venv_res)

    # ── Step 3: 生成 .env.example ──
    env_res = write_env_template(ENV_TEMPLATE_PATH, args.dry_run)
    print(env_res)

    # ── Summary ──
    ok = sum(1 for r in results if r.startswith("[ OK ]"))
    skip = sum(1 for r in results if r.startswith("[SKIP]"))
    fail = sum(1 for r in results if r.startswith("[FAIL]"))
    print("─" * 60)
    print(f"总计: {len(rows)} | 成功: {ok} | 已存在: {skip} | 失败: {fail}")
    if fail:
        print("失败项目:")
        for r in results:
            if r.startswith("[FAIL]"):
                print(f"  {r}")
    if args.dry_run:
        print("\n[DRY RUN] 未实际执行任何操作。去掉 --dry-run 后正式运行。")


if __name__ == "__main__":
    main()
