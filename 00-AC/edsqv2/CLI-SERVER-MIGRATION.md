# CLI → Server 薄客户端改造 - 架构决策记录

> **时间：** 2026-05-14
> **状态：** 待实施（Server 模式实现时同步改造）
> **风险：** 双接入路径导致治理真空

---

## ⚠️ P1 升级：消息队列持久化

| 项目 | 原设计 | 风险 | 新设计 |
|------|--------|------|--------|
| 队列 | asyncio.Queue（内存） | 进程重启丢消息 | SQLite 持久化 |
| 确认 | 无 | 处理失败无重试 | ACK 机制 + 超时重入队 |
| 优先级 | P2 | 线上事故 | **P1（与 Server 同期）** |

**新增文件：** `persistent_queue.py`

```python
queue = PersistentMessageQueue("message_queue.db")

# 入队
queue.enqueue("dispatch", {"request": "..."}, trace_id="trace_001")

# 出队（阻塞）
msg = queue.dequeue("dispatch")

# 确认完成
queue.ack(msg.id)

# 处理失败，拒绝重试
queue.nack(msg.id, requeue=True)
```

---

## 问题描述

```
当前架构：
CLI ──────────────────────────→ dispatch（直接调用）
        （同步阻塞）

规划架构：
CLI ──→ Server(FastAPI+WS) ──→ dispatch
                │
                └── 队列系统（内存 - 进程重启丢消息）

风险：
Server 模式上线后，CLI 直连可能继续存在，
形成"双接入路径"——一套经过队列，一套不经过。

消息队列风险：
进程崩溃或重启 → asyncio.Queue 消息全部丢失 → 请求丢失无恢复
```

---

## 架构决策

**Server 模式上线后，CLI 降级为薄客户端，所有逻辑集中在 Server。**

```
改造后：
CLI（薄客户端）
  │
  └── 仅负责：输入 → HTTP/WS → Server → 返回显示
  │
  └── 无业务逻辑

Server（厚服务端）
  │
  ├── 接收请求
  ├── 队列管理
  ├── dispatch 调用
  ├── G3 治理管道
  ├── AC Bus 事件总线
  └── 统一持久化
```

---

## 实施时机

| 阶段 | 内容 | 依赖 | 优先级 |
|------|------|------|--------|
| **Phase 0** | 实现 PersistentMessageQueue | 无 | **P1（已完成）** |
| **Phase 1** | 实现 Server 模式（FastAPI + WebSocket） | Phase 0 完成 | P1 |
| **Phase 2** | CLI 改造为 HTTP/WS 客户端 | Phase 1 完成 | P1 |
| **Phase 3** | 移除 CLI 直连 dispatch 路径 | Phase 2 验证 | P2 |

---

## 改造检查清单

### 消息队列（P0 - 已完成）

- [x] PersistentMessageQueue 实现（SQLite 持久化）
- [x] ACK 机制（Worker 处理完成后确认）
- [x] 超时重试（未确认消息自动重新入队）
- [x] 多队列支持（不同类型消息隔离）
- [x] 追踪 ID（关联同一请求的所有消息）

### Server 端

- [ ] FastAPI 服务端点 `/dispatch` - 接收请求
- [ ] WebSocket 端点 `/ws` - 支持实时推送
- [ ] Server 端接入 PersistentMessageQueue
- [ ] Server 端接入 AC Bus 事件总线
- [ ] Server 端接入 G3 治理管道
- [ ] 统一持久化到 unified_platform.db

### CLI 端

- [ ] 移除直接 import dispatch
- [ ] 实现 HTTP 客户端调用 Server
- [ ] 实现 WebSocket 客户端接收实时推送
- [ ] CLI 仅保留：参数解析、输入验证、结果显示
- [ ] CLI 配置 Server URL（支持本地/远程）

### 迁移

- [ ] 迁移脚本：CLI 配置默认指向 localhost
- [ ] 文档更新：说明 CLI 已降级为薄客户端
- [ ] 监控：确保所有流量经过 Server

---

## 配置示例

```yaml
# cli_config.yaml
server:
  url: "http://localhost:8000"  # 或远程服务器
  ws_url: "ws://localhost:8000/ws"
  timeout: 30
  retry: 3

fallback:
  # 可选：Server 不可用时的降级策略
  mode: "queue"  # 或 "reject"
```

---

## 预期收益

1. **消除双接入路径** - 所有请求统一经过 Server + 队列
2. **治理一致性** - G3 管道覆盖 100% 请求
3. **运维简化** - CLI 无需本地环境配置
4. **扩展性** - Server 集群部署，CLI 零改动

---

## 关联文件

| 文件 | 当前状态 | 改造后 |
|------|---------|--------|
| `dispatch.py` | CLI 直接调用 | 仅 Server 调用 |
| `cli.py` | 厚客户端 | 薄客户端（HTTP/WS） |
| `server.py` | 规划中 | 主入口 |
| `unified_dispatcher.py` | 已有 | Server 调用 |

---

**决策结论：** Server 模式上线时，CLI 必须同步改造为薄客户端，否则双接入路径风险不可接受。

