from pathlib import Path
import importlib.util
import sys

_ac_spec = importlib.util.spec_from_file_location(
    "ac_core",
    str(Path(__file__).resolve().parent.parent.parent.parent / "ac-core" / "__init__.py"),
)
_ac_core = importlib.util.module_from_spec(_ac_spec)
sys.modules["ac_core"] = _ac_core
_ac_spec.loader.exec_module(_ac_core)

from .environment import inject_dynamic_context
from .watchdog import ACWatchdog


class ACAgent(_ac_core.BaseAgent):
    def __init__(self):
        super().__init__()
        self.watchdog = ACWatchdog()
        self.watchdog.register_callback(self.on_product_event)

    def think(self, user_input: str) -> list:
        dynamic_ctx = inject_dynamic_context(user_input)
        self.memory.add({"role": "user", "content": user_input})
        if self.hermes_client:
            self.hermes_client.query(dynamic_ctx)
        steps = self.planner.decompose(dynamic_ctx)
        self.memory.add({"role": "assistant", "content": {"steps": steps}})
        return steps

    def on_product_event(self, event: dict) -> None:
        product = event["product"]
        task_id = event["task_id"]
        state = event["state"]
        if state in ("done", "error"):
            self.memory.add({
                "role": "product",
                "content": f"{product}:{task_id} -> {state}",
            })
