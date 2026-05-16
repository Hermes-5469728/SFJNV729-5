"""
BrainPool - 多AI模型注册表与路由
支持 DeepSeek/Claude/Qwen/Kimi/Ollama

功能：
- 模型注册与能力标签
- 意图路由到最优模型
- 并行调用取共识
"""

from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass
from enum import Enum
from loguru import logger
import asyncio

class Intent(Enum):
    """意图类型"""
    ARCH_DESIGN = "INTENT_ARCH_DESIGN"
    CODE_REVIEW = "INTENT_CODE_REVIEW"
    CREATIVE = "INTENT_CREATIVE"
    VIDEO = "INTENT_VIDEO"
    FORMAT = "INTENT_FORMAT"
    FAST_QUERY = "INTENT_FAST_QUERY"
    DEFAULT = "INTENT_DEFAULT"

@dataclass
class ModelCapability:
    """模型能力标签"""
    model_id: str
    name: str
    tags: List[str]  # deep_logic, long_review, cn_creative, video_gen, fast_cheap
    endpoint: Optional[str] = None
    api_key: Optional[str] = None

class BrainPool:
    """多AI模型大脑池"""

    # 意图路由表：意图 -> 能力标签
    ROUTING_TABLE: Dict[Intent, List[str]] = {
        Intent.ARCH_DESIGN: ["deep_logic"],
        Intent.CODE_REVIEW: ["long_review", "deep_logic"],  # 双审取共识
        Intent.CREATIVE: ["cn_creative"],
        Intent.VIDEO: ["video_gen"],
        Intent.FORMAT: ["fast_cheap"],
        Intent.FAST_QUERY: ["fast_cheap"],
        Intent.DEFAULT: ["deep_logic"],
    }

    def __init__(self):
        self.models: Dict[str, ModelCapability] = {}
        self.llm_clients: Dict[str, Callable] = {}
        logger.info("BrainPool模型池初始化")

    def register_model(self, model_id: str, name: str, tags: List[str],
                      endpoint: str = None, api_key: str = None) -> 'BrainPool':
        """注册模型"""
        self.models[model_id] = ModelCapability(
            model_id=model_id,
            name=name,
            tags=tags,
            endpoint=endpoint,
            api_key=api_key
        )
        logger.info(f"模型注册: {name} ({model_id}), 能力: {tags}")
        return self

    def register_client(self, model_id: str, client_fn: Callable) -> 'BrainPool':
        """注册LLM客户端"""
        self.llm_clients[model_id] = client_fn
        return self

    def route(self, intent: Intent) -> List[str]:
        """根据意图路由模型"""
        required_tags = self.ROUTING_TABLE.get(intent, self.ROUTING_TABLE[Intent.DEFAULT])
        matched_models = []

        for model_id, cap in self.models.items():
            if any(tag in cap.tags for tag in required_tags):
                matched_models.append(model_id)

        if not matched_models:
            # 回退到默认模型
            matched_models = list(self.models.keys())[:1]

        logger.debug(f"意图 {intent.value} -> 模型 {matched_models}")
        return matched_models

    async def call_single(self, model_id: str, prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """调用单个模型"""
        client = self.llm_clients.get(model_id)
        if client:
            try:
                result = await client(prompt, context or {})
                return {"model_id": model_id, "status": "success", "output": result}
            except Exception as e:
                logger.error(f"模型调用失败 {model_id}: {e}")
                return {"model_id": model_id, "status": "error", "error": str(e)}
        else:
            # 模拟调用
            return {
                "model_id": model_id,
                "status": "success",
                "output": f"[模拟输出 from {model_id}] {prompt[:50]}..."
            }

    async def call_consensus(self, intent: Intent, prompt: str, 
                            context: Dict[str, Any] = None) -> Dict[str, Any]:
        """并行调用多个模型，取共识"""
        model_ids = self.route(intent)

        if len(model_ids) == 1:
            return await self.call_single(model_ids[0], prompt, context)

        # 并行调用
        tasks = [self.call_single(mid, prompt, context) for mid in model_ids]
        results = await asyncio.gather(*tasks)

        # 简单共识：返回第一个成功的
        for r in results:
            if r.get("status") == "success":
                return r

        return {"status": "error", "error": "所有模型调用失败"}

    def get_best_model(self, intent: Intent) -> Optional[str]:
        """获取最优模型"""
        models = self.route(intent)
        return models[0] if models else None

    def list_models(self) -> List[Dict[str, Any]]:
        """列出所有注册模型"""
        return [
            {"model_id": m.model_id, "name": m.name, "tags": m.tags}
            for m in self.models.values()
        ]

# 全局实例
_brain_pool = None

def get_brain_pool() -> BrainPool:
    """获取BrainPool单例"""
    global _brain_pool
    if _brain_pool is None:
        _brain_pool = BrainPool()
        # 注册默认模型
        _brain_pool.register_model("deepseek-chat", "DeepSeek Chat", ["deep_logic", "fast_cheap"])
        _brain_pool.register_model("claude-3-sonnet", "Claude 3 Sonnet", ["long_review", "deep_logic"])
        _brain_pool.register_model("qwen-turbo", "通义千问", ["cn_creative", "fast_cheap"])
        _brain_pool.register_model("gemini-pro", "Gemini Pro", ["cn_creative", "video_gen"])
    return _brain_pool

# 测试
if __name__ == "__main__":
    pool = get_brain_pool()

    print("已注册模型:")
    for m in pool.list_models():
        print(f"  - {m['name']}: {m['tags']}")

    print("\n路由测试:")
    for intent in Intent:
        route = pool.route(intent)
        print(f"  {intent.value} -> {route}")

    print("\n共识调用测试:")
    result = asyncio.run(pool.call_consensus(Intent.CODE_REVIEW, "审查这段代码"))
    print(f"结果: {result['status']}")