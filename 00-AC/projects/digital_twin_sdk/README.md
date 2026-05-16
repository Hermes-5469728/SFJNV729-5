# 个人数字孪生底座 SDK

一个通用的个人数字孪生底座SDK框架，提供权限控制、数据检索和插件管理能力。

## 核心概念

### 数学模型

SDK 抽象为一个基础空间 S，包含两个核心算子：

1. **算子 A (Access Control)**: 过滤函数 f(x) → {0, 1}，负责合规性检查
2. **算子 R (RAG/Data)**: 映射函数 g(x) → y，负责知识检索

DADS（医疗插件）是这个空间中的一个特定向量，调用 f(x) 和 g(x) 完成任务。

## 目录结构

```
digital_twin_sdk/
├── src/
│   ├── core/              # 核心模块
│   │   ├── interfaces.rs  # 核心接口定义
│   │   ├── plugin_manager.rs  # 插件管理器
│   │   ├── sdk.rs         # SDK主入口
│   │   └── mod.rs
│   ├── auth/              # 权限控制模块
│   │   ├── casbin_auth.rs # Casbin集成
│   │   └── mod.rs
│   ├── storage/           # 存储模块
│   │   ├── lancedb_storage.rs   # LanceDB实现
│   │   ├── sqlite_storage.rs    # SQLite实现
│   │   └── mod.rs
│   ├── plugins/           # 插件模块
│   ├── utils/             # 工具函数
│   └── lib.rs             # 库入口
├── examples/              # 示例代码
├── tests/                 # 测试用例
└── Cargo.toml
```

## 核心接口

### IAuth
权限控制接口，集成Casbin实现合规性检查。

### IStorage / IVectorStorage
存储接口，支持LanceDB和SQLite向量检索。

### IPlugin
插件接口，定义插件的生命周期和执行逻辑。

### IPluginManager
插件管理器，负责插件的加载、卸载和执行。

## 第三方库清单

| 库名 | 用途 | 版本 |
|------|------|------|
| casbin | 权限控制 | 2.0 |
| lancedb | 向量数据库 | 0.10 |
| rusqlite | SQLite数据库 | 0.29 |
| async-trait | 异步trait支持 | 0.1.74 |
| serde | 序列化/反序列化 | 1.0 |
| bincode | 二进制序列化 | 1.3 |
| log | 日志 | 0.4 |

## 使用示例

```rust
use digital_twin_sdk::{DigitalTwinSDK, SDKConfig};

let mut sdk = DigitalTwinSDK::new();
let config = SDKConfig {
    auth_config: Some(AuthConfig {
        model_path: "rbac_model.conf".to_string(),
        policy_path: "rbac_policy.csv".to_string(),
    }),
    storage_config: Some(StorageConfig {
        storage_type: StorageType::LanceDB,
        connection_string: "./data".to_string(),
        options: HashMap::new(),
    }),
    plugin_config: HashMap::new(),
};

sdk.initialize(config).await?;
```

## 插件化设计

SDK采用插件化架构，支持动态加载外部插件：

1. 实现 `IPlugin` trait
2. 通过 `PluginManager` 加载插件
3. 调用插件的 `execute` 方法执行任务

DADS医疗助手就是运行在这个SDK之上的一个插件实例。

## 许可证

MIT License