"""
E/D/S/Q Architecture v2.0 - Stage 4: Full Integration
主架构类：集成所有模块
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable

from stage1_encoder_gate1 import EncoderLayer, Gate1Result
from stage2_ds_collaboration import DSCollaboration, DSCollaborationResult
from stage3_governance_gate3 import GovernancePipeline, GovernanceResult, InputType


class EDSQv2:
    """E/D/S/Q v2.0 - 完整架构集成"""
    
    def __init__(self):
        # 阶段 1: E + Gate1
        self.encoder = EncoderLayer()
        
        # 阶段 2: D/S 协作
        self.ds_collaboration = DSCollaboration()
        
        # 阶段 3: Q + Gate3
        self.governance = GovernancePipeline()
        
        # 状态
        self.calls_count = 0
        self.cache_hits = 0
        self.orchestrator_used_count = 0
    
    def register_experts(self, experts: Dict[str, Callable]):
        """注册专家"""
        self.ds_collaboration.register_experts(experts)
    
    def add_anchor(self, topic: str, truth: str):
        """添加锚点"""
        self.governance.add_anchor(topic, truth)
    
    def process(self, input_text: str) -> Dict[str, Any]:
        """处理输入 - 完整流程"""
        self.calls_count += 1
        
        result = {
            "success": False,
            "input": input_text,
            "timestamp": datetime.now().isoformat(),
            "stages": {}
        }
        
        try:
            # === 阶段 1: E 层 + Gate1 ===
            gate1_result, sanitized = self.encoder.encode(input_text)
            result["stages"]["encoder_gate1"] = {
                "allowed": gate1_result.allowed,
                "reason": gate1_result.reason,
                "category": gate1_result.structured_input.category.value,
                "cache_hit": gate1_result.cache_hit
            }
            
            if not gate1_result.allowed:
                result["success"] = False
                result["output"] = f"[BLOCKED by Gate1] {gate1_result.reason}"
                return result
            
            if gate1_result.cache_hit:
                self.cache_hits += 1
                cache_entry = self.encoder.get_cache(input_text)
                result["success"] = True
                result["output"] = cache_entry.output_text if cache_entry else "[CACHE ERROR]"
                return result
            
            # 确定输入类型
            category = gate1_result.structured_input.category
            input_type = self._map_to_input_type(category.value)
            
            # === 阶段 2: D/S 协作 ===
            ds_result = self.ds_collaboration.process(sanitized)
            result["stages"]["ds_collaboration"] = {
                "used_orchestrator": ds_result.used_orchestrator,
                "complexity": ds_result.complexity.value,
                "has_dispatch": ds_result.dispatch_task is not None,
                "has_orchestrator": ds_result.orchestrator_task is not None
            }
            
            if ds_result.used_orchestrator:
                self.orchestrator_used_count += 1
            
            # === 阶段 3: Q 治理 ===
            gov_result = self.governance.process(ds_result.final_result, input_type)
            result["stages"]["governance"] = {
                "passed": gov_result.passed,
                "pipeline": gov_result.gate3_result.pipeline_name,
                "check_count": len(gov_result.gate3_result.check_results)
            }
            
            if not gov_result.passed:
                result["success"] = False
                result["output"] = f"[BLOCKED by Governance] {gov_result.gate3_result.reason}"
                return result
            
            # === 成功 ===
            result["success"] = True
            result["output"] = gov_result.output_text
            
            # 放入缓存
            self.encoder.put_cache(input_text, result["output"])
            
        except Exception as e:
            result["success"] = False
            result["output"] = f"[SYSTEM ERROR] {str(e)}"
            result["error"] = str(e)
        
        return result
    
    def stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "calls_count": self.calls_count,
            "cache_hits": self.cache_hits,
            "orchestrator_used_count": self.orchestrator_used_count,
            "cache_hit_rate": (self.cache_hits / self.calls_count * 100) if self.calls_count > 0 else 0
        }
    
    def _map_to_input_type(self, category: str) -> InputType:
        """将分类映射到输入类型"""
        mapping = {
            "simple": InputType.SIMPLE,
            "complex": InputType.COMPLEX,
            "medical": InputType.MEDICAL,
            "chat": InputType.CHAT,
            "invalid": InputType.SIMPLE,
            "duplicate": InputType.SIMPLE
        }
        return mapping.get(category, InputType.SIMPLE)


# --- 快速测试 ---

def create_test_edsqv2() -> EDSQv2:
    """创建测试实例"""
    eds = EDSQv2()
    
    # 注册测试专家
    experts = {
        "medical_expert": (
            lambda text: f"医学咨询: {text} - 需要进一步分析",
            "处理医学相关问题",
            ["医疗", "健康", "症状", "医生"]
        ),
        "tech_expert": (
            lambda text: f"技术咨询: {text}",
            "处理技术相关问题",
            ["技术", "编程", "代码", "开发"]
        ),
        "general_expert": (
            lambda text: f"通用回答: {text}",
            "处理通用问题",
            ["一般", "通用", "其他"]
        )
    }
    eds.register_experts(experts)
    
    # 添加测试锚点
    eds.add_anchor("图灵测试", "图灵测试由艾伦·图灵于1950年提出")
    eds.add_anchor("医疗", "AI 不能诊断疾病，只能提供参考")
    
    return eds


def run_test_suite():
    """运行测试套件"""
    print("=" * 80)
    print("  E/D/S/Q v2.0 - 测试套件")
    print("=" * 80)
    
    eds = create_test_edsqv2()
    
    test_cases = [
        "什么是高血压？",
        "帮我写一个 Python 脚本",
        "今天天气怎么样？",
        "帮我设计一个系统架构，需要包含多个步骤",
        "什么是高血压？"  # 缓存命中测试
    ]
    
    print("\n--- 开始测试 ---\n")
    
    for i, test in enumerate(test_cases, 1):
        print(f"测试 {i}: {test[:60]}")
        result = eds.process(test)
        print(f"  成功: {result['success']}")
        print(f"  输出: {result['output'][:100]}")
        print(f"  阶段: {list(result['stages'].keys())}")
        print()
    
    print("\n--- 统计信息 ---")
    print(eds.stats())
    print()
    print("=" * 80)
    print("  测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    run_test_suite()

