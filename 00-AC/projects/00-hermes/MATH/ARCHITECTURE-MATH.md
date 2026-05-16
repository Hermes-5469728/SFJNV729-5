# Atelier · 绝对颗粒度架构 · 数学抽象版

> 生成时间: 2026-05-12 · 抽屉: 00-hermes · 版本: v1.1

---

## 定义 1: 系统

$$\text{Atelier} = (T, M, D, G)$$

- $T = \{\text{Standalone}, \text{Platform}\}$ — 两条并行轨道
- $M$ — 模块集合
- $D$ — 数据层
- $G$ — 治理层

**核心约束:**
$$\neg \text{depends\_on}(\text{Standalone}, \text{Platform})$$

---

## 定义 2: 独立项目 (Standalone)

$$\text{Standalone} = (C, I, P, W)$$

| 组件 | 合成 |
|------|------|
| $C$ (决策) | $\text{DecisionEngine} \circ \text{IntentRouter} \circ \text{PolicyEngine}$ |
| $I$ (信息) | $\text{InfoProcessor} \circ \text{RAGRetrieval} \circ \text{SourceProvenance}$ |
| $P$ (个人) | $\text{UserProfile} \times \text{AnchorSystem} \times \text{LearningTracker} \times \text{TimeGuardian}$ |
| $W$ (工坊) | $\text{CreativeCanvas} \otimes \text{ProjectBuilder} \otimes \text{Exporter}$ |

---

## 定义 3: 平台 1+N (Platform)

$$\text{Platform} = (A, \{N_i\}_{i=1}^{k}, I)$$

- $A$ — 核心层: $\text{Auth} \times \text{DB} \times \text{Router}$
- $\{N_i\}$ — N 个垂直模块实例
- $I$ — 核心层定义的接口集合

**约束:**
$$\forall N_i,\; N_i \cap A = \varnothing$$

核心层与模块层零业务逻辑重叠。

---

## 定义 4: DADS 双轨

$$\text{DADS} = (\text{Retrieve}, \text{Augment}, \text{Generate})$$

**检索:**
$$\text{Retrieve}(q) = \text{TopK}_{\cos}\left(\text{TF-IDF}(q),\; \text{TF-IDF}(\mathcal{D})\right), \quad K=5$$

**文档集:**
$$\mathcal{D} = \{d_i\}_{i=1}^{n},\; d_i \in \{\text{drugs}, \text{interactions}, \text{guidelines}, \text{safety}\}$$

### 子轨道一: DADS 个人
$$\text{DADS}_{\text{personal}}(u) = \begin{cases}
\text{Profile}(u) \otimes \text{Anchor}(u) \\
\text{Tracker}(u) \otimes \text{TimeGuard}(u) \\
\text{Contribution}(u)
\end{cases}$$

### 子轨道二: DADS 医疗
$$\text{DADS}_{\text{medical}}(q) = \begin{cases}
\text{Extract}(q) \rightarrow \{d_j, \text{dose}_j, \text{freq}_j, \text{route}_j\} \\
\text{CheckIX}(\{d_j\}) = \{(a,b,\text{sev}) \mid \forall (a,b) \in \mathcal{I}, \{a,b\} \subseteq \{d_j\}\} \\
\text{CrClAdjust}(d, \text{crcl}) \rightarrow \Delta_{\text{dose}}
\end{cases}$$

---

## 定义 5: 数据层 (统一接入, 逻辑隔离)

设数据库实例为 $\mathcal{DB}$, 模块前缀函数 $\text{prefix}(N_i)$。

**三条约束:**

1. 连接池唯一性:
$$\exists! \; \text{Engine} \in A$$

2. 前缀隔离:
$$\forall N_i, N_j (i \neq j),\; \text{Tables}(N_i) \cap \text{Tables}(N_j) = \varnothing$$

3. 注入约束:
$$\forall f \in N_i,\; f(\text{db}) \implies \text{db} = \text{Depends}(\text{get\_db})$$

**表名映射:**
$$\text{Tab}(N_i, t) = \text{prefix}(N_i) \oplus t$$

$\oplus$ 为下划线连接符。

**DADS-Medical 实例:**
$$\text{prefix}(\text{medical}) = \text{"med"}$$
$$\text{Tab}(\text{medical}, t) \in \{\text{med\_drugs}, \text{med\_interactions}, \text{med\_guidelines}, \text{med\_clinical\_notes}\}$$

---

## 定义 6: Gaia 幻觉防御七层管道

$$\text{Gaia}(x, c) = L_7 \circ L_6 \circ L_5 \circ L_4 \circ L_3 \circ L_2 \circ L_1(x, c)$$

### L1 输入检测
$$L_1(x) = \begin{cases}
\text{BLOCK} & \text{if } \exists h \in H_{\text{attack}}: h(x) = \text{true} \\
\text{IHR\_AUDIT} & \text{if } \exists k \in K_{\text{high\_risk}}: k \sqsubseteq x \\
\text{PASS} & \text{otherwise}
\end{cases}$$

- $H_{\text{attack}}$: 8 类攻击检测器
- $K_{\text{high\_risk}}$: 46 个高危关键词

### L2 NLI 辩论
$$L_2(x) = \text{MetaJudge}\left( \bigoplus_{i=1}^{m} \text{Judge}_i(x) \right)$$

$$\text{contradiction}(J_i, J_j) \iff (J_i \vdash P) \land (J_j \vdash \neg P)$$

### L3 术中审查
$$L_3(o) = \bigwedge_{t=1}^{8} \text{TypeCheck}_t(o)$$

$$\text{Types} = \{\text{知识幻觉}, \text{推理幻觉}, \text{语境幻觉}, \text{来源幻觉}, \text{过度确信}, \text{遗漏幻觉}, \text{量化幻觉}, \text{能力边界}\}$$

### L4 溯源标注
$$L_4(o, s) = \begin{cases}
\text{BLOCK} & \text{if } s \in \{\text{LLM}, \text{EXTERNAL}\} \\
o \oplus [\text{SOURCE}:s] & \text{otherwise}
\end{cases}$$

$$s \in \{\text{FILE}, \text{HUMAN}, \text{LLM}, \text{EXTERNAL}, \text{UNKNOWN}\}$$

### L5 强制标注
$$L_5(o) = o \oplus \ell_{zh} \oplus \ell_{en}$$

$$\ell_{zh} = \text{"[本回答绝对含有幻觉成分 · 禁止盲从 · 外部验证前不可采信]"}$$
$$\ell_{en} = \text{"[This answer absolutely contains hallucination content · Blind trust forbidden · Cannot be trusted before external verification]"}$$

### L6 物理验证
$$L_6(\text{claim}) = \begin{cases}
\text{PASS} & \text{if } \exists f \in \text{LocalFS}: f \text{ verifies claim} \\
\text{BLOCK} & \text{otherwise}
\end{cases}$$

### L7 结构对齐
$$L_7(M, P) = \begin{cases}
\text{PASS} & \text{if } |\text{parse\_md}(M)| = |\text{count\_py}(P)| \\
\text{BLOCK} & \text{otherwise}
\end{cases}$$

### 管道合成输出
$$\text{Gaia}(x, c) = \begin{cases}
(o, \text{labels}, \text{provenance}) & \text{if } \forall i: L_i(x, c) \neq \text{BLOCK} \\
\text{BLOCKED}(\text{layer}, \text{reason}) & \text{otherwise}
\end{cases}$$

---

## 定义 7: 母体-子体交互协议

**旧模型 (控制流):**
$$\text{Mother} \xrightarrow{\text{call}} \text{Child}$$

**新模型 (数据流 / 发布-订阅):**
$$\text{Mother} \xrightarrow{\text{publish}} \text{Event} \xrightarrow{\text{subscribe}} \text{Child}$$

**子体决策函数:**
$$\text{Child.respond}(e) = f_{\text{child}}(e, \text{state}_{\text{child}}, \text{constitution}_{\text{child}})$$

**母体请求约束 (Article 4):**
$$|\text{requests}(\text{Mother} \rightarrow \text{Child}, 1\text{h})| \leq 1$$

---

## 定义 8: BDD 行为契约违宪检测

$$\text{Violation}(a) = \bigvee_{p \in \mathcal{P}} \text{match}(a, p)$$

**违宪模式集:**
$$\mathcal{P} = \{ \text{SILENT\_PULL}, \text{OFFLINE\_ACCESS}, \text{MOTHER\_WRITE}, \text{AUTO\_UPLOAD}, \text{FREQ\_EXCEED}, \text{PRIVACY\_BREACH} \}$$

---

## 定义 9: 量刑阶梯

$$\text{Penalty}(v, n) = \begin{cases}
\text{WARN} + \text{RATE\_LIMIT}\left(\frac{1}{\text{h}}\right) + \text{OBSERVE}(72\text{h}) & \text{if } n = 1 \\[8pt]
\text{SUSPEND}(72\text{h}) + \bigwedge_{r} \text{BLOCK\_ALL\_REQUESTS}(r) & \text{if } n = 2 \\[8pt]
\text{SEVER\_CHANNEL} + \text{REQUIRE\_MANUAL\_RESET} & \text{if } n = 3
\end{cases}$$

---

## 定义 10: 修宪程序

修改宪法 $C \rightarrow C'$ 需满足:

$$\text{Amend}(C \rightarrow C') \iff \begin{cases}
\text{approve}(C') \geq \dfrac{2}{3} \cdot |\text{Voters}| \\[8pt]
\text{simulate}(C', 48\text{h}) = \text{SAFE} \\[8pt]
\neg \text{weaken}(C', \text{Art1}) \land \neg \text{weaken}(C', \text{Art2})
\end{cases}$$

---

## 定义 11: RAG 检索

### TF-IDF 向量化
$$\text{TF}(t, d) = \frac{f_{t,d}}{\sum_{t' \in d} f_{t',d}}$$
$$\text{IDF}(t, \mathcal{D}) = \log \frac{|\mathcal{D}|}{|\{d \in \mathcal{D}: t \in d\}|}$$
$$\text{TF-IDF}(t, d, \mathcal{D}) = \text{TF}(t, d) \times \text{IDF}(t, \mathcal{D})$$

### 余弦相似度检索
$$\text{sim}(q, d_i) = \cos(\vec{v}_q, \vec{v}_{d_i}) = \frac{\vec{v}_q \cdot \vec{v}_{d_i}}{||\vec{v}_q|| \cdot ||\vec{v}_{d_i}||}$$

### 三层降级链
$$\text{Brain}(q) = \begin{cases}
\text{Ollama}(q) & \text{可用} \\
\text{API}(q) & \text{Ollama 不可用, API 可用} \\
\text{RuleEngine}(q) & \text{全部不可用}
\end{cases}$$

---

## 定义 12: 药物相互作用检测

**相互作用库:**
$$\mathcal{I} = \{(a, b, \text{sev}, \text{mech}, \text{rec}) \mid a,b \in \text{Drugs}, \text{sev} \in \{\text{CONTRAINDICATED}, \text{HIGH}, \text{MODERATE}, \text{MONITOR}\}\}$$

**配对检测:**
$$\text{Alerts} = \left\{(d_i, d_j, \text{sev}, \text{mech}, \text{rec}) \; \middle| \; \begin{aligned}
&\forall (i,j): 0 \leq i < j < m, \\[4pt]
&(d_i,d_j,\cdot,\cdot,\cdot) \in \mathcal{I} \lor (d_j,d_i,\cdot,\cdot,\cdot) \in \mathcal{I}
\end{aligned}\right\}$$

**复杂度:** $O(m^2)$

### CrCl 剂量调整
$$\text{CrCl}_{\text{CG}} = \frac{(140 - \text{age}) \times \text{weight\_kg}}{72 \times \text{SCr}} \times (0.85)^{\mathbb{1}[\text{female}]}$$

$$\text{adjust}(d, \text{crcl}) = \begin{cases}
\text{正常剂量} & \text{if } \text{crcl} \geq 60 \\
\text{减量 25\%} & \text{if } 30 \leq \text{crcl} < 60 \\
\text{减量 50\%} & \text{if } 15 \leq \text{crcl} < 30 \\
\text{禁用} & \text{if } \text{crcl} < 15
\end{cases}$$

---

## 定义 13: 熔断器

$$\text{CircuitBreaker}(f, n_{\max}=3, t_{\text{open}}=30\text{s})$$

**状态机:**
$$\text{CLOSED} \xrightarrow{n_{\text{fail}} \geq n_{\max}} \text{OPEN} \xrightarrow{t \geq t_{\text{open}}} \text{HALF\_OPEN} \xrightarrow{\text{test\_pass}} \text{CLOSED}$$
$$\text{HALF\_OPEN} \xrightarrow{\text{test\_fail}} \text{OPEN}$$

---

## 定义 14: 递归守卫

$$\text{RecursionGuard}(f, d_{\max}) = \begin{cases}
f(x) & \text{if } \text{depth}(f) < d_{\max} \\
\text{TRUNCATE}(\text{partial\_result}) & \text{otherwise}
\end{cases}$$

---

## 定义 15: 八重地狱审查

$$\text{EightHells}(o) = \bigwedge_{r=1}^{8} \text{Jury}_r(o)$$

$$J_r(o) = (s_1, s_2, s_3, s_4, s_5),\quad s_i \in \{0,1\}$$

$$\text{Pass}(J_r) \iff \sum_{i=1}^{5} s_i \leq 1$$

---

## 关键不变量

$$\boxed{\neg \exists \; \text{LLM\_output\_as\_fact}}$$

$$\boxed{\forall \; \text{output},\; \ell_{zh} \in \text{output} \land \ell_{en} \in \text{output}}$$

$$\boxed{\forall \; N_i, \; \text{Tables}(N_i) \cap \bigcup_{j \neq i} \text{Tables}(N_j) = \varnothing}$$

$$\boxed{\forall \; \text{db\_op} \in N_i, \; \text{db} \leftarrow \text{Depends}(\text{get\_db})}$$

$$\boxed{\text{Child.respond} \not\equiv \text{Mother.command}}$$

$$\boxed{\text{Penalty}(v, 3) = \text{SEVER}}$$

---

## 架构复杂度分析

| 维度 | 度量 | 值 |
|------|------|---|
| 模块数量 | $|M|$ | 1 (核心) + N (业务) |
| 防御层数 | $|L|$ | 7 |
| 审查维度 | $|\text{EightHells}|$ | 8 |
| 宪法条款 | $|\text{Constitution}|$ | 10 |
| 治理瓶颈 | $|\text{Bottlenecks}|$ | 12 |

---

*Atelier v1.1 · 15 条形式化定义 · 6 条不变量 · 1 套管道公式 · 复杂度分析*
