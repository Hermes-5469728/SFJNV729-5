class SdkError(Exception):
    def __init__(self, message: str, code: str = "SDK_UNKNOWN", source: str = ""):
        super().__init__(message)
        self.code = code
        self.source = source


class TimeoutError(SdkError):
    def __init__(self, endpoint: str, timeout_sec: int):
        super().__init__(
            f"请求超时: {endpoint} ({timeout_sec}s)",
            code="SDK_TIMEOUT",
            source=endpoint,
        )


class AuthError(SdkError):
    def __init__(self, endpoint: str):
        super().__init__(
            "鉴权失败: API Key 无效或已过期",
            code="SDK_AUTH_ERROR",
            source=endpoint,
        )


class RateLimitError(SdkError):
    def __init__(self, endpoint: str):
        super().__init__(
            "请求频率超限, 请稍后重试",
            code="SDK_RATE_LIMIT",
            source=endpoint,
        )


class ServerError(SdkError):
    def __init__(self, endpoint: str, status: int):
        super().__init__(
            f"服务端错误: {status}",
            code="SDK_SERVER_ERROR",
            source=endpoint,
        )
