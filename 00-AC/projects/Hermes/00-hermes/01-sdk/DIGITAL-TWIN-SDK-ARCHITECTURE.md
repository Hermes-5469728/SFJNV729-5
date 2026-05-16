# 个人数字孪生底座 SDK - 详细架构设计

## 一、架构总览

### 数学模型

SDK 抽象为一个基础空间 **S**，包含两个核心算子：

| 算子 | 数学表达 | 功能描述 |
|------|---------|---------|
| **算子 A (Access Control)** | f(x) → {0, 1} | 权限过滤，合规性检查 |
| **算子 R (RAG/Data)** | g(x) → y | 向量检索，知识查询 |

**DADS 插件**作为空间中的特定向量，调用 f(x) 和 g(x) 完成任务。

### 分层架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      插件层 (Plugins)                        │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐   │
│   │  DADS   │  │ PluginB │  │ PluginC │  │   ...       │   │
│   │ (医疗)  │  │         │  │         │  │             │   │
│   └────┬────┘  └────┬────┘  └────┬────┘  └──────┬──────┘   │
│        │            │            │               │          │
├────────┼────────────┼────────────┼───────────────┼──────────┤
│                   管理层 (Manager)                          │
│         ┌─────────────────────────────────────┐             │
│         │        PluginManager                │             │
│         │  - 插件加载/卸载                     │             │
│         │  - 生命周期管理                      │             │
│         │  - 执行调度                         │             │
│         └───────────────┬─────────────────────┘             │
├──────────────────────────┼───────────────────────────────────┤
│                   核心接口层 (Interfaces)                    │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │    IAuth    │  │ IStorage    │  │  IPlugin    │        │
│   │  (算子A)    │  │ (算子R)     │  │             │        │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
├──────────┼────────────────┼────────────────┼────────────────┤
│                   实现层 (Implementations)                   │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │ CasbinAuth  │  │ LanceDB     │  │  SQLite     │        │
│   │             │  │ Storage     │  │  Storage    │        │
│   └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│                    基础设施层 (Infrastructure)              │
│              ┌─────────┐  ┌───────────┐                    │
│              │  Casbin │  │  LanceDB  │                    │
│              │         │  │  / SQLite │                    │
│              └─────────┘  └───────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、核心接口设计

### 2.1 IAuth - 算子A（权限控制）

```rust
pub trait IAuth: Send + Sync {
    fn as_any(&self) -> &dyn Any;
    
    // f(subject, object, action) → {0, 1}
    async fn enforce(
        &self,
        subject: &str,   // 用户/角色
        object: &str,    // 资源
        action: &str,    // 操作
    ) -> Result<bool, AuthError>;
    
    async fn add_policy(&self, subject: &str, object: &str, action: &str) -> Result<(), AuthError>;
    async fn remove_policy(&self, subject: &str, object: &str, action: &str) -> Result<(), AuthError>;
    async fn load_policy(&self) -> Result<(), AuthError>;
    async fn save_policy(&self) -> Result<(), AuthError>;
}
```

### 2.2 IStorage / IVectorStorage - 算子R（数据检索）

```rust
pub trait IStorage: Send + Sync {
    async fn insert(&self, collection: &str, data: &[u8]) -> Result<String, StorageError>;
    async fn query(&self, collection: &str, query: &Query) -> Result<Vec<QueryResult>, StorageError>;
    async fn update(&self, collection: &str, id: &str, data: &[u8]) -> Result<(), StorageError>;
    async fn delete(&self, collection: &str, id: &str) -> Result<(), StorageError>;
    async fn create_collection(&self, name: &str, schema: Option<&str>) -> Result<(), StorageError>;
    async fn drop_collection(&self, name: &str) -> Result<(), StorageError>;
}

pub trait IVectorStorage: IStorage {
    // g(query_vector) → [(id, vector, score), ...]
    async fn insert_vector(&self, collection: &str, vector: &[f32], metadata: Option<&HashMap<String, String>>) -> Result<String, StorageError>;
    async fn search_vectors(&self, collection: &str, query_vector: &[f32], top_k: usize) -> Result<Vec<VectorSearchResult>, StorageError>;
}
```

### 2.3 IPlugin - 插件接口

```rust
pub trait IPlugin: Send + Sync {
    fn get_id(&self) -> &str;
    fn get_name(&self) -> &str;
    fn get_version(&self) -> &str;
    fn get_description(&self) -> &str;
    
    async fn initialize(&self, context: &PluginContext) -> Result<(), PluginError>;
    async fn execute(&self, request: PluginRequest) -> Result<PluginResponse, PluginError>;
    async fn shutdown(&self) -> Result<(), PluginError>;
}
```

### 2.4 IPluginManager - 插件管理器

```rust
pub trait IPluginManager: Send + Sync {
    async fn load_plugin(&self, path: &str) -> Result<String, PluginError>;
    async fn unload_plugin(&self, plugin_id: &str) -> Result<(), PluginError>;
    async fn get_plugin(&self, plugin_id: &str) -> Option<Box<dyn IPlugin>>;
    async fn list_plugins(&self) -> Vec<PluginInfo>;
    async fn execute_plugin(&self, plugin_id: &str, request: PluginRequest) -> Result<PluginResponse, PluginError>;
}
```

---

## 三、目录结构

```
digital_twin_sdk/
├── src/
│   ├── core/
│   │   ├── interfaces.rs      # 核心接口定义
│   │   ├── plugin_manager.rs  # 插件管理器
│   │   ├── sdk.rs             # SDK主入口
│   │   └── mod.rs
│   ├── auth/
│   │   ├── casbin_auth.rs     # Casbin集成
│   │   └── mod.rs
│   ├── storage/
│   │   ├── lancedb_storage.rs # LanceDB实现
│   │   ├── sqlite_storage.rs  # SQLite实现
│   │   └── mod.rs
│   ├── plugins/               # 插件模块(预留)
│   ├── utils/                 # 工具函数(预留)
│   └── lib.rs                 # 库导出
├── examples/
│   ├── basic_usage.rs         # SDK基础用法
│   └── dads_plugin.rs         # DADS插件示例
├── tests/
│   ├── auth_test.rs           # 权限测试
│   └── storage_test.rs        # 存储测试
├── Cargo.toml
└── README.md
```

---

## 四、数据流与交互

### DADS插件典型调用链

```
用户请求医疗知识查询
       │
       ▼
DADS.execute(PluginRequest)
       │
       ├──► IAuth.enforce("user1", "medical_data", "read") → true
       │
       └──► IVectorStorage.search_vectors("medical_knowledge", query_vec, 5)
                   │
                   ▼
            返回相似医疗知识向量
                   │
                   ▼
       PluginResponse { success: true, data: ... }
```

---

## 五、关键设计模式

| 模式 | 应用位置 | 作用 |
|------|---------|------|
| 策略模式 | IAuth, IStorage | 多种实现可互换 |
| 插件模式 | IPlugin, PluginManager | 动态加载扩展 |
| 外观模式 | DigitalTwinSDK | 统一SDK入口 |
| 依赖注入 | PluginContext | 插件获取共享服务 |

---

## 六、第三方库清单

| 库名 | 用途 | 版本 |
|------|------|------|
| casbin | 权限控制 | 2.0 |
| lancedb | 向量数据库 | 0.10 |
| rusqlite | SQLite数据库 | 0.29 |
| async-trait | 异步trait支持 | 0.1.74 |
| serde / serde_json | 序列化 | 1.0 |
| bincode | 二进制序列化 | 1.3 |

---

## 七、安全性设计

| 安全特性 | 实现方式 |
|---------|---------|
| 最小权限原则 | Casbin RBAC/ABAC策略 |
| 数据隔离 | 插件通过接口访问资源 |
| 策略热更新 | IAuth.reload_policy() |
| 输入验证 | 各接口层参数校验 |