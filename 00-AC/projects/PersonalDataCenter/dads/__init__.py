"""
OpenCode TUI Hooks:
/dads run-pipeline <query>       # 运行RAG流水线
/dads review-result <result>     # 单步审查
/dads contract-create <type>     # 创建契约
/dads contract-verify <id>       # 验证契约
/dads review-step <step>         # 单步调试审查
"""

from .rag_pipeline import RAGPipeline, LangChainRAGPipeline
from .octuple_review import OctupleReview, ReviewStatus, ReviewResult
from .parent_child_contract import ParentChildContract, ContractType, ContractStatus

__all__ = [
    "RAGPipeline", "LangChainRAGPipeline",
    "OctupleReview", "ReviewStatus", "ReviewResult",
    "ParentChildContract", "ContractType", "ContractStatus"
]