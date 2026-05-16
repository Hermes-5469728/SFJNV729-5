# 单一源码架构 - 消除双份代码

> **时间：** 2026-05-14
> **问题：** `ac\` 和 `HERMES-DATE\` 两套代码并存，靠人工拷贝维持一致
> **风险：** P0 级不同步，已导致生产风险

---

## 问题分析

```
当前状态：
HERMES-DATE\HERMES-DATE\   ← 主工作目录
  ├── ac_bus.py
  ├── unified_dispatcher.py
  ├── main.py
  ├── projects/
  └── 00-AC/

C:\ac\                      ← 独立代码仓库
  ├── governance/
  ├── qa/
  ├── core.py
  ├── orchestrator.py
  └── cli.py

问题：
1. 两套代码并存，靠人工拷贝同步
2. 任何更新需要手动在两个地方维护
3. 不同步导致生产环境运行旧代码
4. 无法追踪哪个是"正确"的源码
```

---

## 解决方案

### 方案：单一源码仓库 + 构建产物

```
源码位置（唯一）：
HERMES-DATE\HERMES-DATE\   ← 唯一的源码目录
  ├── src/                 ← 所有源码
  │   ├── core/
  │   ├── governance/
  │   ├── qa/
  │   ├── modules/
  │   └── ...
  ├── .github/             ← CI/CD 配置
  └── pyproject.toml       ← 构建配置

构建产物（生成）：
dist/                      ← 构建产物（不提交到源码）
  ├── ac_platform.whl
  └── ac_platform.tar.gz

运行目录（部署）：
/opt/ac/                   ← 服务器运行目录
  └── 从 dist/ 安装
```

---

## 实施步骤

### Phase 1: 源码合并（立即）

**目标：** 将所有源码合并到一个目录

```bash
# 1. 识别所有源码位置
find . -name "*.py" -o -name "*.rs" | grep -v __pycache__ | grep -v .git

# 2. 合并到 src/
mkdir -p src/core src/governance src/qa src/modules

# 3. 移动文件
mv ac/governance/* src/governance/
mv ac/qa/* src/qa/
mv ac/core.py src/core/
mv ac/orchestrator.py src/orchestrator/

# 4. 删除 ac\ 目录的源码（或保留为备份后删除）
```

### Phase 2: CI 一致性检查（立即）

**目标：** 在 CI 中加入 diff 检查，防止不同步

```yaml
# .github/workflows/ci.yml
jobs:
  source-sync-check:
    name: 源码一致性检查
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: 检查重复目录
        run: |
          # 禁止存在独立源码目录
          if [ -d "ac" ]; then
            echo "错误: 存在独立 ac\ 目录，必须合并到 src/"
            exit 1
          fi

      - name: Diff check
        run: |
          git status --short
          CHANGES=$(git status --short)
          if [ -n "$CHANGES" ]; then
            echo "发现未提交的变更"
            exit 1
          fi
```

### Phase 3: 构建产物分离（CI 实现）

**目标：** 源码和构建产物完全分离

```yaml
# CI 中构建
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Build
        run: |
          pip install build
          python -m build

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
```

---

## 文件结构（合并后）

```
HERMES-DATE\HERMES-DATE\
├── src\                      # 唯一源码目录
│   ├── core\                 # 核心模块
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── db.py
│   │   └── ...
│   ├── governance\           # 治理管道
│   │   ├── __init__.py
│   │   ├── checker.py
│   │   ├── hallucination_auditor.py
│   │   └── ...
│   ├── qa\                   # QA 管道
│   │   ├── __init__.py
│   │   ├── pipeline\
│   │   └── ...
│   ├── modules\              # 业务模块
│   │   ├── medical\
│   │   └── personal\
│   ├── orchestrator.py      # 编排器
│   ├── cli.py               # CLI
│   └── main.py               # 入口
├── .github\                  # CI/CD
│   └── workflows\
│       ├── ci.yml
│       └── cd.yml
├── pyproject.toml            # 项目配置
└── dist\                     # 构建产物（生成，不提交）
    ├── ac_platform-*.whl
    └── ac_platform-*.tar.gz
```

---

## CI 检查清单

在 CI 中必须检查：

- [x] **禁止独立源码目录** - 如果存在 `ac\` 等独立目录，CI 失败
- [x] **Diff 检查** - 如果有未提交的变更，CI 失败
- [x] **构建测试** - 确保源码可以成功构建
- [ ] **运行测试** - 确保构建产物可以正常运行
- [ ] **集成测试** - 确保各模块可以正确协作

---

## 回滚计划

如果合并后出现问题：

```bash
# 1. 从 git 回滚
git revert <commit>

# 2. 恢复备份
cp -r backup/ac ./ac

# 3. 分析问题
git log --oneline -10
git diff <last-good-commit>
```

---

## 收益

| 收益 | 说明 |
|------|------|
| **单一真相源** | 只有一个源码位置，不存在"哪个是正确的"问题 |
| **自动同步** | CI 检查确保源码一致性，无需人工拷贝 |
| **快速定位** | 问题定位只需在一个代码库中搜索 |
| **一致构建** | 构建产物从同一源码生成，版本一致 |

---

## 下一步

1. **立即执行 Phase 1** - 合并源码到 `src/`
2. **提交 CI 修改** - 包含一致性检查
3. **验证 CI 通过** - 确保没有破坏性变更
4. **删除 `ac\` 目录** - 确认新结构正常工作后

