"""
State Machine Engine - 状态机编排引擎
不使用 LangGraph，纯 Python 标准库实现

功能：
- 节点编排与状态管理
- Checkpoint 持久化（崩溃恢复）
- 条件边路由（PASS/FAIL）
"""

import json
import os
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

@dataclass
class NodeResult:
    """节点执行结果"""
    status: str  # PASS, FAIL, RUNNING
    output: Any = None
    error: Optional[str] = None
    retry_hint: Optional[str] = None

@dataclass
class Node:
    """状态机节点定义"""
    name: str
    execute: Callable[[Dict[str, Any]], NodeResult]
    validator: Optional[Callable[[Any], NodeResult]] = None
    rollback_node: Optional[str] = None  # 失败时回退的节点名

@dataclass
class State:
    """状态机状态"""
    current_node: str
    context: Dict[str, Any]
    history: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "RUNNING"  # RUNNING, COMPLETED, FAILED

class StateMachine:
    """状态机编排引擎"""

    def __init__(self, name: str, checkpoint_dir: str = ".checkpoints"):
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.start_node: Optional[str] = None
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_file = os.path.join(checkpoint_dir, f"{name}.json")
        os.makedirs(checkpoint_dir, exist_ok=True)
        logger.info(f"状态机引擎初始化: {name}")

    def add_node(self, name: str, execute: Callable, validator: Callable = None, 
                 rollback_node: str = None) -> 'StateMachine':
        """添加节点"""
        self.nodes[name] = Node(
            name=name,
            execute=execute,
            validator=validator,
            rollback_node=rollback_node
        )
        if self.start_node is None:
            self.start_node = name
        return self

    def set_start_node(self, name: str):
        """设置起始节点"""
        self.start_node = name

    def save_checkpoint(self, state: State):
        """保存检查点"""
        checkpoint = {
            "machine_name": self.name,
            "timestamp": datetime.now().isoformat(),
            "current_node": state.current_node,
            "context": state.context,
            "history": state.history,
            "status": state.status
        }
        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
        logger.debug(f"检查点已保存: {state.current_node}")

    def load_checkpoint(self) -> Optional[State]:
        """加载检查点"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                state = State(
                    current_node=checkpoint['current_node'],
                    context=checkpoint['context'],
                    history=checkpoint.get('history', []),
                    status=checkpoint['status']
                )
                logger.info(f"从检查点恢复: {state.current_node}")
                return state
            except Exception as e:
                logger.error(f"加载检查点失败: {e}")
        return None

    def clear_checkpoint(self):
        """清除检查点"""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
            logger.info("检查点已清除")

    def run(self, initial_context: Dict[str, Any]) -> State:
        """运行状态机"""
        # 尝试从检查点恢复
        state = self.load_checkpoint()
        if state is None:
            state = State(
                current_node=self.start_node,
                context=initial_context,
                history=[],
                status="RUNNING"
            )

        logger.info(f"[状态机启动] 起始节点: {state.current_node}")

        while state.status == "RUNNING":
            current_node = self.nodes.get(state.current_node)
            if current_node is None:
                state.status = "FAILED"
                state.context['error'] = f"节点不存在: {state.current_node}"
                break

            # 执行节点
            logger.info(f"[执行节点] {current_node.name}")
            try:
                result = current_node.execute(state.context)
            except Exception as e:
                logger.error(f"节点执行异常: {e}")
                result = NodeResult(status="FAIL", error=str(e))

            # 记录历史
            state.history.append({
                "node": current_node.name,
                "timestamp": datetime.now().isoformat(),
                "status": result.status,
                "output": str(result.output)[:200] if result.output else None
            })

            if result.status == "FAIL":
                if current_node.rollback_node:
                    logger.warning(f"[节点失败] 回退到: {current_node.rollback_node}")
                    state.current_node = current_node.rollback_node
                else:
                    state.status = "FAILED"
                    state.context['error'] = result.error
                    break

            elif result.status == "PASS":
                # 执行验证器
                if current_node.validator and result.output:
                    try:
                        validator_result = current_node.validator(result.output)
                        if validator_result.status == "FAIL":
                            logger.warning(f"[验证失败] {validator_result.retry_hint}")
                            if current_node.rollback_node:
                                state.current_node = current_node.rollback_node
                            else:
                                state.status = "FAILED"
                                break
                        else:
                            state.context['output'] = result.output
                            state.current_node = result.output.get('next_node', self._get_next_node(current_node.name))
                    except Exception as e:
                        logger.error(f"验证器执行异常: {e}")
                        state.current_node = self._get_next_node(current_node.name)
                else:
                    state.context['output'] = result.output
                    state.current_node = self._get_next_node(current_node.name)

            # 保存检查点
            self.save_checkpoint(state)

            # 检查是否结束
            if state.current_node not in self.nodes:
                state.status = "COMPLETED"
                logger.info(f"[状态机完成] 最终节点: {state.current_node}")

        self.clear_checkpoint()
        return state

    def _get_next_node(self, current_name: str) -> Optional[str]:
        """获取下一个节点（按添加顺序）"""
        node_names = list(self.nodes.keys())
        try:
            idx = node_names.index(current_name)
            return node_names[idx + 1] if idx + 1 < len(node_names) else None
        except ValueError:
            return None

# 测试
if __name__ == "__main__":
    def mock_generate(context: Dict) -> NodeResult:
        return NodeResult(status="PASS", output={"next_node": "validate", "content": "生成的代码"})

    def mock_validate(content: Any) -> NodeResult:
        if len(content.get('content', '')) > 5:
            return NodeResult(status="PASS")
        return NodeResult(status="FAIL", retry_hint="内容太短")

    machine = StateMachine("code_generation")
    machine.add_node("generate", mock_generate, mock_validate)
    machine.add_node("validate", lambda c: NodeResult(status="PASS", output={}))
    machine.set_start_node("generate")

    result = machine.run({"task": "创建函数"})
    print(f"最终状态: {result.status}")
    print(f"历史: {len(result.history)} 步")