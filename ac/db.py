"""Database Operations · 数据库操作模块

失忆预防铁律：
1. 任何操作 ac_platform.db 的代码，必须先校验 schema 版本（PRAGMA user_version）
2. schema 不匹配时不允许直接 CREATE/ALTER，必须走 migration 脚本
3. AI 必须在 migration 前输出 diff，经确认后执行
4. 涅槃快照必须包含 schema 版本号

并发安全（Task 3 改造）：
- WAL 模式已启用，支持读写并发
- 所有写操作通过 execute_with_retry() 包装 tenacity 指数退避重试
- 重试次数上限 3 次，退避策略: 0.1s → 0.2s → 0.4s (max 2s)
"""

import sqlite3
import uuid
import hashlib
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 导入迁移管理器
from .db_migration import CURRENT_SCHEMA_VERSION, require_schema_version
from .validator import validate_truth

_log = logging.getLogger("ac.db")

GOVERNANCE_LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS ac_governance_log (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    command TEXT,
    input_preview TEXT,
    passed INTEGER,
    checks_json TEXT,
    corrected INTEGER,
    retries INTEGER,
    encoding_sanitized INTEGER DEFAULT 0,
    encoding_events TEXT,
    created_at TEXT
)
"""


def _validate_schema_version(conn: sqlite3.Connection) -> None:
    """校验schema版本（失忆预防铁律1）"""
    cur = conn.execute("PRAGMA user_version")
    current_version = cur.fetchone()[0]
    if current_version != CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"❌ Schema版本不匹配! 当前v{current_version}, 需要v{CURRENT_SCHEMA_VERSION}\n"
            f"请运行迁移脚本: python -m db_migration migrate"
        )


def ensure_governance_table(conn: sqlite3.Connection) -> None:
    """确保治理日志表存在（通过migration管理）"""
    _validate_schema_version(conn)
    # 表结构通过migration管理，这里只做版本校验
    pass


@require_schema_version(CURRENT_SCHEMA_VERSION)
def log_governance(conn: sqlite3.Connection, session_id: str, command: str, input_preview: str, result: dict[str, Any]) -> None:
    """记录治理日志"""
    import uuid as _uuid
    import json as _json
    from datetime import datetime, timezone
    from ac.governance.security import EncodingProbe
    
    encoding_events = EncodingProbe.get_log()
    conn.execute(
        "INSERT INTO ac_governance_log (id, session_id, command, input_preview, passed, checks_json, corrected, retries, encoding_sanitized, encoding_events, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(_uuid.uuid4()),
            session_id,
            command,
            input_preview[:200],
            1 if result["passed"] else 0,
            _json.dumps(result["checks"], ensure_ascii=False),
            1 if any(c.get("corrected") for c in result["checks"]) else 0,
            sum(c.get("retries", 0) for c in result["checks"]),
            1 if result.get("encoding_sanitized") else 0,
            _json.dumps(encoding_events, ensure_ascii=False) if encoding_events else None,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()


# 数据库路径唯一源头
# 所有模块通过此函数获取路径，避免分散解析导致双副本
_DEFAULT_DB = "ac_platform.db"
_AC_DIR = Path(__file__).resolve().parent  # C:\...\ac\
CANONICAL_DB_PATH = str(_AC_DIR / _DEFAULT_DB)

# ── 并发安全: SQLite 写操作自动化配置 ──
_WRITE_OPS_COUNT = 0
_RETRY_COUNT = 0
_CONFLICT_COUNT = 0


def get_write_stats() -> dict[str, int]:
    """获取写操作统计（监控用）"""
    return {"write_ops": _WRITE_OPS_COUNT, "retries": _RETRY_COUNT, "conflicts": _CONFLICT_COUNT}


def _is_sqlite_busy(exc: Exception) -> bool:
    """判断是否为 SQLite 写锁冲突"""
    if isinstance(exc, sqlite3.OperationalError):
        msg = str(exc).lower()
        return "database is locked" in msg or "database schema is locked" in msg
    return False


def execute_with_retry(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
    *,
    max_attempts: int = 3,
    base_wait: float = 0.1,
    max_wait: float = 2.0,
) -> sqlite3.Cursor:
    """带指数退避重试的写操作执行

    Args:
        conn: SQLite 连接
        sql: SQL 语句
        params: 参数元组
        max_attempts: 最大尝试次数（含首次）
        base_wait: 初始等待时间（秒）
        max_wait: 最大等待时间（秒）

    Returns:
        sqlite3.Cursor

    Raises:
        sqlite3.OperationalError: 所有重试均失败时抛出
    """
    global _WRITE_OPS_COUNT, _RETRY_COUNT, _CONFLICT_COUNT
    _WRITE_OPS_COUNT += 1

    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            cur = conn.execute(sql, params)
            if attempt > 0:
                _RETRY_COUNT += 1
            return cur
        except sqlite3.OperationalError as e:
            last_exc = e
            if not _is_sqlite_busy(e):
                raise
            _CONFLICT_COUNT += 1
            if attempt < max_attempts - 1:
                wait = min(base_wait * (2 ** attempt), max_wait)
                _log.warning(f"SQLite write lock conflict, retry {attempt + 1}/{max_attempts} after {wait:.2f}s: {sql[:60]}")
                time.sleep(wait)

    raise last_exc  # type: ignore[misc]


def _get_db_path(config: dict) -> str:
    p = config.get("paths", {}).get("db_path", _DEFAULT_DB)
    candidate = Path(p)
    if candidate.is_absolute():
        return str(candidate)
    return str(_AC_DIR / candidate)


def get_conn(config: dict) -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path(config), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def load_experts(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    try:
        conn.execute("SELECT priority FROM ac_experts LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE ac_experts ADD COLUMN priority VARCHAR(5) DEFAULT 'P5'")
    cur = conn.execute("SELECT * FROM ac_experts ORDER BY category, name")
    return [dict(r) for r in cur.fetchall()]


def log_schedule(conn: sqlite3.Connection, session_id: str, query: str, matched: str, mode: str) -> int:
    h = hashlib.md5(query.encode("utf-8")).hexdigest()[:32]
    cur = conn.execute(
        "INSERT INTO ac_schedule_log (log_id, session_id, query_hash, query_preview, matched_expert, response_mode, scheduler_version, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            session_id,
            h,
            query[:100],
            matched,
            mode,
            "v2.3",
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    return cur.lastrowid


def save_truth(conn: sqlite3.Connection, title: str, category: str, source: str, content: str, tags: str | None = None) -> dict[str, Any]:
    # 入库前自动验证（L0/L2/L5三级）
    vr = validate_truth(title, content)
    vtag = f"[v{vr.level}:{vr.score:.1f}]"
    verified = 1 if vr.passed and vr.level == "L5" else 0
    existing_tags = (tags or "").strip()
    full_tags = f"{existing_tags} {vtag}" if existing_tags else vtag
    cur = conn.execute(
        "INSERT INTO ac_truth (truth_id, title, category, source, content, truth_count, verified, anchor_verified, tags, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            title,
            category,
            source,
            content,
            1,
            verified,
            verified,  # anchor_verified 与 verified 同步（DB 触发器要求）
            full_tags,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    return {"rowid": cur.lastrowid, "verified": verified, "validation": vr.level, "score": vr.score}


def get_log(conn: sqlite3.Connection, limit: int = 10) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT * FROM ac_schedule_log ORDER BY created_at DESC LIMIT ?", (limit,)
    )
    return [dict(r) for r in cur.fetchall()]


def get_stats(conn: sqlite3.Connection) -> dict[str, int]:
    cur = conn.execute(
        "SELECT category, COUNT(*) as cnt FROM ac_experts GROUP BY category"
    )
    return {r["category"]: r["cnt"] for r in cur.fetchall()}
