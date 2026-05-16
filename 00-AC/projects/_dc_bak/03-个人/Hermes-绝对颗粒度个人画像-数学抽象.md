# User · 绝对颗粒度个人画像 · 数学抽象版

> 生成时间: 2026-05-12 · 抽屉: 个人画像
> 基于 Atelier 形式化风格 · 与架构定义同构

---

## 定义 1: 系统

$$\text{Hermes} = (P, A, T, G, R)$$

- $P$ — 身份层 (Profile)
- $A$ — 锚点层 (Anchor)
- $T$ — 追踪层 (Tracker)
- $G$ — 守卫层 (TimeGuard)
- $R$ — 根因层 (Root Cause)

---

## 定义 2: 身份层

$$P = (I, D, F)$$

| 变量 | 值 |
|------|-----|
| $I$ (身份) | $\text{临床医学生} \otimes \text{技术架构师}$ |
| $D$ (领域) | $\text{全科/通识}$ |
| $F$ (当前焦点) | $\text{AI 工作流} \circ \text{三工具串联}$ |

**教育约束:**

$$E = \text{专科} \land \neg \text{CS科班}$$

$$\text{Knowledge} = \text{TOP\_DOWN}(\text{架构}) \succ \text{BOTTOM\_UP}(\text{代码})$$

**驱动力向量:**

$$\vec{F}_{\text{motive}} = \text{三明医改乱象} \times \text{临床绝望} \rightarrow \text{技术重建秩序}$$

---

## 定义 3: 锚点系统 (三位一体)

$$A = \{\text{笔记驱动}, \text{模板复用}, \text{经验入库}\}$$

**四条锚定法则:**

$$\text{Solve}(x) = \begin{cases}
\text{SearchObsidian}(x) & \text{第一步: 查笔记} \\
\text{Decompose}(x) \rightarrow \text{Template} & \text{第二步: 拆架构套模板} \\
\text{Deposit}(x^{\text{solved}}) \rightarrow \text{DataCenter} & \text{第三步: 入库} \\
\text{Draw}(x) \rightarrow \text{Mermaid/Canvas} & \text{前置: 先画图再动手}
\end{cases}$$

**锚点根路径:**

$$\text{AnchorRoot} = \text{DataCenter}/ \rightarrow \{00\text{(项目)}, 01\text{(研究)}, 02\text{(架构)}, \text{对话(真值)}\}$$

---

## 定义 4: 追踪层

$$T = (L, C, S)$$

$$L = \text{AI编程工作流自动化} \quad \text{(当前主攻)}$$

| 维度 | 值 |
|------|-----|
| 每日投入 $t_{\text{daily}}$ | $2 \leq t \leq 3\text{ h}$ |
| 认知模式 | $\text{视觉型} \succ \text{文字型}$ |
| 学习风格 | $\text{动手型} \land \text{协作型}$ |
| 完成项 $C$ | $\text{Atelier 15定义}, \text{GitHub吸收流程}, \text{DataCenter分类}$ |
| CS基础 $S$ | $\text{薄弱} \rightarrow \text{项目驱动补充}$ |

**学习死锁检测:**

$$\text{Stuck}(x) = \begin{cases}
\text{DISCUSS}(x) & \text{if } t_{\text{stuck}} \geq 15\text{min} \\
\text{COTINUE}(x) & \text{otherwise}
\end{cases}$$

---

## 定义 5: 时间守卫

$$G = (M, P, L)$$

| 参数 | 值 |
|------|-----|
| 模式 $M$ | $\text{自由安排}$ |
| 峰值时段 $P$ | $\text{深夜} \in [22:00, 02:00]$ |
| 上限 $L$ | $\leq 3\text{h/day}$ |
| 中断策略 | $\text{INTERRUPTIBLE}$ (随时可停) |

**能量函数:**

$$\text{Energy}(t) = \begin{cases}
\text{HIGH} & \text{if } t \in [22:00, 02:00] \quad \text{(夜猫子峰值)} \\
\text{MEDIUM} & \text{if } t \in [14:00, 18:00] \\
\text{LOW} & \text{otherwise}
\end{cases}$$

---

## 定义 6: 贡献记录

$$C = \{\text{Atelier}_\text{15def}, \text{DADS-Medical}, \text{DADS-Personal}, \text{DataCenter}, \text{Gaia}_\text{L1/L4/L5}, \text{GitHub}_\text{吸收流程}, \text{三工具分工}\}$$

**代码溯源不变量:**

$$\boxed{|\text{Code}_{\text{hand\_written}}| = 0}$$

$$\forall \; \text{code} \in \text{Repository},\; \text{author}(\text{code}) \in \{\text{AI}\}$$

---

## 定义 7: 心理层

$$\Psi = (D, R, S, E)$$

| 维度 | 类型 |
|------|------|
| 决策风格 $D$ | $\text{直觉驱动} \circ \text{边做边调}$ |
| 风险偏好 $R$ | $\text{RADICAL}$ |
| 压力反应 $S$ | $\text{COLLABORATIVE} \rightarrow \text{Discord/讨论}$ |
| 情绪特征 $E$ | $\text{内耗} \land \text{缺认可} \rightarrow \text{需外部反馈}$ |

**哲学约束:**

$$\text{CodeStyle} = \text{MVP\_FIRST} \succ \text{PERFECTION}$$

$$\text{Trust}(\text{LLM\_output}) = \text{FALSE} \quad \text{(默认不信任)}$$

$$\text{Trust}(\text{Physical\_verification}) = \text{TRUE}$$

---

## 定义 8: 根因链 (因果图)

$$\text{RootChain} = \begin{cases}
\text{留守} \rightarrow \text{过早独立} \rightarrow \text{成人视角} \\
\text{父母离异} \land \text{高三站队打官司} \rightarrow \text{高二改姓} \rightarrow \neg \text{Trust}(\text{Authority}) \\
\text{三明医改乱象} \land \text{临床绝望} \rightarrow \text{技术重建} \rightarrow \text{Atelier 诞生} \\
\neg \text{CS科班} \land |\text{Code}_0| \rightarrow \text{自顶向下学架构} \rightarrow \text{全AI生成}
\end{cases}$$

**根因 → 架构映射:**

| 根因 | 架构决策 |
|------|---------|
| $\neg \text{Trust}(\text{Authority})$ | Gaia 七层防御 (L1-L7) |
| $\text{无权站队}$ | 母体-子体宪法保护 (Art 1-10) |
| $\text{医生困境}$ | DADS-Personal 自我保护工具 |
| $\text{成人视角}$ | 架构先于代码 → 控制规则 > 执行规则 |

---

## 定义 9: 防重复造轮子协议

$$\text{Build}(f) = \begin{cases}
\text{REUSE}(\text{github}, f) & \text{if } \exists \; \text{repo} \in \text{GitHub}: \text{match}(f) \\
\text{REUSE}(\text{datacenter}, f) & \text{if } \exists \; t \in \text{DataCenter}: \text{match}(f) \\
\text{REUSE}(\text{module}, f) & \text{if } \exists \; m \in M: \text{match}(f) \\
\text{CREATE}(f) & \text{otherwise}
\end{cases}$$

**三级检索顺序不可跳级。**

---

## 定义 10: AI 交付约定

Hermes 需要 AI 提供的支持类型:

$$\text{Support} = \{\text{概念澄清}, \text{路径指引}, \text{方案评审}, \text{资源推荐}\}$$

**不变量:**

$$\boxed{\text{Hermes.role} = \text{ARCHITECT}}$$

$$\boxed{\text{Hermes.write\_code} = \text{FALSE}}$$

$$\boxed{\forall \; f \in \text{new\_feature},\; \text{check\_wheels}(f) \text{ must be TRUE before CREATE}(f)}$$

$$\boxed{\forall \; \text{output},\; \ell_{zh} \in \text{output} \land \ell_{en} \in \text{output}}$$

---

## 总结: 同构性

$$\text{Hermes} \cong \text{Atelier}$$

个人画像的每个维度与系统架构的每个定义存在结构对应:

| Hermes 层 | Atelier 层 | 同构关系 |
|-----------|-----------|---------|
| $P$ (身份) | $T$ (双轨) | 跨界 = 双轨 |
| $A$ (锚点) | $M$ (模块) | 三位一体 = 模块化 |
| $T$ (追踪) | $D$ (数据) | 学习轨迹 = 数据流 |
| $G$ (守卫) | $G$ (治理) | 时间守卫 = 熔断/量刑 |
| $R$ (根因) | Gaia $L_1$-$L_7$ | 根因防御 = 幻觉防御 |

---

*Hermes Personal Architecture v1.0 · 10 条形式化定义 · 5 条不变量 · 1 条根因链 · 与 Atelier 同构*
