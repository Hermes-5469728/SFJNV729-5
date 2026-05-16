"""
AC Platform · 固化测试套件
运行所有三关测试，验证系统核心功能完整。
"""

import sys, subprocess, time, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TESTS = [
    ("第一关：幻觉审计闭环", ROOT / "tests" / "test_hallucination_audit.py"),
    ("第二关：事实锚点引擎激活", ROOT / "tests" / "test_anchor_engine.py"),
    ("第三关：分类提取兜底", ROOT / "tests" / "test_classifier_fallback.py"),
    ("心脏起搏：双实例推理+契约验证", ROOT / "tests" / "test_heartbeat.py"),
    ("第四关：SQL 语义守卫熔断", ROOT / "tests" / "test_sql_hijack.py"),
]

pass_count = 0
fail_count = 0

print("=" * 60)
print("AC Platform · 固化测试套件")
print(f"运行时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
print()

for name, path in TESTS:
    if not path.exists():
        print(f"[SKIP] {name}")
        print(f"       文件不存在: {path}")
        print()
        continue

    print(f"▶ {name}")
    print(f"  {path.name}")
    start = time.time()

    result = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True, text=True, cwd=str(ROOT),
        encoding='utf-8', errors='replace',
        env={**dict(os.environ), "PYTHONPATH": str(ROOT.parent)}
    )

    elapsed = time.time() - start
    output = result.stdout + result.stderr
    passed = ("PASS]" in output or "pass]" in output)

    if passed:
        pass_count += 1
        print(f"  [PASS] ({elapsed:.1f}s)")
    else:
        fail_count += 1
        print(f"  [FAIL] ({elapsed:.1f}s)")
        for line in output.split('\n'):
            ls = line.strip()
            if any(kw in ls for kw in ['FAIL]', 'Error', 'assert', 'Exception', 'Traceback']):
                print(f"     {ls[:120]}")
    print()

print("=" * 60)
print(f"Result: {pass_count} passed / {fail_count} failed / {len(TESTS)} total")
if fail_count == 0:
    print("All tests passed. System core functions solidified.")
else:
    print(f"{fail_count} test(s) failed, need fixes.")
print("=" * 60)
