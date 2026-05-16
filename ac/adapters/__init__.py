"""AC 模型适配器层 · 统一接口 + 路由 + 治理

入口规则:
  1. 禁止直接调用适配器 —— 走 router.call() 经过治理
  2. 密钥走环境变量，禁止硬编码
  3. 新模型在 registry 注册后自动生效
"""

import sys
from pathlib import Path
_ac_dir = Path(__file__).resolve().parent.parent.parent
if str(_ac_dir) not in sys.path:
    sys.path.insert(0, str(_ac_dir))

from .base import ModelAdapter, ModelResponse
from .registry import ModelRegistry, get_registry
from .router import ModelRouter, get_router
from .deepseek_free import DeepSeekFreeAdapter
from .qwen_free import QwenFreeAdapter
from .doubao import DoubaoAdapter
from .kimi import KimiAdapter
from .wenxin_adapter import WenxinAdapter

_reg = get_registry()
_reg.register(DeepSeekFreeAdapter())
_reg.register(QwenFreeAdapter())
_reg.register(DoubaoAdapter())
_reg.register(KimiAdapter())

_reg.register(WenxinAdapter())

__all__ = [
    "ModelAdapter", "ModelResponse",
    "ModelRegistry", "get_registry",
    "ModelRouter", "get_router",
    "DeepSeekFreeAdapter",
    "QwenFreeAdapter",
    "DoubaoAdapter",
    "KimiAdapter",
    "WenxinAdapter",
]
