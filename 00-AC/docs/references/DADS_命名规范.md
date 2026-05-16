# 项目命名规范 v2.0 · 统一

> 一个项目 · 多个切面 · 统一命名

---

## 核心原则

一个通用认知决策引擎。医疗是第一个垂直领域。

## 项目命名

```
CoPilot/                       主项目·通用决策引擎
├── agents/                     Agent定义
│   ├── personal/               个人助手(6领域+4元)
│   └── dads/                   医疗垂直(DADS/CDSS)
├── skills/                     技能(4母体+4子体)
│   ├── core-knowledge-stitcher/
│   ├── core-signal-mapper/
│   ├── core-instruction-encoder/
│   ├── core-governance/
│   ├── dads-guideline/
│   ├── dads-diagnosis/
│   ├── dads-protocol/
│   └── llm-executor/
├── eval/                       评测
├── datasets/                   数据
├── app.py                      Streamlit前端
├── server.py                   Flask面板
└── AGENTS.md                   入口
```

## 废弃名称映射

| 旧名 | 新理解 |
|------|--------|
| AgentHub | CoPilot 的能力基础（原系统目录保留不动）|
| CoPilot-Medical | → CoPilot（主项目·不只医疗）|
| Hermes-AgentHub | CoPilot 的 CLI 开发工具 |
| MyNewHub | → Hermes-AgentHub |
| DADS | CoPilot 的医疗垂直子体 |

## 命名公式

```
项目:       CoPilot（大写C·PascalCase）
垂域子体系: {前缀}-{功能}（如 dads-guideline）
母体技能:   core-{功能}
Agent文件:  {小写}-{小写}.md
评测文件:   {前缀}-{编号}.yaml
```

## 禁止

- ❌ 不要因为功能不同就建新项目文件夹
- ❌ 不要给同一个项目起多个名字
- ❌ 旧名保留在文档里，代码只认新名
