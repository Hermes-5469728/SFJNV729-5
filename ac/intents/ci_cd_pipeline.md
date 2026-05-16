# 意图: CI/CD 自动交付流水线

## 目标
建立从 `git push` 到自动测试、自动扫描、自动部署的完整流水线，使系统在无人值守时也能自我验证。

## 背景 · 当前缺失的后果
- 测试、扫描、部署目前靠手动触发 `python run_tests.py` / `python archguard.py`
- 用户不在时系统无法自我验证，一次误提交可能进入生产环境而无人察觉
- R10 已规定 CI/CD 强制熔断（`test_sql_hijack.py`），但熔断机制本身无载体

## 关键约束
1. **所有步骤必须可重现** — 失败的构建必须能通过重新触发得到相同结果
2. **失败必须阻断部署** — 测试或扫描 FAIL 时，后续阶段不执行
3. **不依赖特定云服务** — 可在本地 GitHub Actions runner 或 GitHub-hosted runner 上运行
4. **与宪法铁律对齐** — 必须包含 ArchGuard 全量扫描 + SQL 执行计划劫持检测
5. **R10 强制熔断** — 任一检查失败，构建直接 FAIL

## 输入/输出
- **输入**: `git push` 到目标分支（`main` 或 `master`）
- **输出**: 流水线状态（PASS/FAIL）+ 各阶段日志 + ArchGuard 扫描报告
- **接口**:
  - GitHub Actions workflow 文件: `.github/workflows/ac-ci.yml`
  - 部署脚本: `scripts/deploy.sh` 或 uvicorn service 定义

## 流水线阶段

```
git push
  ├── Stage 1: 代码检查
  │   ├── ruff lint + format check
  │   └── mypy type check (strict)
  ├── Stage 2: 测试
  │   ├── pytest run_tests.py
  │   └── test_sql_hijack.py (R10 熔断)
  ├── Stage 3: 架构扫描
  │   ├── archguard full_scan
  │   └── cloud_guard scan
  └── Stage 4: 部署 (仅 main 分支)
      ├── 重启 AC Server (uvicorn)
      └── 健康检查
```

## 已知难点
- [TODO] 本地 Windows 环境 vs GitHub-hosted runner (Ubuntu) 路径差异
- [TODO] uvicorn 服务重启在 Windows 上的实现（需 Windows Service 或 Task Scheduler）
- [OPT] 部署阶段可增量：先只做测试+扫描，部署手动；后续再加自动部署
- [OPT] Docker 化可解决平台差异，但违反"不依赖特定云服务"约束（可本地 Docker）

## 调研方向
- GitHub Actions: `actions/setup-python`, `actions/checkout`
- Python CI 模板: `pytest`, `ruff`, `mypy` 在 CI 中的配置
- Windows runner: GitHub Actions 支持 `windows-latest`
- uvicorn 守护: `nssm` (Non-Sucking Service Manager) for Windows

## 实施阶段
1. **Phase 1**: 创建 `.github/workflows/ac-ci.yml`，包含代码检查 + 测试 + 架构扫描
2. **Phase 2**: 配置 Windows runner，解决路径兼容性
3. **Phase 3**: 添加部署阶段（自动重启 uvicorn）
4. **Phase 4**: 添加健康检查 + 部署失败自动通知

## 当前状态
仅生成意图文档。Phase 1 workflow 文件已就绪，待推送到 GitHub 后验证。
