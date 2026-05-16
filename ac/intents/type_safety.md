# 意图: 类型安全（mypy strict）

## 目标
为核心模块添加完整静态类型注解，集成 mypy strict 模式到 CI，在运行时之前拦截类型错误。

## 背景 · 当前缺失的后果
- Python 动态特性容易在运行时爆雷：类型不匹配、None 访问、字典键缺失
- 当前 mypy.ini 已存在但 `disallow_untyped_defs = False`，实际未强制
- pyproject.toml 虽然设置了 `strict = true`，但未被 CI 或 pre-commit 实际激活
- 多 AI 协作时，不同 AI 对同一函数的参数类型理解不一致，接口契约口头化

## 关键约束
1. **严格模式** — 启用 `disallow_untyped_defs`、`disallow_incomplete_defs`、`no_implicit_optional`
2. **忽略 any 类型** — 不允许 `Any` 逃逸到公共接口
3. **不阻塞现有功能** — 注解是增量添加的，不应改变运行时行为
4. **与 R3 对齐** — 导入路径必须真实可达，mypy 可验证

## 输入/输出
- **输入**: 核心 Python 模块（governance/、adapters/、jarvis_core.py、core.py、db.py）
- **输出**: 通过 mypy strict 检查的模块
- **接口**: mypy 配置（mypy.ini + pyproject.toml [tool.mypy]）

## 覆盖范围

### P0 优先（核心链路）
| 模块 | 文件 | 当前状态 |
|------|------|---------|
| 治理管道 | governance/checker.py | 部分注解 |
| 治理管道 | governance/syntax.py | 待注解 |
| 治理管道 | governance/semantic.py | 待注解 |
| 治理管道 | governance/security.py | 待注解 |
| 治理管道 | governance/corrector.py | 待注解 |
| 治理管道 | governance/hallucination_auditor.py | 待注解 |
| 适配器层 | adapters/base.py | 已有注解 |
| 适配器层 | adapters/registry.py | 待注解 |
| 适配器层 | adapters/router.py | 待注解 |
| 对话引擎 | jarvis_core.py | 部分注解 |
| 调度核心 | core.py | 无注解 |

### P1 扩展
| 模块 | 文件 |
|------|------|
| 数据库层 | db.py |
| 架构卫士 | archguard.py |
| 双实例推理 | dual_inference.py |
| 契约验证 | schema_contract.py |
| 锚点引擎 | anchor_engine.py |

## 已知难点
- [TODO] `ignore_missing_imports = True` 会导致第三方库的类型隐患被隐藏
- [TODO] `conn: object` 在 db.py 中需要改为 `sqlite3.Connection`（需解决循环导入）
- [OPT] SQLAlchemy Row 类型注解需要 `sqlite3.Row`
- [OPT] 动态构建的 dict（如 `matched_result`）缺少 TypedDict 定义

## 调研方向
- mypy 1.x strict mode 最佳实践
- `typing.Protocol` vs ABC 用于接口定义
- `TypeGuard` / `type narrowing` 用于运行时类型收窄
- `TypedDict` 用于治理管道上下文 dict

## 实施阶段
1. **Phase 1**: 为 P0 模块添加完整类型注解
2. **Phase 2**: 激活 mypy strict mode 并修复所有错误
3. **Phase 3**: 集成到 CI 流水线（Task 1 联动）
4. **Phase 4**: 为 P1 模块添加注解

## 当前状态
意图文档已生成。P0 模块注解进行中。
