# 给 Lingma 的任务指令书 — 将 Hermes + Lingma 封装为统一 SDK

> 此文档直接发给 Lingma。Lingma 恢复后请首先执行此任务。

---

## 一、你要做的事（一句话）

把 AgentHub 中的两个核心项目（Hermes 数据中心 + Lingma API）封装成一个统一 SDK，对外提供 `HermesLingmaSdk` 单一入口。

---

## 二、当前项目全貌（你需要知道的上下文）

### 2.1 代码仓库结构

```
AgentHub/                         ← 主仓库
├── ac-core/                      ← 平台底座 (BaseAgent/TaskPlanner/ShortTermMemory)
├── dads-medical/                 ← 医疗插件 (MedicalDiagnosis + 10疾病KB)
├── dads-personal/                ← 个人插件 (DoctorRiskAgent + 8条防护规则)
├── shared/hermes/                ← 数据中心连接器 (HermesClient + Schema)
├── src/core/AC/                  ← AC决策中心 (ACAgent/Watchdog/Router/Environment)
│   ├── agent.py                  ← ACAgent
│   ├── watchdog.py               ← DB 轮询
│   ├── router.py                 ← 多模型调度器 (已接入 DeepSeek + 阿里灵码)
│   └── environment.py            ← 动态环境注入
└── main.py                       ← CLI 入口

TRAE/                             ← 知识库仓库
└── Hermes/00-hermes/
    ├── 01-架构设计/              ← 架构文档
    ├── 01-AC/                    ← AC 文档
    ├── 01-数据中心/              ← 数据中心文档
    ├── 01-DADS-medical/          ← 医疗版文档
    └── 01-DADS-person/           ← 个人版文档
```

### 2.2 当前已接入的 AI 节点

| 节点 | Base URL | 模型 |
|------|----------|------|
| DeepSeek V3 | `https://api.deepseek.com/v1` | deepseek-chat |
| DeepSeek R1 | `https://api.deepseek.com/v1` | deepseek-reasoner |
| 阿里灵码 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | qwen-turbo/plus/max |

### 2.3 多模型路由器现状

`AgentHub/src/core/AC/router.py` 中的 `AIRouter` 已实现：
- 5 种意图分类 (CODE/MEDICAL/LEGAL/REASON/CHAT)
- 11 条路由规则 (匹配中文比例、Token 数、复杂度)
- `call()` 方法直接调 API
- 路由测试已通过：

```
[CODE   ] → qwen/plus      | 含中文注释的代码
[MEDICAL] → qwen/max       | 高精度医疗诊断
[LEGAL  ] → qwen/max       | 法律合规
[REASON ] → deepseek/R1    | 复杂推理
[CHAT   ] → qwen/turbo     | 闲聊
```

---

## 三、SDK 架构（按以下 4 层实现）

### 架构图

```
+---------------------------+      业务方调用: sdk = HermesLingmaSdk(config)
|   HermesLingmaSdk         |  ← 对外单一入口
+---------------------------+
|   适配层                   |  ← HermesAdapter / LingmaAdapter
+---------------------------+
|   公共能力层               |  ← 重试 超时 熔断 日志 鉴权
+---------------------------+
|   底层通信与安全层         |  ← HTTP 客户端 连接池 签名
+---------------------------+
```

### 第三层：公共能力层 — 你要实现的

| 模块 | 文件路径 | 实现内容 |
|------|----------|----------|
| 重试与熔断 | `sdk/common/retry.py` | 指数退避重试 (1s/2s/4s)，熔断器 (连续5次失败→熔断30s) |
| 超时管理 | `sdk/common/timeout.py` | 连接超时 10s，读取超时 30s，可配置 |
| 统一日志 | `sdk/common/logger.py` | 结构化日志 (JSON格式)，记录: 时间/模型/耗时/Token数/是否重试 |
| 错误模型 | `sdk/common/errors.py` | 统一错误码映射: TimeoutError / AuthError / RateLimitError / ServerError |
| 序列化 | `sdk/common/serde.py` | 请求/响应 JSON 序列化，自动类型转换 |

### 第二层：适配层 — 你要实现的

**抽象基类**:
```python
class ProjectClient(ABC):
    @abstractmethod
    def call(self, method: str, params: dict) -> dict:
        pass
```

**HermesAdapter** (`sdk/adapters/hermes.py`):
- 封装 `shared/hermes/client.py` 的 HermesClient
- 适配 read_data() / write_data()
- 内置重试逻辑 (继承公共能力层)

**LingmaAdapter** (`sdk/adapters/lingma.py`):
- 封装 `src/core/AC/router.py` 的 AIRouter
- 适配: code_complete() / chat() / reason()
- 自动模型选择 + Fallback

### 第一层：对外接口 — 你要实现的

**API 风格：底层透传** — `sdk.hermes.io.read_data()` 直接映射到底层 HermesClient，不做业务语义包装。

```python
class HermesLingmaSdk:
    def __init__(self, config: SdkConfig):
        self.hermes = HermesIO(self._hermes_adapter)
        self.lingma = LingmaAI(self._lingma_adapter)

class HermesIO:
    """底透: sdk.hermes.io.read_data(path) → HermesClient.read_data()"""
    def read_data(self, path: str) -> dict:
        return self._adapter.call("read_data", {"path": path})
    def write_data(self, path: str, payload: dict) -> dict:
        return self._adapter.call("write_data", {"path": path, "payload": payload})

class LingmaAI:
    """底透: sdk.lingma.code.complete() / sdk.lingma.chat.send()"""
    def __init__(self, adapter):
        self.code = LingmaCode(adapter)
        self.chat = LingmaChat(adapter)

class LingmaCode:
    def complete(self, code: str) -> str:
        return self._adapter.call("code_complete", {"code": code})

class LingmaChat:
    def send(self, message: str) -> str:
        return self._adapter.call("chat", {"message": message})
```

### SdkConfig

```python
@dataclass
class SdkConfig:
    hermes_endpoint: str
    lingma_endpoint: str
    deepseek_key: str
    aliyun_key: str
    max_retries: int = 3
    timeout_sec: int = 30
    enable_circuit_breaker: bool = True
```

---

## 四、你要创建的完整文件清单

```
AgentHub/sdk/
├── __init__.py                   ← 导出 HermesLingmaSdk, SdkConfig
├── config.py                     ← SdkConfig dataclass
├── interface/                    ← 对外接口层 (底层透传风格)
│   ├── __init__.py
│   ├── hermes_io.py              ← HermesIO 门面: io.read_data() / io.write_data()
│   ├── lingma_code.py            ← LingmaCode 门面: code.complete()
│   └── lingma_chat.py            ← LingmaChat 门面: chat.send()
├── adapters/                     ← 适配层
│   ├── __init__.py
│   ├── base.py                   ← ProjectClient ABC
│   ├── hermes_adapter.py         ← HermesAdapter
│   └── lingma_adapter.py         ← LingmaAdapter
├── common/                       ← 公共能力层
│   ├── __init__.py
│   ├── retry.py                  ← 重试 + 熔断
│   ├── errors.py                 ← 统一错误模型
│   ├── logger.py                 ← 结构化日志
│   └── timeout.py                ← 超时配置
└── transport/                    ← 底层通信层
    ├── __init__.py
    ├── http_client.py            ← HTTP 客户端 (基于 urllib/requests)
    └── auth.py                   ← 鉴权头生成
```

---

## 五、验收标准

完成后运行以下测试应全部通过：

```python
from sdk import HermesLingmaSdk, SdkConfig

sdk = HermesLingmaSdk(SdkConfig(
    hermes_endpoint="https://api.hermes.local",
    lingma_endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1",
    deepseek_key="sk-c8***",
    aliyun_key="sk-66***",
))

# 测试1: Hermes I/O 读 (底层透传)
result = sdk.hermes.io.read_data("病历/高血压")
assert result is not None

# 测试2: Hermes I/O 写
sdk.hermes.io.write_data("诊断/AML", {"confidence": 0.85})

# 测试3: Lingma 代码补全
code = sdk.lingma.code.complete("def quicksort(arr):")
assert "sort" in code.lower()

# 测试4: Lingma 自动路由聊天
answer = sdk.lingma.chat.send("急性白血病的诊断标准是什么")
assert len(answer) > 0

# 测试4: 重试机制 (模拟)
# 预期: 失败后 3 次指数退避重试
```

---

## 六、技术约束

1. **不引入第三方依赖** — 只用 Python 标准库 (urllib + abc + dataclasses + json + logging + time)
2. **线程安全** — SDK 实例可跨线程共享
3. **向后兼容** — 不破坏现有的 ac-core / dads-medical / shared/hermes 代码
4. **API Key 安全** — 不允许在日志中打印 Key，不允许在错误消息中暴露 Key

---

*编写时间: 2026-05-11 | 编写人: Opencode (项目秘书)*
*状态: 等待 Lingma 恢复执行*
