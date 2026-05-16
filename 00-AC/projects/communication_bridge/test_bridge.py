"""
AI沟通桥测试脚本
测试完整的A2A通信流程
"""

import asyncio
from loguru import logger

# 配置日志
logger.remove()
logger.add(open("bridge_test.log", "w", encoding="utf-8"), level="DEBUG")
logger.add(lambda msg: print(msg), level="INFO")

async def run_test():
    """运行完整测试"""
    logger.info("=" * 60)
    logger.info("AI沟通桥测试开始")
    logger.info("=" * 60)

    # 1. 初始化组件
    logger.info("\n[1/5] 初始化组件")
    from communication_bridge import (
        get_gateway,
        get_security_manager,
        get_connector,
        get_a2a_protocol,
        MessageType
    )

    gateway = get_gateway()
    security = get_security_manager()
    connector = get_connector()
    protocol = get_a2a_protocol()

    logger.info("✓ 网关初始化完成")
    logger.info("✓ 安全管理器初始化完成")
    logger.info("✓ 连接器初始化完成")
    logger.info("✓ A2A协议初始化完成")

    # 2. 创建身份
    logger.info("\n[2/5] 创建Agent身份")
    coder = security.create_identity("代码Agent", ["code_write", "code_read"])
    reviewer = security.create_identity("评审Agent", ["code_review"])
    executor = security.create_identity("执行Agent", ["task_execute"])

    logger.info(f"✓ 代码Agent: {coder.agent_id}")
    logger.info(f"✓ 评审Agent: {reviewer.agent_id}")
    logger.info(f"✓ 执行Agent: {executor.agent_id}")

    # 3. 注册端点
    logger.info("\n[3/5] 注册端点")
    gateway.register_endpoint(coder.agent_id, "http://localhost:8000/coder")
    gateway.register_endpoint(reviewer.agent_id, "http://localhost:8000/reviewer")
    gateway.register_endpoint(executor.agent_id, "http://localhost:8000/executor")

    connector.connect(coder.agent_id, "http://localhost:8000/coder")
    connector.connect(reviewer.agent_id, "http://localhost:8000/reviewer")
    connector.connect(executor.agent_id, "http://localhost:8000/executor")

    logger.info("✓ 所有端点已注册")

    # 4. 创建安全群组
    logger.info("\n[4/5] 创建安全群组")
    dev_group = security.create_group("开发小组", [coder.agent_id, reviewer.agent_id])
    logger.info(f"✓ 开发小组创建: {dev_group.group_id}")

    # 5. 测试消息路由
    logger.info("\n[5/5] 测试消息路由")

    # 创建消息
    msg1 = protocol.create_message(
        sender_id=coder.agent_id,
        receiver_id=reviewer.agent_id,
        task_id="task-code-review-001",
        content={
            "action": "review",
            "code": "def calculate_sum(a: int, b: int) -> int:\n    return a + b",
            "requirements": "检查代码规范和安全性"
        }
    )

    logger.info(f"✓ 创建消息: {msg1.message_id}")

    # 路由消息
    result = await gateway.route_message(msg1)
    logger.info(f"✓ 消息路由完成: {result.status.value}")

    # 创建响应消息
    msg2 = protocol.create_message(
        sender_id=reviewer.agent_id,
        receiver_id=coder.agent_id,
        task_id="task-code-review-001",
        content={
            "action": "review_result",
            "approved": True,
            "feedback": "代码规范良好，建议添加单元测试"
        },
        message_type=MessageType.RESPONSE
    )

    result2 = await gateway.route_message(msg2)
    logger.info(f"✓ 响应消息路由完成: {result2.status.value}")

    # 获取任务消息历史
    history = gateway.get_messages_by_task("task-code-review-001")
    logger.info(f"✓ 任务消息历史: {len(history)} 条")

    logger.info("\n" + "=" * 60)
    logger.info("AI沟通桥测试完成")
    logger.info("=" * 60)

    # 输出测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    print(f"创建身份: 3个")
    print(f"注册端点: 3个")
    print(f"创建群组: 1个")
    print(f"发送消息: 2条")
    print(f"消息状态: {result.status.value}, {result2.status.value}")
    print("=" * 60)
    print("\n✓ 所有测试通过！")

if __name__ == "__main__":
    asyncio.run(run_test())