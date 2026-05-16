"""AC Package · Architecture Coordinator"""

__version__ = "2.4"
__author__ = "Hermes"
__description__ = "Portable Architecture Coordinator · 便携式架构调度工具"

# Export key components
from . import core
from . import governor
from . import collaborative_governor
from . import orchestrator
from . import schemas
from . import adapters
from .dual_inference import DualInference, get_dual
from .schema_contract import ClinicalQuery, ClinicalResponse, DualInferenceResult, DispatchResponse
from .jarvis_core import Jarvis, JarvisResponse, get_jarvis
from .knowledge_service import KnowledgeService, get_knowledge

__all__ = [
    "core",
    "governor",
    "collaborative_governor",
    "orchestrator",
    "schemas",
    "adapters",
    "DualInference",
    "get_dual",
    "ClinicalQuery",
    "ClinicalResponse",
    "DualInferenceResult",
    "DispatchResponse",
    "Jarvis",
    "JarvisResponse",
    "get_jarvis",
    "KnowledgeService",
    "get_knowledge",
]