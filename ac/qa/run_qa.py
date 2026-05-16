#!/usr/bin/env python3
# AC · Q 层实测运行器
# 运行全部清洗管线测试 → 产出 s_5 分值

import json
import sys
import time
import traceback
import types
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ac.qa.config import QA_CONFIG, S5_TARGET
from ac.qa.pipeline.cleaner import clean, is_valid_length
from ac.qa.pipeline.deduplicator import MinHash, SimHash, deduplicate_docs
from ac.qa.pipeline.language_filter import detect_language, is_target_language

REPORT = {
    "timestamp": None,
    "s5_raw": 0,
    "s5_normalized": 0,
    "target": S5_TARGET,
    "modules": {},
    "tests": {"total": 0, "passed": 0, "failed": 0, "details": []},
    "coverage": {"cleaner": False, "deduplicator": False, "language": False, "quality": False, "pipeline": False},
}


def load_tests():
    test_dir = Path(__file__).parent / "tests"
    tests = {}
    for tf in sorted(test_dir.glob("test_*.py")):
        try:
            mod = types.ModuleType(tf.stem)
            code = compile(tf.read_text("utf-8"), tf.name, "exec")
            exec(code, mod.__dict__)
            funcs = [getattr(mod, n) for n in dir(mod) if n.startswith("test_") and callable(getattr(mod, n))]
            tests[tf.stem] = funcs
        except Exception as e:
            print(f"  [FAIL] 加载 {tf.name}: {e}")
            traceback.print_exc()
    return tests


def run_tests():
    tests = load_tests()
    total, passed, failed = 0, 0, 0
    details = []
    for module_name, funcs in tests.items():
        for func in funcs:
            total += 1
            try:
                func()
                passed += 1
                details.append({"test": f"{module_name}.{func.__name__}", "status": "PASS"})
            except AssertionError as e:
                failed += 1
                details.append({"test": f"{module_name}.{func.__name__}", "status": "FAIL", "msg": str(e)})
            except Exception as e:
                failed += 1
                details.append({"test": f"{module_name}.{func.__name__}", "status": "ERROR", "msg": f"{type(e).__name__}: {e}"})

    REPORT["tests"]["total"] = total
    REPORT["tests"]["passed"] = passed
    REPORT["tests"]["failed"] = failed
    REPORT["tests"]["details"] = details
    print(f"\n  {total} 总用例, {passed} 通过, {failed} 失败")
    return passed / max(total, 1)


def run_coverage_check():
    modules = {
        "cleaner": ["clean", "strip_html", "normalize_unicode", "collapse_whitespace", "is_valid_length"],
        "deduplicator": ["MinHash", "SimHash", "deduplicate_docs"],
        "language": ["detect_language", "is_target_language"],
        "quality": ["compute_perplexity", "is_quality_text"],
        "pipeline": ["test_pipeline"],
    }

    from ac.qa.pipeline import cleaner, deduplicator, language_filter, quality_filter

    module_map = {
        "cleaner": cleaner,
        "deduplicator": deduplicator,
        "language": language_filter,
        "quality": quality_filter,
    }

    covered = {}
    for mod_key, mod in module_map.items():
        funcs = modules[mod_key]
        results = {}
        for fname in funcs:
            results[fname] = hasattr(mod, fname)
        covered[mod_key] = results
        REPORT["coverage"][mod_key] = all(results.values())

    REPORT["coverage"]["pipeline"] = (
        REPORT["coverage"]["cleaner"]
        and REPORT["coverage"]["deduplicator"]
        and REPORT["coverage"]["language"]
        and REPORT["coverage"]["quality"]
    )

    print("\n  模块覆盖:")
    for mod, ok in REPORT["coverage"].items():
        status = "[OK]" if ok else "[..]"
        print(f"    {status} {mod}")

    n_covered = sum(1 for v in REPORT["coverage"].values() if v)
    return n_covered / max(len(REPORT["coverage"]), 1)


def run_precision_probe():
    try:
        texts = [
            "今天天气真好，适合出去散步。",
            "    <p>带HTML的文本</p>   ",
            "The English text should be filtered.",
            "重复的文本。重复的文本。",
            "正常的中文文本内容。",
        ]
        cleaned = [clean(t) for t in texts]
        deduped = deduplicate_docs([c for c in cleaned if c])

        zh_count = sum(1 for c in cleaned if is_target_language(c, "zh")[0])
        en_count = sum(1 for c in cleaned if is_target_language(c, "zh")[0] is False and len(c) > 0)
        valid_count = sum(1 for c in cleaned if is_valid_length(c))

        score = 0.0
        score += 0.3 if zh_count >= 2 else 0.15 if zh_count >= 1 else 0.0
        score += 0.3 if valid_count >= 4 else 0.15 if valid_count >= 2 else 0.0
        score += 0.2 if len(deduped) < len(texts) and len(deduped) > 0 else 0.1
        score += 0.2 if any("HTML" not in c for c in cleaned) else 0.0
        REPORT["modules"]["precision_probe"] = {"score": round(score, 2), "zh": zh_count, "valid": valid_count, "deduped": len(deduped), "original": len(texts)}
        return score
    except Exception as e:
        REPORT["modules"]["precision_probe"] = {"error": str(e)}
        return 0.0


def run_speed_benchmark():
    try:
        texts = ["测试短文本。"] * 10
        start = time.perf_counter()
        for t in texts:
            _ = clean(t)
        clean_time = time.perf_counter() - start

        start = time.perf_counter()
        _ = deduplicate_docs(texts)
        dedup_time = time.perf_counter() - start

        score = 1.0
        if clean_time > 0.5:
            score -= 0.2
        if dedup_time > 1.0:
            score -= 0.2
        score = max(score, 0.0)
        REPORT["modules"]["speed"] = {"clean_sec": round(clean_time, 4), "dedup_sec": round(dedup_time, 4), "score": round(score, 2)}
        return score
    except Exception as e:
        REPORT["modules"]["speed"] = {"error": str(e)}
        return 0.0


def compute_s5(test_pass_rate, coverage_rate, precision, speed):
    w = QA_CONFIG["scoring"]
    raw = (
        w["test_pass_weight"] * test_pass_rate
        + w["coverage_weight"] * coverage_rate
        + w["precision_weight"] * precision
        + w["speed_weight"] * speed
    )
    normalized = min(raw * S5_TARGET, S5_TARGET)
    return round(raw, 4), round(normalized, 2)


def main():
    REPORT["timestamp"] = datetime.now(timezone.utc).isoformat()
    print("=" * 54)
    print("  AC · 质量层 · 实测 (s_5) 运行器")
    print("  Q = (VERSION, METRICS, tests)")
    print("=" * 54)
    print(f"\n  清洗管线版本: cleaner(+dedup+lang+ppl)")
    print(f"  s_5 目标: {S5_TARGET}/100")

    print("\n--- 阶段 1: 单元测试 ---")
    test_pass_rate = run_tests()

    print("\n--- 阶段 2: 模块覆盖 ---")
    coverage_rate = run_coverage_check()

    print("\n--- 阶段 3: 精度探测 ---")
    precision = run_precision_probe()
    REPORT["modules"]["precision_probe"]["score"] = precision
    print(f"  精度分数: {precision:.2f}")

    print("\n--- 阶段 4: 性能基准 ---")
    speed = run_speed_benchmark()
    print(f"  性能分数: {speed:.2f}")

    raw, normalized = compute_s5(test_pass_rate, coverage_rate, precision, speed)
    REPORT["s5_raw"] = raw
    REPORT["s5_normalized"] = normalized

    print(f"\n{'=' * 54}")
    print(f"  s_5 原始分:   {raw:.4f}")
    print(f"  s_5 归一化分: {normalized:.2f}/{S5_TARGET}")
    print(f"  达成率:       {normalized / S5_TARGET * 100:.1f}%")
    print(f"{'=' * 54}")

    report_path = Path(__file__).parent / "last_run.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(REPORT, f, ensure_ascii=False, indent=2)
    print(f"\n  报告已保存: {report_path}")

    return normalized


if __name__ == "__main__":
    main()
