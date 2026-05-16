import sys
import os
from pathlib import Path
import importlib.util

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stdin.encoding != "utf-8":
    sys.stdin.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, str(ROOT / path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_dads_med = _load_module("dads_medical", "dads-medical/__init__.py")
_dads_personal = _load_module("dads_personal", "dads-personal/__init__.py")


def format_medical(result: dict) -> str:
    sev = _dads_med.MedicalDiagnosis.SEVERITY_MAP.get(result["severity"], {})
    emoji = sev.get("emoji", "[?]")
    label = sev.get("label", result["severity"])
    header = f"  {emoji}  诊断结果"
    severity_line = f"  严重程度: {emoji} {label}"
    try:
        "\n".join([header, severity_line]).encode("gbk")
    except UnicodeEncodeError:
        emoji = f"[{label[0]}]"
        header = f"  {emoji} 诊断结果"
        severity_line = f"  严重程度: {emoji} {label}"
    return "\n".join([
        "=" * 46, header, "=" * 46,
        f"  病名    : {result['disease']}",
        severity_line,
        f"  置信度  : {result['confidence']:.0%}",
        f"  建议    : {result['advice']}",
        "=" * 46, "",
        "  [本结果由 AI 辅助生成，仅供参考，不构成医疗建议]",
    ])


def format_protection(result: dict) -> str:
    sev = _dads_personal.DoctorRiskAgent.SEVERITY_MAP.get(result["severity"], {})
    label = sev.get("label", result["severity"])
    return "\n".join([
        "=" * 46,
        f"  [{label[0]}] 风险评估: {result.get('scenario', '')[:30]}",
        "=" * 46,
        f"  规则ID  : {result.get('rule_id', '-')}",
        f"  风险等级: [{label[0]}] {label}",
        f"  置信度  : {result['confidence']:.0%}",
        f"  建议    : {result['advice']}",
        "=" * 46, "",
        "  [本结果由 AI 辅助生成，仅供参考，不构成法律建议]",
    ])


def main():
    print("=" * 46)
    print("  DADS 智能工作台  v2.0")
    print("=" * 46)
    print("  [1] 医疗诊断  (dads-medical)")
    print("  [2] 职业防护  (dads-personal)")
    print()

    mode = input("请选择模式 (1/2): ").strip()
    if mode == "2":
        _run_personal()
    else:
        _run_medical()


def _run_medical():
    while True:
        symptoms = input("\n请输入患者症状: ").strip()
        if not symptoms:
            continue
        d = _dads_med.MedicalDiagnosis()
        r = d.diagnose(symptoms)
        print(format_medical(r))
        if input("\n继续? (y/n): ").strip().lower() in ("n", "no", "q"):
            break


def _run_personal():
    print("\n  三明医改背景下，帮医生保护自己")
    while True:
        desc = input("\n请描述工作场景: ").strip()
        if not desc:
            continue
        agent = _dads_personal.DoctorRiskAgent()
        r = agent.assess(desc)
        print(format_protection(r))
        if input("\n继续? (y/n): ").strip().lower() in ("n", "no", "q"):
            break


if __name__ == "__main__":
    main()
