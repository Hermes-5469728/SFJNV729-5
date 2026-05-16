"""
完整验证测试套件 - 测试事实校验引擎作为不可绕过的物理关卡
"""

import json
import sys
from datetime import datetime


class FullValidationTest:
    """完整验证测试套件"""
    
    def __init__(self):
        self.results = {
            "tests": [],
            "summary": {}
        }
    
    def _log_result(self, test_name, passed, message):
        """记录测试结果"""
        self.results["tests"].append({
            "test_name": test_name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def test_1_force_blocking(self):
        """测试1: 强制拦截 - 故意写入与锚点冲突的数据"""
        print("\n🔴 测试1: 强制拦截测试")
        print("-" * 50)
        
        try:
            from validator import AnchorValidator
            
            validator = AnchorValidator("00-DataCenter/anchor_db.json")
            
            # 测试用例：与已知锚点冲突的回答
            conflict_cases = [
                {
                    "query": "图灵测试是什么时候提出的?",
                    "response": "图灵测试是由艾伦·图灵于1960年提出的。",  # 错误：正确是1950年
                    "should_block": True
                },
                {
                    "query": "什么是AGI?",
                    "response": "AGI指能够通过图灵测试的人工智能系统。",  # 错误：定义不符
                    "should_block": True
                },
                {
                    "query": "什么是AGI?",
                    "response": "AGI指在几乎所有具有经济价值的工作上都能胜过人类的AI。",  # 正确
                    "should_block": False
                }
            ]
            
            all_passed = True
            for case in conflict_cases:
                result = validator.validate_response(case["query"], case["response"])
                
                is_blocked = result.status == "FAILED"
                expected_block = case["should_block"]
                
                if is_blocked == expected_block:
                    status = "✅"
                    passed = True
                else:
                    status = "❌"
                    passed = False
                    all_passed = False
                
                print(f"{status} 查询: {case['query'][:30]}...")
                print(f"   期望拦截: {expected_block}, 实际拦截: {is_blocked}")
                if hasattr(result, 'conflict_point'):
                    print(f"   冲突原因: {result.conflict_point}")
            
            self._log_result("强制拦截测试", all_passed, f"测试用例: {len(conflict_cases)}个, 通过: {sum(1 for c in conflict_cases if validator.validate_response(c['query'], c['response']).status == ('FAILED' if c['should_block'] else 'PASSED'))}个")
            return all_passed
        
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            self._log_result("强制拦截测试", False, str(e))
            return False
    
    def test_2_auto_validation(self):
        """测试2: 自动化验证 - 完整数据写入流程"""
        print("\n🟡 测试2: 自动化验证测试")
        print("-" * 50)
        
        try:
            from validator import AnchorValidator
            from anchor_schema import FactAnchor
            
            validator = AnchorValidator("00-DataCenter/anchor_db.json")
            
            # 模拟完整写入流程
            def write_anchor(topic, truth, source):
                """模拟写入锚点的完整流程"""
                # 1. 创建锚点对象
                anchor = FactAnchor(
                    id=f"test-{topic[:10]}",
                    topic=topic,
                    verified_truth=truth,
                    source=source,
                    confidence_score=1.0,
                    verified_at=datetime.now().strftime("%Y-%m-%d"),
                    tags=["test"]
                )
                
                # 2. 自动触发校验
                result = validator.validate_response(topic, truth)
                
                # 3. 根据校验结果决定是否写入
                if result.status == "FAILED":
                    print(f"❌ 写入被拦截: {topic}")
                    print(f"   冲突原因: {result.conflict_point}")
                    return False
                else:
                    print(f"✅ 写入通过: {topic}")
                    # 实际写入逻辑（此处仅模拟）
                    return True
            
            # 测试写入
            test_cases = [
                ("测试-正确锚点", "Python是一种高级编程语言。", "test"),
                ("图灵测试", "图灵测试是由艾伦·图灵于1960年提出的。", "test"),  # 冲突
                ("测试-新主题", "这是一个全新的事实陈述，与现有锚点不冲突。", "test")
            ]
            
            passed = 0
            for topic, truth, source in test_cases:
                if write_anchor(topic, truth, source):
                    passed += 1
            
            all_passed = passed == 2  # 期望2个通过，1个被拦截
            
            self._log_result("自动化验证测试", all_passed, f"测试用例: {len(test_cases)}个, 通过: {passed}个")
            return all_passed
        
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            self._log_result("自动化验证测试", False, str(e))
            return False
    
    def test_3_backward_validation(self):
        """测试3: 回溯校验 - 对已有数据进行一致性扫描"""
        print("\n🟢 测试3: 回溯校验测试")
        print("-" * 50)
        
        try:
            from simple_anchor_engine import AnchorEngine
            
            engine = AnchorEngine("00-DataCenter/anchor_db.json")
            result = engine.run_backward_conflict_detection()
            
            # 检查是否有冲突
            conflict_count = len(result["conflicts"])
            
            print(f"已检测锚点: {result['stats']['total_anchors']}")
            print(f"检测配对: {result['stats']['checked_pairs']}")
            print(f"发现冲突: {conflict_count}")
            
            # 对于回溯测试，我们期望没有冲突（或者冲突率很低）
            # 这里我们记录结果，但不判定失败，因为已有数据可能存在历史冲突
            all_passed = conflict_count == 0
            
            self._log_result("回溯校验测试", all_passed, f"锚点总数: {result['stats']['total_anchors']}, 冲突数: {conflict_count}, 冲突率: {result['stats']['conflict_rate']:.2%}")
            return all_passed
        
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            self._log_result("回溯校验测试", False, str(e))
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("    🧪 完整验证测试套件")
        print("=" * 60)
        print(f"测试开始时间: {datetime.now().isoformat()}")
        
        results = []
        results.append(self.test_1_force_blocking())
        results.append(self.test_2_auto_validation())
        results.append(self.test_3_backward_validation())
        
        # 生成总结
        passed = sum(results)
        total = len(results)
        
        print("\n" + "=" * 60)
        print("    📊 测试结果汇总")
        print("=" * 60)
        print(f"测试总数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {total - passed}")
        print(f"通过率: {passed / total * 100:.1f}%")
        print("=" * 60)
        
        # 保存测试报告
        self.results["summary"] = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total,
            "timestamp": datetime.now().isoformat()
        }
        
        with open("validation_test_report.json", 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print("\n📄 测试报告已保存到: validation_test_report.json")
        
        return all(results)


if __name__ == "__main__":
    test_suite = FullValidationTest()
    success = test_suite.run_all_tests()
    sys.exit(0 if success else 1)