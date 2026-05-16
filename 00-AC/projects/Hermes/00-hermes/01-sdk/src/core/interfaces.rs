use async_trait::async_trait;
use std::any::Any;
use std::collections::HashMap;

#[async_trait]
pub trait IAuth: Send + Sync {
    fn as_any(&self) -> &dyn Any;
    
    async fn enforce(
        &self,
        subject: &str,
        object: &str,
        action: &str,
    ) -> Result<bool, AuthError>;
    
    async fn add_policy(
        &self,
        subject: &str,
        object: &str,
        action: &str,
    ) -> Result<(), AuthError>;
    
    async fn remove_policy(
        &self,
        subject: &str,
        object: &str,
        action: &str,
    ) -> Result<(), AuthError>;
    
    async fn load_policy(&self) -> Result<(), AuthError>;
    
    async fn save_policy(&self) -> Result<(), AuthError>;
}

#[async_trait]
pub trait IStorage: Send + Sync {
    fn as_any(&self) -> &dyn Any;
    
    async fn init(&self, config: &StorageConfig) -> Result<(), StorageError>;
    
    async fn insert(&self, collection: &str, data: &[u8]) -> Result<String, StorageError>;
    
    async fn query(&self, collection: &str, query: &Query) -> Result<Vec<QueryResult>, StorageError>;
    
    async fn update(&self, collection: &str, id: &str, data: &[u8]) -> Result<(), StorageError>;
    
    async fn delete(&self, collection: &str, id: &str) -> Result<(), StorageError>;
    
    async fn create_collection(&self, name: &str, schema: Option<&str>) -> Result<(), StorageError>;
    
    async fn drop_collection(&self, name: &str) -> Result<(), StorageError>;
}

#[async_trait]
pub trait IVectorStorage: IStorage {
    async fn insert_vector(
        &self,
        collection: &str,
        vector: &[f32],
        metadata: Option<&HashMap<String, String>>,
    ) -> Result<String, StorageError>;
    
    async fn search_vectors(
        &self,
        collection: &str,
        query_vector: &[f32],
        top_k: usize,
    ) -> Result<Vec<VectorSearchResult>, StorageError>;
}

#[async_trait]
pub trait IPlugin: Send + Sync {
    fn as_any(&self) -> &dyn Any;
    
    fn get_id(&self) -> &str;
    
    fn get_name(&self) -> &str;
    
    fn get_version(&self) -> &str;
    
    fn get_description(&self) -> &str;
    
    async fn initialize(&self, context: &PluginContext) -> Result<(), PluginError>;
    
    async fn execute(
        &self,
        request: PluginRequest,
    ) -> Result<PluginResponse, PluginError>;
    
    async fn shutdown(&self) -> Result<(), PluginError>;
}

#[async_trait]
pub trait IPluginManager: Send + Sync {
    async fn load_plugin(&self, path: &str) -> Result<String, PluginError>;
    
    async fn unload_plugin(&self, plugin_id: &str) -> Result<(), PluginError>;
    
    async fn get_plugin(&self, plugin_id: &str) -> Option<Box<dyn IPlugin>>;
    
    async fn list_plugins(&self) -> Vec<PluginInfo>;
    
    async fn execute_plugin(
        &self,
        plugin_id: &str,
        request: PluginRequest,
    ) -> Result<PluginResponse, PluginError>;
}

#[derive(Debug, Clone)]
pub struct StorageConfig {
    pub storage_type: StorageType,
    pub connection_string: String,
    pub options: HashMap<String, String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StorageType {
    LanceDB,
    SQLite,
    SQLiteVector,
}

#[derive(Debug, Clone)]
pub struct Query {
    pub filters: Option<HashMap<String, String>>,
    pub vector_query: Option<Vec<f32>>,
    pub limit: Option<usize>,
    pub offset: Option<usize>,
}

#[derive(Debug, Clone)]
pub struct QueryResult {
    pub id: String,
    pub data: Vec<u8>,
    pub score: Option<f32>,
}

#[derive(Debug, Clone)]
pub struct VectorSearchResult {
    pub id: String,
    pub vector: Vec<f32>,
    pub metadata: Option<HashMap<String, String>>,
    pub score: f32,
}

#[derive(Debug, Clone)]
pub struct PluginContext {
    pub auth: Option<Box<dyn IAuth>>,
    pub storage: Option<Box<dyn IStorage>>,
    pub config: HashMap<String, String>,
}

#[derive(Debug, Clone)]
pub struct PluginRequest {
    pub action: String,
    pub params: HashMap<String, String>,
    pub data: Option<Vec<u8>>,
}

#[derive(Debug, Clone)]
pub struct PluginResponse {
    pub success: bool,
    pub message: Option<String>,
    pub data: Option<Vec<u8>>,
}

#[derive(Debug, Clone)]
pub struct PluginInfo {
    pub id: String,
    pub name: String,
    pub version: String,
    pub description: String,
    pub status: PluginStatus,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PluginStatus {
    Loaded,
    Initialized,
    Running,
    Error,
}

#[derive(Debug)]
pub enum AuthError {
    CasbinError(String),
    PolicyNotFound,
    InvalidInput(String),
    InternalError(String),
}

#[derive(Debug)]
pub enum StorageError {
    ConnectionError(String),
    QueryError(String),
    CollectionNotFound(String),
    InvalidInput(String),
    InternalError(String),
}

#[derive(Debug)]
pub enum PluginError {
    LoadError(String),
    InitializeError(String),
    ExecuteError(String),
    PluginNotFound(String),
    InvalidInput(String),
    InternalError(String),
}