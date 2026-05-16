class TaskPlanner:
    def decompose(self, task: str) -> list:
        return [
            f"[Plan] 分析需求: {task[:60]}",
            f"[Plan] 检索相关知识: {task[:60]}",
            f"[Plan] 生成输出: {task[:60]}",
        ]
