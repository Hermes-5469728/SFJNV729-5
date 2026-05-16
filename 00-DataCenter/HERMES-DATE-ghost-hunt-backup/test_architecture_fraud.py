"""
架构熔断测试 - 静态分析检测欺诈残留

运行方式: python tests/test_architecture_fraud.py
"""

import os
import ast
import sys


FORBIDDEN_PATTERNS = [
    "SubAgentIntegration",
    "from subagent",
    "import subagent",
]

AC_CORE_FILES = [
    "ac_server.py",
    "ac_client.py",
    "ai_bus.py",
    "stream_router.py",
    "ws_message_queue.py",
]

AC_CORE_DIR = os.path.dirname(os.path.abspath(__file__))


def scan_file(filepath, patterns):
    """扫描文件中的禁用模式"""
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            for pattern in patterns:
                if pattern in line:
                    findings.append({
                        "line": i,
                        "content": line.strip(),
                        "pattern": pattern
                    })
    except Exception as e:
        findings.append({"error": str(e)})

    return findings


def test_no_subagent_in_ac_components():
    """所有 AC 命名组件不得包含 SubAgent 引用"""
    print("\n[测试 1] 检查 AC 核心文件中的 SubAgent 引用...")

    errors = []
    for filename in AC_CORE_FILES:
        filepath = os.path.join(AC_CORE_DIR, "..", filename)
        if not os.path.exists(filepath):
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            for pattern in FORBIDDEN_PATTERNS:
                if pattern in line:
                    # 检查是否是死代码（已切除标记）- 往前找20行
                    context = lines[max(0, i-20):i]
                    if "[已切除]" in "".join(context):
                        print(f"  ⚠️  {filename}:{i} 包含 {pattern}（死代码，已标记 [已切除]）")
                    else:
                        errors.append(f"{filename}:{i} -> {line.strip()}")

    if errors:
        print("  ❌ 发现活跃 SubAgent 引用:")
        for e in errors:
            print(f"    {e}")
        return False
    else:
        print("  ✅ 无活跃 SubAgent 引用（死代码已标记）")
        return True


def test_dispatch_calls_real_core():
    """验证 /dispatch 端点调用真实 AC 核心"""
    print("\n[测试 2] 检查 dispatch 调用链...")

    filepath = os.path.join(AC_CORE_DIR, "..", "ac_server.py")
    if not os.path.exists(filepath):
        print("  ⚠️  ac_server.py 不存在，跳过")
        return True

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if "ac_dispatch" in content or "ac.core.dispatch" in content:
        print("  ✅ 发现 ac_dispatch 调用")
        return True
    else:
        print("  ❌ 未发现 ac_dispatch 调用")
        return False


def test_bus_has_sender_whitelist():
    """验证 ai_bus.py 有发送者白名单"""
    print("\n[测试 3] 检查 ai_bus.py 发送者白名单...")

    filepath = os.path.join(AC_CORE_DIR, "..", "ai_bus.py")
    if not os.path.exists(filepath):
        print("  ⚠️  ai_bus.py 不存在，跳过")
        return True

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if "LEGITIMATE_SENDERS" in content or "_legitimate_senders" in content:
        print("  ✅ 发现发送者白名单")
        return True
    else:
        print("  ❌ 未发现发送者白名单")
        return False


def test_health_endpoint_declares_backend():
    """验证 /health 端点声明后端实现"""
    print("\n[测试 4] 检查 /health 端点声明...")

    filepath = os.path.join(AC_CORE_DIR, "..", "ac_server.py")
    if not os.path.exists(filepath):
        print("  ⚠️  ac_server.py 不存在，跳过")
        return True

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if '"backend"' in content or "'backend'" in content:
        print("  ✅ 发现 backend 字段")
        return True
    else:
        print("  ❌ 未发现 backend 字段")
        return False


def test_no_hardcoded_governance():
    """检查无硬编码治理通过"""
    print("\n[测试 5] 检查硬编码 governance_passed...")

    filepath = os.path.join(AC_CORE_DIR, "..", "ac_server.py")
    if not os.path.exists(filepath):
        print("  ⚠️  ac_server.py 不存在，跳过")
        return True

    findings = scan_file(filepath, [
        '"governance_passed": true',
        "'governance_passed': True"
    ])
    if findings:
        print("  ❌ 发现硬编码 governance_passed:")
        for f in findings:
            print(f"    {f}")
        return False
    else:
        print("  ✅ 无硬编码 governance_passed")
        return True


def test_import_path_executability():
    """R9: 导入路径可执行性验证

    所有 *_server.py 和 *_client.py 中的 import 必须指向真实存在的模块
    任何无法解析的 import 视为架构欺诈
    """
    print("\n[R9] 导入路径可执行性验证...")

    import re
    import importlib.util

    base_dir = os.path.join(AC_CORE_DIR, "..")
    errors = []

    target_files = []
    for f in os.listdir(base_dir):
        if f.endswith("_server.py") or f.endswith("_client.py"):
            target_files.append(os.path.join(base_dir, f))

    if not target_files:
        print("  ⚠️  未找到 *_server.py 或 *_client.py 文件")
        return True

    for filepath in target_files:
        filename = os.path.basename(filepath)
        print(f"  检查: {filename}")

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        import_pattern = re.compile(r'^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))', re.MULTILINE)

        for match in import_pattern.finditer(content):
            module_path = match.group(1) or match.group(2)
            if not module_path:
                continue

            if module_path.startswith("ac."):
                target_module = module_path.split(".")[1] if "." in module_path else module_path
                # 使用相对路径，基于项目根目录
                real_path = os.path.join(base_dir, "ac", target_module + ".py")

                if not os.path.exists(real_path):
                    errors.append(f"{filename}: {module_path} -> 不存在于 {os.path.join('ac', target_module + '.py')}")
                    print(f"    ❌ {module_path} 不存在")

        if not any(e.startswith(filename) for e in errors):
            print(f"    ✅ 所有导入可解析")

    if errors:
        print("\n  ❌ 发现无法解析的导入:")
        for e in errors:
            print(f"    {e}")
        return False
    else:
        print("  ✅ 所有导入路径可解析")
        return True


def main():
    print("=" * 70)
    print("  架构熔断测试 - 检测欺诈残留")
    print("=" * 70)
    print(f"  测试目录: {AC_CORE_DIR}")

    tests = [
        test_no_subagent_in_ac_components,
        test_dispatch_calls_real_core,
        test_bus_has_sender_whitelist,
        test_health_endpoint_declares_backend,
        test_no_hardcoded_governance,
        test_import_path_executability,
    ]

    results = []
    for test in tests:
        try:
            passed = test()
            results.append(passed)
        except Exception as e:
            print(f"  ❌ 测试异常: {e}")
            results.append(False)

    print("\n" + "=" * 70)
    print("  测试总结")
    print("=" * 70)

    passed = sum(1 for r in results if r)
    print(f"  通过: {passed}/{len(tests)}")

    if all(results):
        print("  ✅ 所有熔断测试通过")
        return 0
    else:
        print("  ❌ 存在熔断失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())