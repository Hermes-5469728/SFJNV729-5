---
title: 绝对颗粒度评估·核心业务价值（底盘 vs 轮胎）
category: architecture
source: architecture_analysis
verified: true
tags: 绝对真值,评估标准,代码规范
created: 2026-05-13T03:59:44.163298+00:00
---

# 绝对颗粒度评估·核心业务价值（底盘 vs 轮胎）

轮胎（pip install，严禁自研）:
- 网络请求: HTTP/gRPC必须用requests/httpx/aiohttp
- 数据校验: JSON→Python用pydantic，不自己写if isinstance
- 日志记录: 用loguru或标准库logging，不用print/f.write
- 向量检索: 用chromadb/faiss/milvus，不自己写余弦相似度
- 命令行解析: 用click/typer/argparse，不自己解析sys.argv

底盘（必须自研，严禁过度封装）:
- Agent记忆管理: 何时存/存什么/怎么压缩必须自己写
- 工具调用路由: 根据当前代码库结构决定调用哪个CLI命令必须自己写
- 错误恢复策略: 重试/降级/人工介入的决策树必须自己写
