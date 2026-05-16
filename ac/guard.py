"""AC L0 防御层 · InputGuard — 编码/路径/换行/环境变量/退出码"""

import os
import sys
import json
import time
import logging
import threading
import functools
from pathlib import Path

_LOG: logging.Logger | None = None


def get_log(level: int = logging.INFO) -> logging.Logger:
    global _LOG
    if _LOG is not None:
        return _LOG
    _LOG = logging.getLogger("ac")
    _LOG.setLevel(level)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)-5s] %(message)s", datefmt="%H:%M:%S"))
    if not _LOG.handlers:
        _LOG.addHandler(handler)
    return _LOG

_GUARD_LOG: list[dict] = []


def flush_log(db_path: str = "ac_platform.db"):
    if not _GUARD_LOG:
        return
    import sqlite3
    from datetime import datetime, timezone
    db = str(Path(__file__).resolve().parent / db_path)
    try:
        conn = sqlite3.connect(db, timeout=5)
    except Exception:
        return
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ac_guard_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guard TEXT,
                action TEXT,
                detail TEXT,
                created_at TEXT
            )
        """)
        now = datetime.now(timezone.utc).isoformat()
        for entry in _GUARD_LOG:
            conn.execute(
                "INSERT INTO ac_guard_log (guard, action, detail, created_at) VALUES (?, ?, ?, ?)",
                (entry.get("guard"), entry.get("action"), json.dumps(entry, ensure_ascii=False), now),
            )
        conn.commit()
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
    _GUARD_LOG.clear()


def _log(guard: str, action: str, **kw):
    _GUARD_LOG.append({"guard": guard, "action": action, **kw})


# ── 1. 编码 ──────────────────────────────────────────

_ENCODING_ERROR_MSG = (
    "输入编码损坏。AC CLI 需要 UTF-8 终端。\n"
    "  Windows: chcp 65001   (将代码页切换为 UTF-8)\n"
    "  或重启终端后重试。\n"
    "  如持续出现，运行: python ac/cli.py status"
)


def config_encoding():
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        try:
            sys.stdin.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    _log("encoding", "config", stdin_encoding=sys.stdin.encoding, stdout_encoding=sys.stdout.encoding)


def ensure_utf8(text: str) -> str:
    if not text:
        return text
    original = text
    if "\ufffd" in text:
        try:
            recovered = text.encode("latin-1").decode("utf-8")
            if "\ufffd" not in recovered:
                text = recovered
                _log("encoding", "recovered", via="latin1_bridge")
                return text
        except (UnicodeEncodeError, UnicodeDecodeError, ValueError):
            pass
        raise ValueError(_ENCODING_ERROR_MSG)
    if text != original:
        _log("encoding", "sanitized")
    return text


# ── 2. 换行 ──────────────────────────────────────────

def normalize_newlines(text: str) -> str:
    original_len = len(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if len(text) != original_len:
        _log("newline", "normalized", original_len=original_len, result_len=len(text))
    return text


# ── 3. 路径 ──────────────────────────────────────────

def sanitize_path(path: str) -> Path:
    raw = path.strip().strip("\"'")
    p = Path(raw)
    # 防止路径遍历攻击
    if ".." in p.parts:
        p = Path(p.parts[-1])
    if not p.is_absolute():
        p = Path.cwd() / p
    p = p.resolve()
    # 限制在允许的根目录内
    allowed = [Path.cwd().resolve(), Path.home().resolve()]
    if not any(str(p).startswith(str(a)) for a in allowed):
        p = Path.cwd() / Path(raw).name
        p = p.resolve()
    if str(p) != raw:
        _log("path", "normalized", raw=raw, resolved=str(p))
    return p


def sanitize_paths(*paths: str) -> list[Path]:
    return [sanitize_path(p) for p in paths]


# ── 4. 环境变量 ──────────────────────────────────────

class EnvConfig:
    def __init__(self, prefix: str = ""):
        self._prefix = prefix
        self._errors: list[str] = []

    def get_str(self, key: str, default: str | None = None, required: bool = False) -> str | None:
        full = f"{self._prefix}{key}" if self._prefix else key
        val = os.environ.get(full)
        if val is None:
            if required:
                self._errors.append(f"缺少必填环境变量: {full}")
            return default
        _log("env", "loaded", key=full, type="str")
        return val

    def get_int(self, key: str, default: int | None = None, required: bool = False) -> int | None:
        full = f"{self._prefix}{key}" if self._prefix else key
        val = os.environ.get(full)
        if val is None:
            if required:
                self._errors.append(f"缺少必填环境变量: {full}")
            return default
        try:
            result = int(val)
            _log("env", "loaded", key=full, type="int")
            return result
        except (ValueError, TypeError):
            self._errors.append(f"环境变量 {full} 应为整数, 实际为 {val!r}")
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        full = f"{self._prefix}{key}" if self._prefix else key
        val = os.environ.get(full)
        if val is None:
            return default
        result = val.lower() in ("1", "true", "yes", "on")
        if result:
            _log("env", "loaded", key=full, type="bool")
        return result

    def errors(self) -> list[str]:
        return list(self._errors)

    def require_ok(self) -> bool:
        return len(self._errors) == 0


# ── 5. 退出码 ────────────────────────────────────────

class GuardExit(SystemExit):
    pass


def guard_exit(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kw):
        try:
            return fn(*args, **kw)
        except GuardExit:
            raise
        except Exception as e:
            print(f"[FATAL] {e}", file=sys.stderr)
            _log("exit", "exception", error=str(e))
            raise GuardExit(1) from e
    return wrapper


def exit_ok():
    raise GuardExit(0)


def exit_fail(msg: str = "", code: int = 1):
    if msg:
        print(msg, file=sys.stderr)
    _log("exit", "fail", code=code, msg=msg)
    raise GuardExit(code)


# ── 6. 心跳熔断 ──────────────────────────────────────

class CircuitBreaker:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(self, failure_threshold: int = 3, reset_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.state = self.CLOSED
        self.next_attempt = 0.0

    def record_success(self):
        if self.state != self.CLOSED:
            _log("circuit_breaker", "closed", from_state=self.state)
        self.failure_count = 0
        self.state = self.CLOSED

    def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold and self.state != self.OPEN:
            self.state = self.OPEN
            self.next_attempt = time.time() + self.reset_timeout
            _log("circuit_breaker", "opened", threshold=self.failure_threshold, reset_after=self.reset_timeout)

    def can_request(self) -> bool:
        if self.state == self.CLOSED:
            return True
        if self.state == self.OPEN:
            if time.time() >= self.next_attempt:
                self.state = self.HALF_OPEN
                _log("circuit_breaker", "half_open")
                return True
            return False
        return True


class HeartbeatReporter:
    def __init__(self, cli_id: str = "", interval: int = 5, db_path: str = "ac_platform.db",
                 breaker: CircuitBreaker | None = None):
        self.cli_id = cli_id or f"cli-{os.getpid()}"
        self.interval = interval
        self._db_path = db_path
        self.is_running = False
        self._thread: threading.Thread | None = None
        self._status = "starting"
        self._command = ""
        self.cb = breaker or CircuitBreaker()

    def _db_conn(self):
        import sqlite3
        return sqlite3.connect(str(Path(__file__).resolve().parent / self._db_path), timeout=10)

    def _ensure_table(self, conn):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ac_heartbeat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cli_id TEXT,
                pid INTEGER,
                command TEXT,
                status TEXT,
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ac_circuit_breaker (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cli_id TEXT,
                state TEXT,
                failure_count INTEGER,
                threshold INTEGER,
                created_at TEXT
            )
        """)

    def _log_cb_state(self, conn):
        from datetime import datetime, timezone
        conn.execute(
            "INSERT INTO ac_circuit_breaker (cli_id, state, failure_count, threshold, created_at) VALUES (?, ?, ?, ?, ?)",
            (self.cli_id, self.cb.state, self.cb.failure_count, self.cb.failure_threshold,
             datetime.now(timezone.utc).isoformat()),
        )

    def _beat(self):
        conn = self._db_conn()
        self._ensure_table(conn)
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO ac_heartbeat (cli_id, pid, command, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (self.cli_id, os.getpid(), self._command, self._status, now),
        )
        self._log_cb_state(conn)
        conn.commit()
        conn.close()

    def _loop(self):
        retry = 1
        while self.is_running:
            try:
                self._beat()
                self.cb.record_success()
                retry = 1
            except Exception:
                self.cb.record_failure()
                wait = min(retry, 8)
                _log("heartbeat", "fail", cli_id=self.cli_id, retry_in=wait)
                time.sleep(wait)
                retry = min(retry * 2, 64)
                continue
            time.sleep(self.interval)

    def start(self, command: str = ""):
        if self.is_running:
            return
        if not self.cb.can_request():
            _log("heartbeat", "blocked", cli_id=self.cli_id, cb_state=self.cb.state)
            return
        self._command = command
        self._status = "running"
        self.is_running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        _log("heartbeat", "start", cli_id=self.cli_id, interval=self.interval)

    def stop(self):
        self._status = "stopped"
        self.is_running = False
        try:
            self._beat()
        except Exception:
            pass
        _log("heartbeat", "stop", cli_id=self.cli_id)

    def fail(self):
        self._status = "failed"
        try:
            self._beat()
        except Exception:
            pass
        self.is_running = False

    def can_proceed(self) -> bool:
        return self.cb.can_request()


# ── 7. 真值入库唯一通道 ──────────────────────────────

def store_truth(title: str, category: str, source: str, content: str, tags: str = "") -> dict:
    """真值入库唯一批准通道。强制L0/L2/L5验证，禁止直接SQL INSERT。"""
    import sqlite3
    from ac.db import save_truth, CANONICAL_DB_PATH
    conn = sqlite3.connect(CANONICAL_DB_PATH)
    try:
        result = save_truth(conn, title, category, source, content, tags)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        return {"rowid": None, "verified": 0, "validation": "ERROR", "score": 0.0, "error": str(e)}
    finally:
        conn.close()


# ── 组合入口 ──────────────────────────────────────────

def sanitize_text(text: str) -> str:
    text = normalize_newlines(text)
    text = ensure_utf8(text)
    return text
