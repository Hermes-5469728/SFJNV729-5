# Skill 清单 · Opencode + Trae + Obsidian

> 平台整合索引，按工具分类，标注来源与用途

---

## 一、Opencode Skills

Opencode Skills 存储在 `{USER_HOME}\.config\opencode\skills\`，按功能域分目录。

### 工程类 (engineering)

| Skill | 用途 | 状态 |
|-------|------|------|
| diagnose | 硬 Bug 诊断循环：复现→最小化→假设→仪表→修复→回归测试 | 可用 |
| grill-with-docs | 对照领域模型和文档进行方案拷问，更新 CONTEXT.md/ADR | 可用 |
| improve-codebase-architecture | 发现代码库深化机会，解耦紧密模块 | 可用 |
| prototype | 构建可丢弃原型，终端 App 或 UI 多方案切换 | 可用 |
| setup-matt-pocock-skills | 在 AGENTS.md 中注册工程 Skill 的 issue tracker/标签/领域文档 | 可用 |
| tdd | 红-绿-重构 TDD 循环 | 可用 |
| to-issues | 将计划/PRD 拆解为独立 issue | 可用 |
| to-prd | 将对话上下文转为 PRD 并发布到 issue tracker | 可用 |
| triage | Issue 状态机驱动分类 | 可用 |
| zoom-out | 提供代码库高层上下文 | 可用 |

### 生产力类 (productivity)

| Skill | 用途 |
|-------|------|
| caveman | 极简通信模式，减少 75% token 消耗 |
| grill-me | 对方案进行决策树式拷问 |
| handoff | 将当前对话压缩为交接文档 |
| write-a-skill | 创建新的 Agent Skill（含结构、渐进披露、资源） |

### 杂项 (misc)

| Skill | 用途 |
|-------|------|
| git-guardrails-claude-code | 设置 Git 钩子阻止危险命令 |
| migrate-to-shoehorn | 将 `as` 类型断言迁移到 shoehorn |
| scaffold-exercises | 创建练习题目录结构 |
| setup-pre-commit | 配置 Husky + lint-staged + 类型检查 + 测试 |

### 个人类 (personal)

| Skill | 用途 |
|-------|------|
| edit-article | 编辑改进文章结构 |
| obsidian-vault | 搜索/创建/组织 Obsidian 笔记 |

### 已废弃 (deprecated)

design-an-interface, qa, request-refactor-plan, ubiquitous-language

### 进行中 (in-progress)

review, writing-beats, writing-fragments, writing-shape

---

## 二、Trae Skills

Trae Skills 存储在 `00-AC/projects/.trae/skills/`，两个来源：

### 2.1 mattpocock-skills (与 Opencode 共用)

路径 `00-AC/projects/.trae/skills/mattpocock-skills/skills/`
与上方 Opencode Skill 列表完全一致。（git 子模块/独立仓库）

### 2.2 personal-data-center

| Skill | 路径 | 用途 |
|-------|------|------|
| personal-data-center | `.trae/skills/personal-data-center/SKILL.md` | 个人数据中心操作指南 |

### 2.3 chinese-prompts (AI 模型 Prompt 集合)

按平台/模型分类的 Prompt 采集，不通过 skill_loader 加载，作为参考库。

**OpenAI 系列：**
- GPT-5 / 5.1 / 5.2 / 5.3 / 5.4 / 5.5（含各种 personality）
- o3 / o4-mini（含不同 reasoning effort）
- Codex CLI / Agent Mode / Canvas / Deep Research / 文件搜索 / Web 搜索 / 图片生成 / 记忆 / 高级语音
- GPT-4.1 / 4.5 / 4o

**Google Gemini 系列：**
- Gemini 2.5 Flash / Pro
- Gemini 3 Flash / Pro / 3.1 Pro
- AI Studio / NotebookLM / Chrome / Workspace
- Jules Agent

**Grok (xAI) 系列：**
- Grok 3 / 4 / 4.1 / 4.2 / 4.3
- 多种 Personality（Ani, Mika, Rudi, Valentine 等）
- Twitter Translate / Account

**字节跳动 (Trae/豆包)：**
- Trae.ai: Builder / Chat / SOLO Coder
- 豆包 Prompt + 写作模板

**其他国内模型：**
- 月之暗面 Kimi K2.5
- MiniMax M2.5
- 腾讯 CodeBuddy（Chat / Craft）
- 阿里 Qoder
- 深度求索 DeepSeek

**其他国际平台：**
- Anthropic Claude Sonnet 4
- Cursor (Agents/Composer / Chat / Memory)
- Windsurf (Wave 11)
- Cline / Roo Code / Codex CLI
- Bolt / Lovable / v0 / Replit
- Manus Agent
- Perplexity / Kagi / Le Chat / Meta AI
- Devin / Emergent / Fellou / Same.dev
- Notion AI / Microsoft Copilot
- Xcode (Document/Explain/Message/Playground/Preview)
- Warp / Windsurf / Raycast
- Proton Lumo / Sesame Maya / Poke
- 其他：Kiro, Leap.new, Indus AI, Traycer, Saharsh, Orchids

---

## 三、Obsidian 集成

### 3.1 Obsidian Vault Skill

通过 `opencode` 的 `obsidian-vault` Skill 交互：
- 搜索笔记
- 创建新笔记
- 管理 Wikilink
- 维护 Index 笔记

### 3.2 笔记存储路径

```
{PROJECT_ROOT}\.obsidian/
```

包含 Obsidian 配置、插件、主题等。

### 3.3 关联数据

00-DataCenter/ 目录作为知识库数据源，包含：
- anchor_db.json（锚点引擎）
- 结构化数据文件
- 与 Obsidian vault 可能存在交叉链接

---

## 四、Skill 调用方式

```
平台      加载方式
──────────────────────────────
Opencode  对话自动匹配 available_skills
          手动: /skill <skill-name>
Trae      通过 skill_loader.py 按需加载
Obsidian  通过 opencode obsidian-vault skill 间接操作
          或直接在 Obsidian App 中操作
```

## 五、Skill 数量统计

```
Opencode skills:  28（4 废弃 + 4 进行中 + 20 活跃）
Trae skills:      29 SKILL.md（28 mattpocock + 1 personal-data-center）
Trae prompts:     200+ AI 模型 Prompt 文件
Obsidian:         1 vault + 1 opcode bridge skill
```

---

*生成日期: 2026-05-13*
