# 意图卡 · SubAgent 集成桥

## 模块名
`subagent_bridge` — AC Platform ↔ Task/SubAgent 体系的触发、监控、结果回传

## 目标
打通两套平行"大脑"：AC Platform 作为治理调度层，Task/SubAgent 作为执行层。AC 负责"该不该做、谁来做"，SubAgent 负责"怎么做"，结果回传后经治理管道二次审核。

## 背景
- **宪法规则**: 宪法铁律第 5 条 — AC 是只读审计者，不自动修改用户代码。但 SubAgent 需要执行写操作（创建文件、运行命令），AC 必须在执行前做权限预检、执行后做结果审计
- **猎鬼发现**: 架构审计 (2026-05-13) 第 7 项 — SubAgent 与 AC Platform 完全隔离。两套系统各自运行，无触发机制、无结果合并、无交叉验证。SubAgent 产出的代码直接绕过治理管道写入磁盘，AC 完全不知情
- **为什么需要**: 当前所有 AI 生成的代码都应在写入磁盘前经过治理管道。SubAgent 是执行层，AC 是治理层——两者天然互补，隔离反而是架构漏洞

## 输入
| 参数 | 类型 | 说明 |
|------|------|------|
| `task` | `dict` | SubAgent 任务描述 (action, target_file, parameters) |
| `agent_id` | `str` | 发起请求的 Agent 标识 |
| `session_id` | `str` | 会话上下文 ID |
| `requires_write` | `bool` | 是否需要写文件操作 (触发治理预检) |

## 输出
```python
{
    "bridge_id": str,            # 桥接事件唯一 ID
    "pre_check": {
        "allowed": bool,         # AC 权限预检: 允许执行?
        "risk_level": str,       # low / medium / high / blocked
        "checks": list[dict],    # 各项预检结果 (路径白名单/编码/注入)
    },
    "execution": {
        "agent_id": str,         # 执行的 SubAgent ID
        "status": str,           # dispatched / running / completed / failed
        "started_at": str,
        "completed_at": str,
    },
    "post_audit": {
        "passed": bool,          # 治理管道审核通过?
        "issues": list[str],     # 发现的问题
        "governance_id": str,    # 治理记录 ID (关联 governance_events)
    },
    "files_written": list[str],  # 实际写入的文件路径
    "files_blocked": list[str],  # 被预检拦截的文件路径
}
```

## 关键约束
1. **写操作必须经预检** — `requires_write=True` 时，AC 必须在 SubAgent 执行前验证: (a) 路径在白名单内 (b) 内容不含注入代码 (c) 编码正确
2. **结果必须回写 `governance_events`** — SubAgent 执行完成后，结果送治理管道二次审核，写入 `governance_events` (event_type=`subagent_exec` / `subagent_audit`)
3. **同时活跃 SubAgent ≤ 2** — 与 Worker 限制一致，防止并发写冲突
4. **文件路径必须在输出目录铁律范围内** — `site/`, `ac/`, 或 `Temp/opencode`。其他路径直接 blocked
5. **SubAgent 不能绕过 AC 写文件** — 如果检测到绕过（文件修改但无对应预检记录），视为架构欺诈，触发 ArchGuard 报警
6. **超时熔断** — SubAgent 执行超过 300 秒无响应，AC 发送 cancel 信号并标记为 failed

## 已知难点
1. **SubAgent 环境差异** — SubAgent 运行在独立进程中，文件系统、环境变量、Python 路径可能不同。预检通过的执行可能在实际环境中失败
2. **竞态条件** — 两个活跃 SubAgent 同时写同一文件时，AC 的预检无法预知。需要文件锁 (`resource_lock.py` 已有骨架)
3. **AC 自身不执行** — 根据宪法铁律第 5 条，AC 不能替 SubAgent 执行操作。但 SubAgent 失败时，AC 需要通知用户而非自动重试
4. **双向信任** — SubAgent 需要信任 AC 的预检结果不延迟执行，AC 需要信任 SubAgent 的完成报告真实。当前无加密签名或完整性校验
5. **Opencode 对话端的 Task 工具已有 SubAgent 调度能力** — 集成桥需要与现有 Task 工具共存而非替代，避免双份调度逻辑

## 参考文件
- `orchestrator.py` — 任务编排器（但当前不调 SubAgent）
- `subagent_integration.py` — 旧版集成骨架 (repo 根目录, 待迁移)
- `resource_lock.py` — 文件锁骨架 (repo 根目录, 待迁移)
- `governance/pipeline.py` — 治理管道 (二次审核入口)
- `jarvis_core.py:chat()` — 现有 Agent 调度模式参考
