from .config import SdkConfig
from .adapters.ac_adapter import ACAdapter
from .adapters.datacenter_adapter import DataCenterAdapter
from .interface.ac import ACInterface
from .interface.datacenter import DataCenterInterface
from .common.retry import RetryHandler, CircuitBreaker
from .common.errors import SdkError, TimeoutError, AuthError, RateLimitError, ServerError


class HermesACSdk:
    def __init__(self, config: SdkConfig = None):
        cfg = config or SdkConfig()

        ac_adapter = ACAdapter(
            deepseek_key=cfg.deepseek_key,
            aliyun_key=cfg.aliyun_key,
            data_dir=cfg.data_dir,
        )
        dc_adapter = DataCenterAdapter(endpoint=cfg.hermes_endpoint)

        self.ac = ACInterface(ac_adapter)
        self.dc = DataCenterInterface(dc_adapter)
        self.config = cfg
