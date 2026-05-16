"""状态机验证测试脚本"""

import sys
from pathlib import Path

CLI_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CLI_DIR))

from ac.orchestrator import StateMachine, TaskState, InvalidStateTransition

def test_state_machine():
    """测试状态机严格化"""
    state_machine = StateMachine()
    
    print("=== 状态机验证测试 ===")
    print()
    
    # 测试合法转换
    print("1. 测试合法状态转换:")
    test_cases = [
        (TaskState.CREATED, TaskState.QUEUED, "CREATED -> QUEUED"),
        (TaskState.QUEUED, TaskState.EXECUTING, "QUEUED -> EXECUTING"),
        (TaskState.EXECUTING, TaskState.VERIFYING, "EXECUTING -> VERIFYING"),
        (TaskState.VERIFYING, TaskState.VERIFIED, "VERIFYING -> VERIFIED"),
        (TaskState.VERIFIED, TaskState.COMPLETED, "VERIFIED -> COMPLETED"),
    ]
    
    for current, next_state, desc in test_cases:
        try:
            result = state_machine.transition(current, next_state)
            print(f"   ✅ {desc}: 成功")
        except InvalidStateTransition as e:
            print(f"   ❌ {desc}: 失败 - {e}")
    
    print()
    print("2. 测试非法状态转换:")
    illegal_cases = [
        (TaskState.CREATED, TaskState.EXECUTING, "CREATED -> EXECUTING (跳过QUEUED)"),
        (TaskState.COMPLETED, TaskState.EXECUTING, "COMPLETED -> EXECUTING (终态不允许转换)"),
        (TaskState.VERIFIED, TaskState.QUEUED, "VERIFIED -> QUEUED (只能到COMPLETED)"),
        (TaskState.FAILED, TaskState.COMPLETED, "FAILED -> COMPLETED (必须先回滚)"),
    ]
    
    for current, next_state, desc in illegal_cases:
        try:
            result = state_machine.transition(current, next_state)
            print(f"   ❌ {desc}: 应该失败但成功了")
        except InvalidStateTransition as e:
            print(f"   ✅ {desc}: 正确拦截 - {e}")
    
    print()
    print("3. 测试can_transition方法:")
    print(f"   can_transition(CREATED, QUEUED): {state_machine.can_transition(TaskState.CREATED, TaskState.QUEUED)}")
    print(f"   can_transition(CREATED, EXECUTING): {state_machine.can_transition(TaskState.CREATED, TaskState.EXECUTING)}")
    print(f"   is_terminal(COMPLETED): {state_machine.is_terminal(TaskState.COMPLETED)}")
    print(f"   is_terminal(EXECUTING): {state_machine.is_terminal(TaskState.EXECUTING)}")
    
    print()
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_state_machine()