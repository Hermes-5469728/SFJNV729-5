"""LLM路由策略 - 关键路径与非关键路径隔离"""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from pydantic import BaseModel, field_validator
from enum import Enum
import json
from pathlib import Path


class LLMProvider(str, Enum):
    """LLM提供商枚举"""
    OLLAMA = "ollama"
    DASHSCOPE = "dashscope"
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMRouteType(str, Enum):
    """路由类型枚举"""
    CRITICAL = "critical"  # 关键路径 - 必须走云端
    NON_CRITICAL = "non_critical"  # 非关键路径 - 强制走本地
    FLEXIBLE = "flexible"  # 灵活路由 - 根据配置选择


class LLMModulePolicy(BaseModel):
    """模块级LLM策略"""
    module_name: str  # 模块名称
    allowed_providers: List[LLMProvider]  # 允许的提供商
    default_provider: LLMProvider  # 默认提供商
    route_type: LLMRouteType  # 路由类型
    rate_limit: Optional[int] = None  # 速率限制（请求/分钟）
    timeout: int = 30  # 超时时间（秒）


class LLMRouteConfig(BaseModel):
    """LLM路由配置"""
    # 全局设置
    default_route_type: LLMRouteType = LLMRouteType.FLEXIBLE
    enable_local_only_mode: bool = False  # 本地优先模式
    
    # 关键路径配置
    critical_path_providers: List[LLMProvider] = [
        LLMProvider.DASHSCOPE,
        LLMProvider.DEEPSEEK
    ]
    
    # 非关键路径配置
    non_critical_path_providers: List[LLMProvider] = [
        LLMProvider.OLLAMA
    ]
    
    # 模块级策略
    module_policies: List[LLMModulePolicy] = []
    
    # 降级策略
    enable_fallback: bool = True  # 启用降级
    fallback_order: List[LLMProvider] = [
        LLMProvider.DASHSCOPE,
        LLMProvider.DEEPSEEK,
        LLMProvider.OLLAMA
    ]
    
    # 成本控制
    max_daily_cost: Optional[float] = None  # 每日最大成本（元）
    cost_per_token: Dict[LLMProvider, float] = {
        LLMProvider.DASHSCOPE: 0.000002,
        LLMProvider.DEEPSEEK: 0.0000015,
        LLMProvider.OLLAMA: 0.0  # 本地无成本
    }


class LLMRequestContext(BaseModel):
    """LLM请求上下文"""
    module_name: str  # 发起请求的模块
    task_type: str  # 任务类型
    priority: str = "normal"  # high/normal/low
    is_streaming: bool = False  # 是否流式输出
    required_features: List[str] = []  # 所需特性
    estimated_tokens: Optional[int] = None  # 预估token数


class LLMRouteResult(BaseModel):
    """路由结果"""
    provider: LLMProvider
    route_type: LLMRouteType
    reason: str
    fallback_used: bool = False
    cost_estimate: Optional[float] = None


class LLMRouter:
    """LLM路由管理器"""
    
    def __init__(self, config_path: str = "config/llm_router.json"):
        self.config_path = Path(config_path)
        self.config = LLMRouteConfig()
        self._load_config()
        self._init_default_policies()
        
        # 运行时状态
        self.daily_cost = 0.0
        self.today_date = datetime.now().date()
        self.request_count = {}  # {provider: count}
    
    def _load_config(self):
        """加载配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.config = LLMRouteConfig(**data)
    
    def save_config(self):
        """保存配置"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config.dict(), f, ensure_ascii=False, indent=2)
    
    def _init_default_policies(self):
        """初始化默认模块策略"""
        if not self.config.module_policies:
            policies = [
                # 医疗模块 - 关键路径，禁止本地
                LLMModulePolicy(
                    module_name="medical",
                    allowed_providers=[LLMProvider.DASHSCOPE, LLMProvider.DEEPSEEK],
                    default_provider=LLMProvider.DASHSCOPE,
                    route_type=LLMRouteType.CRITICAL,
                    rate_limit=60,
                    timeout=60
                ),
                
                # 决策中心模块 - 关键路径
                LLMModulePolicy(
                    module_name="ac_decision",
                    allowed_providers=[LLMProvider.DASHSCOPE, LLMProvider.DEEPSEEK],
                    default_provider=LLMProvider.DASHSCOPE,
                    route_type=LLMRouteType.CRITICAL,
                    rate_limit=120,
                    timeout=30
                ),
                
                # 个人助手模块 - 非关键路径，强制本地
                LLMModulePolicy(
                    module_name="personal",
                    allowed_providers=[LLMProvider.OLLAMA],
                    default_provider=LLMProvider.OLLAMA,
                    route_type=LLMRouteType.NON_CRITICAL,
                    rate_limit=200,
                    timeout=30
                ),
                
                # 文档生成模块 - 非关键路径
                LLMModulePolicy(
                    module_name="documentation",
                    allowed_providers=[LLMProvider.OLLAMA],
                    default_provider=LLMProvider.OLLAMA,
                    route_type=LLMRouteType.NON_CRITICAL,
                    rate_limit=100,
                    timeout=60
                ),
                
                # 代码生成模块 - 灵活路由
                LLMModulePolicy(
                    module_name="code_generation",
                    allowed_providers=[LLMProvider.OLLAMA, LLMProvider.DASHSCOPE],
                    default_provider=LLMProvider.OLLAMA,
                    route_type=LLMRouteType.FLEXIBLE,
                    rate_limit=80,
                    timeout=60
                ),
                
                # 测试模块 - 非关键路径
                LLMModulePolicy(
                    module_name="testing",
                    allowed_providers=[LLMProvider.OLLAMA],
                    default_provider=LLMProvider.OLLAMA,
                    route_type=LLMRouteType.NON_CRITICAL,
                    rate_limit=50,
                    timeout=30
                ),
                
                # 防御模块 - 关键路径
                LLMModulePolicy(
                    module_name="defense",
                    allowed_providers=[LLMProvider.DASHSCOPE, LLMProvider.DEEPSEEK],
                    default_provider=LLMProvider.DASHSCOPE,
                    route_type=LLMRouteType.CRITICAL,
                    rate_limit=30,
                    timeout=30
                )
            ]
            self.config.module_policies = policies
            self.save_config()
    
    def get_module_policy(self, module_name: str) -> Optional[LLMModulePolicy]:
        """获取模块策略"""
        return next(
            (p for p in self.config.module_policies 
             if p.module_name == module_name),
            None
        )
    
    def _determine_route_type(self, context: LLMRequestContext) -> LLMRouteType:
        """确定路由类型"""
        # 首先检查模块级策略
        policy = self.get_module_policy(context.module_name)
        if policy:
            return policy.route_type
        
        # 根据任务类型判断
        critical_tasks = [
            "clinical_decision",
            "medical_analysis",
            "security_review",
            "architecture_design",
            "complex_analysis"
        ]
        
        non_critical_tasks = [
            "draft_generation",
            "content_completion",
            "simple_query",
            "formatting",
            "documentation"
        ]
        
        if context.task_type in critical_tasks:
            return LLMRouteType.CRITICAL
        elif context.task_type in non_critical_tasks:
            return LLMRouteType.NON_CRITICAL
        
        return self.config.default_route_type
    
    def _select_provider(self, route_type: LLMRouteType, context: LLMRequestContext) -> LLMProvider:
        """选择LLM提供商"""
        policy = self.get_module_policy(context.module_name)
        
        # 本地优先模式
        if self.config.enable_local_only_mode:
            if LLMProvider.OLLAMA in (policy.allowed_providers if policy else []):
                return LLMProvider.OLLAMA
            else:
                # 模块不允许本地，但全局强制本地模式
                return LLMProvider.OLLAMA
        
        # 根据路由类型选择
        if route_type == LLMRouteType.CRITICAL:
            # 关键路径：从关键提供商列表中选择
            providers = [p for p in self.config.critical_path_providers
                        if (policy is None or p in policy.allowed_providers)]
            if providers:
                return providers[0]
            raise ValueError("关键路径没有可用的提供商")
        
        elif route_type == LLMRouteType.NON_CRITICAL:
            # 非关键路径：强制走本地
            if LLMProvider.OLLAMA in (policy.allowed_providers if policy else []):
                return LLMProvider.OLLAMA
            raise ValueError("非关键路径模块不允许使用本地Ollama")
        
        else:
            # 灵活路由：根据优先级选择
            if policy:
                return policy.default_provider
            return self.config.fallback_order[0]
    
    def _check_cost_limit(self, provider: LLMProvider, tokens: int) -> bool:
        """检查成本限制"""
        if self.config.max_daily_cost is None:
            return True
        
        # 检查日期是否变化
        today = datetime.now().date()
        if today != self.today_date:
            self.daily_cost = 0.0
            self.today_date = today
        
        # 计算成本
        cost_per_token = self.config.cost_per_token.get(provider, 0.0)
        estimated_cost = tokens * cost_per_token
        
        if self.daily_cost + estimated_cost > self.config.max_daily_cost:
            return False
        
        return True
    
    def route(self, context: LLMRequestContext) -> LLMRouteResult:
        """执行路由决策"""
        # 确定路由类型
        route_type = self._determine_route_type(context)
        
        # 选择提供商
        try:
            provider = self._select_provider(route_type, context)
        except ValueError as e:
            return LLMRouteResult(
                provider=LLMProvider.OLLAMA,  # 默认回退到本地
                route_type=route_type,
                reason=str(e),
                fallback_used=True
            )
        
        # 检查成本限制
        if context.estimated_tokens:
            if not self._check_cost_limit(provider, context.estimated_tokens):
                # 成本超限，降级到本地
                if LLMProvider.OLLAMA in (p.allowed_providers for p in self.config.module_policies 
                                        if p.module_name == context.module_name):
                    return LLMRouteResult(
                        provider=LLMProvider.OLLAMA,
                        route_type=LLMRouteType.NON_CRITICAL,
                        reason="成本超限，降级到本地Ollama",
                        fallback_used=True,
                        cost_estimate=0.0
                    )
        
        # 记录请求
        self.request_count[provider] = self.request_count.get(provider, 0) + 1
        
        # 计算成本预估
        cost_estimate = None
        if context.estimated_tokens:
            cost_per_token = self.config.cost_per_token.get(provider, 0.0)
            cost_estimate = context.estimated_tokens * cost_per_token
        
        return LLMRouteResult(
            provider=provider,
            route_type=route_type,
            reason=self._get_route_reason(provider, route_type, context),
            fallback_used=False,
            cost_estimate=cost_estimate
        )
    
    def _get_route_reason(self, provider: LLMProvider, route_type: LLMRouteType, context: LLMRequestContext) -> str:
        """生成路由原因"""
        reasons = []
        
        if route_type == LLMRouteType.CRITICAL:
            reasons.append("关键路径任务")
        elif route_type == LLMRouteType.NON_CRITICAL:
            reasons.append("非关键路径任务，强制本地")
        
        policy = self.get_module_policy(context.module_name)
        if policy:
            reasons.append(f"模块[{context.module_name}]策略限制")
        
        if provider == LLMProvider.OLLAMA:
            reasons.append("使用本地Ollama")
        else:
            reasons.append(f"使用云端{provider.value}")
        
        return "; ".join(reasons)
    
    def enforce_module_restrictions(self, module_name: str, provider: LLMProvider) -> bool:
        """强制执行模块级限制"""
        policy = self.get_module_policy(module_name)
        if not policy:
            return True
        
        if provider not in policy.allowed_providers:
            return False
        
        return True
    
    def get_route_statistics(self) -> Dict[str, Any]:
        """获取路由统计"""
        return {
            "request_count": self.request_count,
            "daily_cost": self.daily_cost,
            "local_requests": self.request_count.get(LLMProvider.OLLAMA, 0),
            "cloud_requests": sum(
                count for provider, count in self.request_count.items()
                if provider != LLMProvider.OLLAMA
            )
        }
    
    def get_module_policy_summary(self) -> List[Dict[str, Any]]:
        """获取模块策略摘要"""
        summary = []
        for policy in self.config.module_policies:
            summary.append({
                "module_name": policy.module_name,
                "route_type": policy.route_type.value,
                "default_provider": policy.default_provider.value,
                "allowed_providers": [p.value for p in policy.allowed_providers],
                "rate_limit": policy.rate_limit,
                "timeout": policy.timeout
            })
        return summary


# 路由策略可视化
def get_route_strategy_diagram() -> str:
    """生成路由策略图"""
    return """
```mermaid
flowchart TD
    subgraph 请求入口
        A[LLM请求]
    end
    
    subgraph 路由决策
        B{路由类型}
        C[关键路径]
        D[非关键路径]
        E[灵活路由]
    end
    
    subgraph 提供商选择
        F[云端LLM]
        G[本地Ollama]
    end
    
    subgraph 模块限制
        H[医疗/决策/防御]
        I[个人/文档/测试]
        J[代码生成]
    end
    
    A --> B
    B -->|Critical| C --> F
    B -->|Non-Critical| D --> G
    B -->|Flexible| E
    
    E --> H --> F
    E --> I --> G
    E --> J --> G
    
    F -->|降级| G
    G -->|成本超限| G
```
"""


# 示例使用
if __name__ == "__main__":
    router = LLMRouter()
    
    # 测试医疗模块请求（关键路径）
    context1 = LLMRequestContext(
        module_name="medical",
        task_type="clinical_decision",
        priority="high"
    )
    result1 = router.route(context1)
    print(f"医疗模块路由结果: {result1.dict()}")
    
    # 测试个人助手请求（非关键路径）
    context2 = LLMRequestContext(
        module_name="personal",
        task_type="content_completion",
        priority="normal"
    )
    result2 = router.route(context2)
    print(f"个人助手路由结果: {result2.dict()}")
    
    # 获取统计
    print(f"\n路由统计: {router.get_route_statistics()}")
    
    # 获取策略摘要
    print("\n模块策略摘要:")
    for policy in router.get_module_policy_summary():
        print(policy)
