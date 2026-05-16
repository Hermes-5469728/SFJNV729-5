from pathlib import Path
import sys
import importlib.util

from .base import BaseAdapter
from ..common.logger import SdkLogger


class ACAdapter(BaseAdapter):
    def __init__(self, deepseek_key: str, aliyun_key: str, data_dir: str):
        self.logger = SdkLogger("ac-adapter")
        self.data_dir = data_dir
        self._load_modules()
        from ac_core_router import AIRouter
        from watchdog_mod import ACWatchdog
        from env_mod import inject_dynamic_context
        self.router = AIRouter()
        self.router.PROVIDERS["deepseek/V3"]["key"] = deepseek_key
        self.router.PROVIDERS["deepseek/R1"]["key"] = deepseek_key
        self.router.PROVIDERS["qwen/turbo"]["key"] = aliyun_key
        self.router.PROVIDERS["qwen/plus"]["key"] = aliyun_key
        self.router.PROVIDERS["qwen/max"]["key"] = aliyun_key
        self._watchdog = ACWatchdog(data_dir=data_dir)
        self._inject = inject_dynamic_context

    def _load_modules(self):
        root = Path(__file__).resolve().parent.parent.parent
        for name, path in [
            ("ac_core_router", root / "src" / "core" / "AC" / "router.py"),
            ("watchdog_mod", root / "src" / "core" / "AC" / "watchdog.py"),
            ("env_mod", root / "src" / "core" / "AC" / "environment.py"),
        ]:
            spec = importlib.util.spec_from_file_location(name, str(path))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)

    def get_watchdog(self):
        return self._watchdog

    def inject_context(self, template: str) -> str:
        return self._inject(template)

    def call(self, method: str, params: dict) -> dict:
        import time
        t0 = time.time()
        try:
            if method == "router_dispatch":
                text = params["text"]
                target = self.router.route(text)
                result = self.router.call(target, [{"role": "user", "content": text}])
                self.logger.log_call("ac", method, int((time.time()-t0)*1000))
                return {"target": target, "result": result}
            if method == "router_classify":
                return self.router.classify(params["text"])
            if method == "router_list_models":
                return {"models": list(self.router.PROVIDERS.keys())}
            if method == "env_inject":
                return {"result": self._inject(params["template"])}
            if method == "watchdog_scan":
                events = self._watchdog.scan()
                self.logger.log_call("ac", method, int((time.time()-t0)*1000))
                return {"events": events}
            if method == "watchdog_register":
                return {"status": "ok", "info": "callback registered via SDK layer"}
            return {"error": f"unknown method: {method}"}
        except Exception as e:
            self.logger.log_call("ac", method, 0, error=str(e))
            raise
