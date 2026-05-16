"""
PipelineTrace - 结构化链路日志
记录每个节点的执行情况：输入/输出哈希、延迟、token消耗、校验结果

功能：
- 结构化trace记录
- JSON格式输出
- 支持本地文件或数据库存储
"""

import json
import os
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from loguru import logger

@dataclass
class NodeTrace:
    """节点执行trace"""
    node_id: str
    model_name: Optional[str]
    input_hash: str
    output_hash: str
    latency_ms: int
    tokens_used: Optional[int] = None
    gaia_verdict: str = "N/A"
    retry_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None

@dataclass
class PipelineTrace:
    """完整管道trace"""
    trace_id: str
    pipeline: str
    nodes: List[NodeTrace] = field(default_factory=list)
    total_retries: int = 0
    final_verdict: str = "RUNNING"
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None

class PipelineTracer:
    """管道追踪器"""

    def __init__(self, trace_dir: str = ".traces", db_path: str = None):
        self.trace_dir = trace_dir
        self.db_path = db_path
        os.makedirs(trace_dir, exist_ok=True)
        self._trace_counter = 0
        logger.info(f"PipelineTracer初始化: trace_dir={trace_dir}")

    def _compute_hash(self, content: str) -> str:
        """计算内容哈希"""
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()[:16]}"

    def create_trace(self, trace_id: str, pipeline: str) -> PipelineTrace:
        """创建新trace"""
        return PipelineTrace(trace_id=trace_id, pipeline=pipeline)

    def record_node(self, trace: PipelineTrace, node_id: str, model_name: str,
                   input_content: str, output_content: str, latency_ms: int,
                   tokens_used: int = None, gaia_verdict: str = "N/A",
                   retry_count: int = 0, error: str = None) -> NodeTrace:
        """记录节点执行"""
        node_trace = NodeTrace(
            node_id=node_id,
            model_name=model_name,
            input_hash=self._compute_hash(input_content),
            output_hash=self._compute_hash(output_content),
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            gaia_verdict=gaia_verdict,
            retry_count=retry_count,
            error=error
        )
        trace.nodes.append(node_trace)
        trace.total_retries += retry_count
        return node_trace

    def finalize_trace(self, trace: PipelineTrace, verdict: str):
        """完成trace"""
        trace.final_verdict = verdict
        trace.end_time = datetime.now().isoformat()

    def to_json(self, trace: PipelineTrace) -> str:
        """转换为JSON字符串"""
        return json.dumps(asdict(trace), ensure_ascii=False, indent=2)

    def save_to_file(self, trace: PipelineTrace) -> str:
        """保存到本地文件"""
        filename = f"{trace.trace_id}.json"
        filepath = os.path.join(self.trace_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json(trace))
        logger.debug(f"Trace已保存: {filepath}")
        return filepath

    def save_to_db(self, trace: PipelineTrace):
        """保存到SQLite数据库"""
        if not self.db_path:
            return

        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pipeline_traces (
                trace_id TEXT PRIMARY KEY,
                pipeline TEXT,
                nodes_json TEXT,
                total_retries INTEGER,
                final_verdict TEXT,
                start_time TEXT,
                end_time TEXT
            )
        ''')

        # 插入记录
        cursor.execute('''
            INSERT OR REPLACE INTO pipeline_traces
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            trace.trace_id,
            trace.pipeline,
            self.to_json(trace),
            trace.total_retries,
            trace.final_verdict,
            trace.start_time,
            trace.end_time
        ))

        conn.commit()
        conn.close()
        logger.debug(f"Trace已保存到数据库: {trace.trace_id}")

    def get_summary(self, trace: PipelineTrace) -> Dict[str, Any]:
        """获取trace摘要"""
        total_latency = sum(n.latency_ms for n in trace.nodes)
        return {
            "trace_id": trace.trace_id,
            "pipeline": trace.pipeline,
            "node_count": len(trace.nodes),
            "total_retries": trace.total_retries,
            "total_latency_ms": total_latency,
            "final_verdict": trace.final_verdict,
            "start_time": trace.start_time,
            "end_time": trace.end_time
        }

    def generate_trace_id(self, pipeline: str) -> str:
        """生成trace ID"""
        self._trace_counter += 1
        date_str = datetime.now().strftime('%Y%m%d')
        return f"tr-{date_str}-{self._trace_counter:03d}"

# 全局追踪器
_tracer = None

def get_tracer() -> PipelineTracer:
    """获取追踪器单例"""
    global _tracer
    if _tracer is None:
        _tracer = PipelineTracer()
    return _tracer

# 测试
if __name__ == "__main__":
    tracer = get_tracer()

    # 创建trace
    trace = tracer.create_trace("tr-20260512-001", "code_generation")

    # 记录节点
    import time
    start = time.time()
    time.sleep(0.1)  # 模拟执行
    tracer.record_node(
        trace=trace,
        node_id="generate",
        model_name="deepseek-chat",
        input_content="创建一个数据处理函数",
        output_content="def process_data(input_data): return {k: v*2 for k, v in input_data.items()}",
        latency_ms=int((time.time() - start) * 1000),
        gaia_verdict="PASS"
    )

    # 完成trace
    tracer.finalize_trace(trace, "PASS")

    # 输出
    print("Trace摘要:")
    print(json.dumps(tracer.get_summary(trace), indent=2, ensure_ascii=False))
    print("\n完整JSON:")
    print(tracer.to_json(trace))

    # 保存
    path = tracer.save_to_file(trace)
    print(f"\n已保存到: {path}")