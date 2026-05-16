from .planner import TaskPlanner
from .memory import ShortTermMemory


class BaseAgent:
    def __init__(self):
        self.planner = TaskPlanner()
        self.memory = ShortTermMemory()
        self.hermes_client = None

    def connect_hermes(self, client):
        self.hermes_client = client

    def think(self, user_input: str) -> list:
        self.memory.add({"role": "user", "content": user_input})
        if self.hermes_client:
            context = self.hermes_client.query(user_input)
        else:
            context = None
        steps = self.planner.decompose(user_input)
        self.memory.add({"role": "assistant", "content": {"steps": steps, "context": context}})
        return steps

    def act(self, step: str) -> str:
        if self.hermes_client:
            result = self.hermes_client.execute(step)
        else:
            result = f"[standalone] executed: {step}"
        self.memory.add({"role": "assistant", "content": result})
        return result

    def recent_context(self) -> list:
        return self.memory.recent()
