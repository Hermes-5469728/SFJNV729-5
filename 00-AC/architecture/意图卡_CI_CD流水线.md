# 意图卡 · CI/CD 流水线

## 模块名
`pipeline` — 自动化测试→ArchGuard→交付 三阶段门禁

## 目标
每次代码变更自动触发：全量测试套件 → ArchGuard 全项扫描 → 交付/回滚判定。消除"测试全手动、部署靠记忆"的现状。

## 背景
- **宪法规则**: 宪法铁律第 1 条 — 代码生成不可信，AI 生成的代码默认标记为待审，必须经 ArchGuard 全量扫描 PASS 后才能提交
- **猎鬼发现**: 架构审计 (2026-05-13) 第 10 项 — CI/CD 完全缺失。测试和部署全手动执行，每次 AI 代写代码后无自动验证，依赖人工记忆跑 `run_tests.py`。历史上多次出现 AI 生成代码未经测试即被提交
- **为什么需要**: 当前已有 `run_tests.py` (5 关测试) 和 `archguard.py` (7 项扫描)，但两者均为手动触发。需要一个编排层将它们串联为自动化门禁

## 输入
| 参数 | 类型 | 说明 |
|------|------|------|
| `trigger` | `str` | 触发方式: `pre-commit` / `manual` / `scheduled` |
| `changed_files` | `list[str]` | 变更文件列表 (pre-commit 模式下由 git hook 提供) |
| `skip_archguard` | `bool` | 紧急热修复时跳过扫描 (需记录原因到 audit log) |

## 输出
```python
{
    "pipeline_id": str,          # 流水线唯一 ID
    "status": str,               # passed / failed / aborted
    "stages": {
        "tests": {
            "passed": bool,      # 全部 5 关 PASS?
            "results": dict,     # 每关的 pass/fail + 耗时
        },
        "archguard": {
            "passed": bool,      # 7/7 全 PASS?
            "failed_items": list,  # 失败项列表 (含详情)
        },
        "deliver": {
            "action": str,       # commit / rollback / hold
            "reason": str,       # 判定依据
        },
    },
    "duration_ms": int,          # 总耗时
    "evidence_path": str,        # 审计报告归档路径
}
```

## 关键约束
1. **失败即阻断** — 任何一关测试 FAIL 或任一 ArchGuard 项 FAIL → 流水线整体 FAIL → 阻止 commit/deploy
2. **不可跳过测试** — `skip_archguard` 只能跳 ArchGuard，不能跳测试。热修复也必须跑测试
3. **归档不可销毁** — 每次流水线结果写入 `00-AC/evidence/pipeline_runs/{pipeline_id}/`
4. **必须对接 git hook** — pre-commit 模式下通过 `.git/hooks/pre-commit` 触发
5. **必须对接 `governance_events`** — 流水线启动/完成/失败均写入 `governance_events` 表
6. **超时熔断** — 单阶段超过 300 秒自动 abort，防止死循环

## 已知难点
1. **Windows 兼容性** — git hooks 在 Windows 上需要特殊处理（bash vs PowerShell）。当前开发环境为 Windows，需同时支持两种脚本
2. **ArchGuard 扫描耗时** — 全量扫描约 10-15 秒（含子进程启动），高频 commit 时可能阻塞开发者。需要增量扫描模式（仅扫描变更相关模块）
3. **跨 AI 会话状态丢失** — 流水线在对话结束时被杀死。需要后台进程或计划任务触发 scheduled 模式
4. **无容器/沙箱** — 测试和 ArchGuard 在当前环境中直接运行，可能受到环境差异影响。缺少隔离的 CI 环境

## 参考文件
- `run_tests.py` — 5 关测试编排 (已实现)
- `archguard.py:full_scan()` — 7 项扫描 (已实现)
- `tests/test_sql_hijack.py` — 第 5 关测试 (已实现)
- `archive_audit.py:audit()` — 归档审计范例 (已实现)
