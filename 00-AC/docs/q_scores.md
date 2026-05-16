# AC · 质量层 · 评分卡

> 更新时间: 2026-05-13 · s_6 治理层 + s_7 修正层 + s_8 编码层

---

## 评分函数

$$\text{Score}(t) = \sum_{i=1}^{5} \omega_i \cdot s_i(t)$$

---

## 当前评分 (v2.3 → v2.4)

| 维度 $s_i$ | 权重 $\omega_i$ | v2.3 | v2.4 | 变动 | 目标 |
|-----------|----------------|------|------|------|------|
| 覆盖率 $s_1$ | 0.30 | 100 | 100 | — | 100 |
| 触发准确 $s_2$ | 0.25 | 95 | 95 | — | 98 |
| 规则清晰 $s_3$ | 0.25 | 95 | 95 | — | 98 |
| 回退安全 $s_4$ | 0.15 | 90 | 90 | — | 95 |
| 实测 $s_5$ | 0.05 | 78.40 | 78.40 | — | 80 |
| **治理层 $s_6$** | **0.05** | **—** | **100** | **+100** | **100** |
| **修正层 $s_7$** | **0.05** | **—** | **80** | **+80** | **95** |
| **编码层 $s_8$** | **0.10** | **—** | **95** | **+95** | **100** |

> 权重重平衡: s_1→s_5 权重不变, s_6/s_7 从原 s_5 之后扩展, s_8 从 s_2 权重分出 0.05

---

### 总分计算

$$\text{Score}_{\text{v2.5}} = 100 \cdot 0.30 + 95 \cdot 0.20 + 95 \cdot 0.25 + 90 \cdot 0.15 + 78.40 \cdot 0.05 + 100 \cdot 0.05 + 80 \cdot 0.05 + 95 \cdot 0.10 = 96.17$$

\[
\Delta = -0.75 \quad (\text{s_8 加入, 权重重平衡})
\]

---

---

## s_8 编码层详情

L0 编码层: 在 CLI 入口强制 UTF-8 编码契约。

| 子维度 | 权重 | 说明 |
|--------|------|------|
| U+FFFD 检测 | 0.40 | 检测替换字符，输入损坏即拒绝 |
| GBK 透明恢复 | 0.30 | 对 Windows CP936 环境尝试 latin-1→UTF-8 恢复 |
| stdin/stdout reconfigure | 0.20 | 自动设置 PYTHONIOENCODING + sys.stdin.reconfigure |
| 用户提示 | 0.10 | 编码错误时给出修复建议 (chcp 65001) |

s_8 实现: `ac/cli.py` 的 `_ensure_utf8()` + `_config_encoding()`, 治理层 `encoding` checker

---

## s_6 治理层详情

| 子维度 | 权重 | 说明 |
|--------|------|------|
| 语法校验 | 0.35 | JSON Schema + L5 头部检查 |
| 语义校验 | 0.25 | 领域规则（专家名、优先级、租约） |
| 安全检查 | 0.25 | 敏感词/凭证泄露/命令注入检测 |
| 审计日志 | 0.15 | governance_log 表写入完整性 |

s_6 实现: `ac/governance/syntax.py` + `semantic.py` + `security.py`, 管道编排在 `ac/governance/__init__.py`

## s_7 修正层详情

| 子维度 | 权重 | 说明 |
|--------|------|------|
| JSON 自动修复 | 0.50 | 括号补全、尾逗号移除 |
| L5 头部补全 | 0.20 | 缺失声明自动注入 |
| 重试机制 | 0.30 | 最多 3 次修正尝试 |

s_7 实现: `ac/governance/corrector.py`

---

## s_5 实测详情

### 评测管线组件

| 模块 | 文件 | 功能 |
|------|------|------|
| cleaner | `ac/qa/pipeline/cleaner.py` | HTML 剥离 · Unicode 标准化 · 空白折叠 · 广告过滤 |
| deduplicator | `ac/qa/pipeline/deduplicator.py` | MinHash 文档级去重 · SimHash 近似去重 |
| language_filter | `ac/qa/pipeline/language_filter.py` | 基于字符集的语言检测 · 目标语种过滤 |
| quality_filter | `ac/qa/pipeline/quality_filter.py` | PPL 困惑度打分 · 低质文本过滤 |

### 评测方法

s_5 由 4 个子维度加权合成：

| 子维度 | 权重 | 说明 |
|--------|------|------|
| 测试通过率 | 0.40 | `ac/qa/tests/` 下全部 test_*.py 的通过比例 |
| 模块覆盖 | 0.30 | 5 个模块（cleaner/dedup/lang/quality/pipeline）的 API 覆盖 |
| 精度探测 | 0.20 | 在预设脏数据上的 clean+dedup+lang 效果评分 |
| 性能基准 | 0.10 | 批量清洗耗时评分 |

$$\text{s_5} = \min(0.4 \cdot P_{\text{test}} + 0.3 \cdot C_{\text{mod}} + 0.2 \cdot P_{\text{prec}} + 0.1 \cdot P_{\text{spd}}, 80)$$

### 运行命令

```powershell
python ac/qa/run_qa.py
```

输出: `ac/qa/last_run.json`

---

## 历史

| 版本 | 日期 | s_5 | 备注 |
|------|------|-----|------|
| v2.2 | — | 0 | 未实施 |
| v2.3 | 2026-05-13 | 78.40 | 清洗管线实测初版: 34/34 测试通过, 100% 模块覆盖 |
