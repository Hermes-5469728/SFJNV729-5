class ACInterface:
    def __init__(self, ac_adapter):
        self._adapter = ac_adapter
        self.router = ACRouterInterface(ac_adapter)
        self.watchdog = ACWatchdogInterface(ac_adapter)
        self.env = ACEnvInterface(ac_adapter)


class ACRouterInterface:
    def __init__(self, adapter):
        self._a = adapter

    def dispatch(self, text: str) -> dict:
        return self._a.call("router_dispatch", {"text": text})

    def classify(self, text: str) -> dict:
        return self._a.call("router_classify", {"text": text})

    def list_models(self) -> dict:
        return self._a.call("router_list_models", {})


class ACWatchdogInterface:
    def __init__(self, adapter):
        self._a = adapter

    def scan(self) -> dict:
        return self._a.call("watchdog_scan", {})


class ACEnvInterface:
    def __init__(self, adapter):
        self._a = adapter

    def inject(self, template: str) -> dict:
        return self._a.call("env_inject", {"template": template})
