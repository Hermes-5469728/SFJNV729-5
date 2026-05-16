import time
import threading


class RetryHandler:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    def execute(self, fn, *args, **kwargs):
        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_err = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** (attempt - 1))
                    time.sleep(delay)
        raise last_err


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_sec: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_sec = recovery_sec
        self._failures = 0
        self._last_failure = 0.0
        self._lock = threading.Lock()

    def call(self, fn, *args, **kwargs):
        with self._lock:
            if self._failures >= self.failure_threshold:
                if time.time() - self._last_failure < self.recovery_sec:
                    raise CircuitOpenError("断路器已打开")
                self._failures = 0
        try:
            result = fn(*args, **kwargs)
            with self._lock:
                self._failures = 0
            return result
        except Exception:
            with self._lock:
                self._failures += 1
                self._last_failure = time.time()
            raise


class CircuitOpenError(Exception):
    pass
