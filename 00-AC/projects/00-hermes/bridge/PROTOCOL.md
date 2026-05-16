# A2A 文件桥协议规范

---

## 1. 协议概述

本协议定义了 Trae 与 OpenCode 之间通过文件系统进行异步通信的规范。

### 1.1 设计原则

- **异步通信**：无实时连接，通过文件轮询实现
- **消息持久化**：所有消息以文件形式持久化存储
- **简单可靠**：基于文件系统，无需额外服务依赖
- **双向通信**：支持 Trae ↔ OpenCode 双向消息传递

### 1.2 目录结构

```
bridge/
├── PROTOCOL.md          ← 协议规范（本文件）
├── bridge.py            ← 收发消息模块
├── blackboard.json      ← 共享状态板
├── inbox/
│   ├── opencode/        ← Trae 发给 OpenCode 的消息
│   └── trae/            ← OpenCode 发给 Trae 的消息
├── sent/                ← 已发送历史
└── archive/             ← 已处理归档
```

---

## 2. 消息格式

### 2.1 消息文件命名

```
msg-YYYYMMDD-{message_id}.json
```

### 2.2 消息结构

```json
{
  "message_id": "唯一消息ID",
  "sender": "发送方标识（trae/opencode）",
  "receiver": "接收方标识（trae/opencode）",
  "timestamp": "ISO8601时间戳",
  "type": "消息类型",
  "content": {...},
  "metadata": {...}
}
```

### 2.3 消息类型

| 类型 | 说明 |
|------|------|
| `handshake` | 握手消息，建立通信连接 |
| `handshake_reply` | 握手回复 |
| `task_update` | 任务状态更新 |
| `request` | 请求消息 |
| `response` | 响应消息 |
| `error` | 错误消息 |

---

## 3. 通信流程

### 3.1 握手流程

```
OpenCode → 发送握手消息 → bridge/inbox/trae/
       ← 接收握手回复 ← bridge/inbox/opencode/
```

### 3.2 消息处理流程

```
1. 发送方写入消息到对方 inbox
2. 接收方轮询 inbox 目录
3. 读取并处理消息
4. 将消息移动到 archive 目录
5. 发送回复（如有）
```

---

## 4. 共享状态板

### 4.1 状态板结构

```json
{
  "last_sync": "ISO8601时间戳",
  "active_tasks": [...],
  "completed_tasks": [...],
  "pending_actions": [...]
}
```

---

## 5. 协议版本

- **版本**: 1.0
- **发布日期**: 2026-05-12
- **状态**: 正式版
