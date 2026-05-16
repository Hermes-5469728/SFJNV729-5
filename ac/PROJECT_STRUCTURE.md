# AC 项目目录宪法 · 文心/Trae 必须遵守

## 核心规则

### 禁止向 `ac/` 目录放入以下文件：
- 前端文件（HTML/CSS/JS）→ 只能放 `site/`
- 测试文件（test_*.py）→ 只能放 `tests/`
- 文档文件（*.md）→ 只能放 `00-AC/docs/`
- 交接文件（handoff）→ 只能放 `00-AC/handoffs/`
- 证据文件（evidence）→ 只能放 `00-AC/evidence/`
- 用户配置（用户契约/Jarvis记忆）→ 只能放 `users/`
- 数据库文件（*.db）→ 只能放项目根目录

### `ac/` 目录只允许放：
- Python 模块（*.py）且必须是 AC 核心逻辑
- 适配器（adapters/）
- 治理管道（governance/）
- Jarvis 核心（jarvis_*.py）
- 架构守护（archguard.py, cloud_guard.py 等）

### 例外（白名单）：
- `PROJECT_STRUCTURE.md` — 本宪法文件本身
- `README.md` — 项目说明（如有）
- `__init__.py` — Python 包标识
