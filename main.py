"""
元认知校准系统 - 主程序
集成生成器、校准器和记录器，实现完整的认知校准流程
"""

import json
from datetime import datetime
from typing import Optional
from validator import AnchorValidator
from metrics_logger import MetricsLogger, MetricsRecord
from anchor_schema import DeviationReport


class MetacognitionCalibrator:
    """
    元认知校准器 - 给AI大脑装一个"前额叶皮层"
    
    流程: 用户输入 → AI生成(草稿) → 校验 → 通过/重写 → 输出
    """
    
    def __init__(self):
        self.validator = AnchorValidator()
        self.logger = MetricsLogger()
    
    def _generate_initial_response(self, user_query: str) -> str:
        """
        模拟AI生成初步回答
        实际应用中替换为真实的LLM调用
        """
        responses = {
            "什么是AGI?": "AGI指在几乎所有具有经济价值的工作上都能胜过人类的AI。",
            "图灵测试是什么时候提出的?": "图灵测试是由艾伦·图灵于1960年提出的。",  # 故意错误
            "什么是AC无效反思?": "AC无效反思0.5层指模型知道自己可能错了，但因为没有外部参照系，只能在错误的逻辑闭环里打转。",
            "什么是五阶段主循环?": "任务执行的五阶段主循环：PLAN、EXECUTE、VERIFY、RESOLVE、LOG。",
            "Schema版本校验规则是什么?": "操作数据库前必须先校验schema版本，不匹配时必须走migration脚本。"
        }
        
        # 如果有预设回答则返回，否则返回一个通用回答
        return responses.get(user_query, f"这是关于'{user_query}'的初步回答。")
    
    def _rewrite_with_anchor(self, user_query: str, deviation_report: DeviationReport) -> str:
        """
        根据偏差报告和锚点重写回答
        
        Args:
            user_query: 用户原始查询
            deviation_report: 偏差报告
            
        Returns:
            重写后的回答（注明已根据事实锚点修正）
        """
        if not deviation_report.conflicting_anchor:
            return f"⚠️ 无法完成重写：缺少冲突锚点信息。"
        
        anchor = deviation_report.conflicting_anchor
        
        rewritten = f"""
根据事实锚点修正后的回答：

【主题】{anchor.topic}

【修正依据】{anchor.source}

【正确信息】{anchor.verified_truth}

【修正说明】
原回答存在偏差（偏差率: {deviation_report.deviation_score:.2%}），已根据事实锚点进行修正。

【回答】{anchor.verified_truth}
"""
        return rewritten.strip()
    
    def _classify_question_type(self, query: str) -> str:
        """分类问题类型"""
        query_lower = query.lower()
        
        if "什么是" in query_lower or "定义" in query_lower or "指的是" in query_lower:
            return "definition"
        elif "什么时候" in query_lower or "哪一年" in query_lower or "时间" in query_lower:
            return "temporal"
        elif "如何" in query_lower or "怎么" in query_lower or "方法" in query_lower:
            return "method"
        elif "为什么" in query_lower or "原因" in query_lower:
            return "reason"
        elif "是否" in query_lower or "对吗" in query_lower or "正确" in query_lower:
            return "verification"
        else:
            return "general"
    
    def process_query(self, user_query: str, simulate_error: bool = False) -> str:
        """
        处理用户查询的完整流程
        
        Args:
            user_query: 用户提问
            simulate_error: 是否模拟错误回答（用于测试）
            
        Returns:
            最终回答
        """
        print(f"\n🤔 用户提问: {user_query}")
        
        # 1. AI生成初步回答
        print("  → 生成器: 正在生成初步回答...")
        initial_response = self._generate_initial_response(user_query)
        
        # 测试模式：模拟错误回答
        if simulate_error:
            initial_response = "这是一个故意错误的回答，用来测试偏差检测。"
        
        print(f"  → 草稿回答: {initial_response[:50]}...")
        
        # 2. 调用校准器检查
        print("  → 校准器: 正在进行事实锚点校验...")
        validation_result = self.validator.validate_response(user_query, initial_response)
        
        # 3. 判断是否触发锚点
        triggered_anchor = len(validation_result.matched_anchors) > 0 if hasattr(validation_result, 'matched_anchors') else False
        deviation_rate = validation_result.deviation_score if hasattr(validation_result, 'deviation_score') else 0.0
        rewrote = False
        final_response = initial_response
        final_deviation = deviation_rate
        anchor_topic = None
        
        # 4. 处理校验结果
        if isinstance(validation_result, DeviationReport):
            # 校验失败 - 需要重写
            print(f"  ❌ 校验失败: {validation_result.conflict_point}")
            print(f"  → 偏差率: {validation_result.deviation_score:.2%}")
            
            # 记录冲突的锚点主题
            if validation_result.conflicting_anchor:
                anchor_topic = validation_result.conflicting_anchor.topic
            
            # 强制重写
            print("  → 正在根据事实锚点重写...")
            final_response = self._rewrite_with_anchor(user_query, validation_result)
            rewrote = True
            final_deviation = 0.0  # 重写后偏差率为0
        else:
            # 校验通过
            print(f"  ✅ 校验通过")
            if triggered_anchor:
                matched_topics = [a.topic for a in validation_result.matched_anchors]
                anchor_topic = ", ".join(matched_topics)
        
        # 5. 记录指标
        record = MetricsRecord(
            timestamp=datetime.now().isoformat(),
            question_type=self._classify_question_type(user_query),
            triggered_anchor=triggered_anchor,
            initial_deviation_rate=deviation_rate,
            rewrote=rewrote,
            final_deviation_rate=final_deviation,
            query=user_query,
            anchor_topic=anchor_topic
        )
        self.logger.log_record(record)
        
        # 6. 输出最终结果
        print(f"\n📝 最终回答:\n{final_response}")
        
        if rewrote:
            print("\n⚠️ 注：此回答已根据事实锚点进行修正")
        
        return final_response
    
    def run_demo(self):
        """运行演示模式"""
        print("=" * 60)
        print("    🧠 元认知校准系统 - 演示模式")
        print("=" * 60)
        print("""
系统流程：
1. 用户输入 → 2. AI生成草稿 → 3. 事实锚点校验 → 4. 通过/重写 → 5. 输出

按 Ctrl+C 退出
""")
        print("=" * 60)
        
        while True:
            try:
                user_query = input("\n请输入问题: ")
                if not user_query.strip():
                    continue
                
                self.process_query(user_query)
                
                # 打印当前系统可信度评分
                print("\n--- 系统状态 ---")
                self.logger.print_summary()
                
            except KeyboardInterrupt:
                print("\n\n👋 退出演示模式")
                break


# 命令行入口
if __name__ == "__main__":
    calibrator = MetacognitionCalibrator()
    calibrator.run_demo()