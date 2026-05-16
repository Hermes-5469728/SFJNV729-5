# 意图: SQLite 并发安全改造

## 目标
分析所有 SQLite 写操作，用 WAL 模式 + 重试机制解决多 AI 同时调用时的写锁冲突，确保数据不丢失。

## 背景 · 当前缺失的后果
- 多 AI 同时调 dispatch 时，SQLite 写锁（数据库级锁）可能成为瓶颈
- 写操作冲突时 SQLite 直接抛 `OperationalError: database is locked`，无重试
- 当前 WAL 模式已启用（`db.py:101`），但缺少以下配套措施：
  - 重试机制（写锁冲突时自动退避重试）
  - 连接池或连接管理策略
  - 超时和死锁检测
  - 写操作监控（哪些操作频率最高、冲突率最高）

## 关键约束
1. **不得丢失数据** — 所有失败写操作必须重试到成功或明确标记为永久失败
2. **性能下降不超过 20%** — 重试机制不应显著增加延迟
3. **向后兼容** — 不改变现有模块的数据库调用接口
4. **与 R4 对齐** — 所有数据库操作必须走 `guard.store_truth()`

## 输入/输出
- **输入**: 现有 SQLite 操作（ac_governance_log, ac_schedule_log, ac_truth 等表的读写）
- **输出**: 带有自动重试的数据库访问层
- **接口**: 
  - `db.execute_with_retry()` — 带重试的写操作
  - `db.get_connection()` — 连接池获取（或单连接管理）
  - `db.monitor()` — 写操作统计

## 当前状态分析

### 已具备
- WAL 模式: ✅ `PRAGMA journal_mode=WAL` (db.py:101)
- 超时设置: ✅ `timeout=10` (db.py:99)
- Row factory: ✅ `conn.row_factory = sqlite3.Row`

### 缺失
- 重试机制: ❌ 写锁冲突时直接抛异常
- 退避策略: ❌ 无指数退避或抖动
- 连接管理: ❌ 每次调用 get_conn() 创建新连接
- 监控: ❌ 无写操作频率/冲突率统计

## WAL 模式须知
| 特性 | 默认 (DELETE) | WAL |
|------|--------------|-----|
| 读写并发 | 写阻塞读 | 读写可并发 |
| 写并发 | 串行 | 仍串行（SQLite 限制） |
| 适用场景 | 单机低频 | 多读少写 |

**关键限制**: WAL 模式允许多个读者 + 一个写者并发，但不允许多个写者同时写。多 AI 同时 dispatch 时如果都触发写操作，仍会产生 `SQLITE_BUSY`。

## 技术方案: tenacity 重试

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.1, min=0.1, max=2),
    retry_error_callback=lambda retry_state: None  # 永久失败返回 None
)
def execute_with_retry(conn, sql, params):
    return conn.execute(sql, params)
```

## 已知难点
- [TODO] `tenacity` 库需要加入依赖（requirements.txt + pyproject.toml）
- [TODO] 多连接场景下 WAL 检查点管理（WAL 文件无限增长）
- [TODO] `SQLITE_BUSY` vs `SQLITE_LOCKED` 区别处理
- [TODO] 写操作重试期间的连接状态管理（是否复用连接）
- [OPT] 考虑 `sqlite3` → `aiosqlite` 迁移（异步重试更优雅）
- [OPT] 连接池实现（`sqlite3` 不支持原生连接池，需自己封装）

## 调研方向
- `tenacity` 库: 指数退避、重试条件、回调
- SQLite WAL 模式最佳实践: checkpoint 策略、`wal_autocheckpoint`
- `PRAGMA busy_timeout` vs 应用层重试
- SQLite 写吞吐量基准测试（模拟 2-5 并发写入）

## 实施阶段
1. **Phase 1**: 添加 tenacity 依赖，为 db.py 的写操作包装重试
2. **Phase 2**: 实现连接管理器（单连接复用 + 重连逻辑）
3. **Phase 3**: 添加写操作监控（执行次数、重试次数、冲突次数）
4. **Phase 4**: WAL 检查点管理 + 并发压力测试

## 当前状态
意图文档已生成。Phase 1 实现进行中。
