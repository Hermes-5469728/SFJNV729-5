from dataclasses import dataclass, field


@dataclass
class SdkConfig:
    deepseek_key: str = ""
    aliyun_key: str = ""
    hermes_endpoint: str = "http://localhost:8000"
    max_retries: int = 3
    timeout_sec: int = 30
    enable_circuit_breaker: bool = True
    data_dir: str = "data"
    poll_interval: float = 5.0
