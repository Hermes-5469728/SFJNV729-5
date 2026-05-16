---
title: 失忆预防铁律：数据库schema版本控制
category: architecture
source: conversation_analysis
verified: true
tags: 绝对真值,认知分析,社会观察
created: 2026-05-13T05:02:40.963273+00:00
---

# 失忆预防铁律：数据库schema版本控制

ac_platform.db被覆盖的根本原因：
- 多个AI各自用不同schema初始化数据库
- 后执行的覆盖前执行的
- 没有数据库migration版本控制

失忆预防铁律：
1. 任何操作ac_platform.db的代码必须先校验schema版本(PRAGMA user_version)
2. schema不匹配时不允许直接CREATE/ALTER，必须走migration脚本
3. AI必须在migration前输出diff，经确认后执行
4. 涅槃快照必须包含schema版本号

操作与确认分离：
对于任何涉及文件修改/数据库写入的操作，AI必须先输出计划，
等待决策中心输入'确认'或'1'之后才能执行。
