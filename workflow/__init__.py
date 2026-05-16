"""workflow/__init__.py
AC 双数据流工作流模块

架构：
                    ┌─────────────────────────┐
                    │       CLT₁  CLT₂  CLTₙ   │
                    │     多终端并发接入        │
                    └──────────┬──────────────┘
                               │
                    ┌──────────▼──────────────┐
                    │   MultiCLTHandler       │
                    │   队列 + 信号量 + 隔离   │
                    └──────────┬──────────────┘
                               │
                    ┌──────────▼──────────────┐
                    │    Stream Router         │
                    │  简单查询 → 流 A         │
                    │  复杂任务 → 流 B         │
                    └──────┬────────┬─────────┘
                           │        │
              ┌────────────▼┐  ┌────▼───────────┐
              │ 流 A         │  │ 流 B            │
              │ Single-turn  │  │ Multi-turn      │
              │ Dispatch     │  │ Orchestrator    │
              │ → Expert     │  │ → PLAN/EXECUTE │
              │ → Governance │  │ → VERIFY/LOG   │
              └──────────────┘  └────────────────┘
                           │        │
                    ┌──────▼────────▼──────────┐
                    │     Governance Pipeline  │
                    │   统一出口 · L5 标注输出  │
                    └──────────────────────────┘

双流设计目的：
- 流 A（单轮）：低延迟，适用于知识问答、简单咨询
- 流 B（多轮）：高能力，适用于多步分析、代码生成、多角色协作
- Router 自动判定路径，也可强制指定
- 治理管道是统一出口，保证双流输出质量一致
"""

from .stream_router import route
from .stream_a_dispatch import stream_a_process
from .stream_b_orchestrator import stream_b_process
from .multi_clt_handler import MultiCLTHandler

__all__ = ["route", "stream_a_process", "stream_b_process", "MultiCLTHandler"]
