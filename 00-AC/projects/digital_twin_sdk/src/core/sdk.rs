use std::sync::Arc;

use crate::core::interfaces::{
    IAuth, IStorage, IPluginManager, PluginContext, PluginManager, StorageConfig,
    StorageType,
};
use crate::storage::LanceDBStorage;

pub struct DigitalTwinSDK {
    auth: Option<Arc<dyn IAuth>>,
    storage: Option<Arc<dyn IStorage>>,
    plugin_manager: Option<Arc<dyn IPluginManager>>,
}

impl DigitalTwinSDK {
    pub fn new() -> Self {
        Self {
            auth: None,
            storage: None,
            plugin_manager: None,
        }
    }
    
    pub async fn with_auth(mut self, auth: Arc<dyn IAuth>) -> Self {
        self.auth = Some(auth);
        self
    }
    
    pub async fn with_storage(mut self, storage: Arc<dyn IStorage>) -> Self {
        self.storage = Some(storage);
        self
    }
    
    pub async fn initialize(&mut self, config: SDKConfig) -> Result<(), SDKError> {
        if let Some(auth_config) = &config.auth_config {
            let auth = crate::auth::CasbinAuth::new(
                &auth_config.model_path,
                &auth_config.policy_path,
            ).await?;
            self.auth = Some(Arc::new(auth));
        }
        
        if let Some(storage_config) = &config.storage_config {
            let storage = match storage_config.storage_type {
                StorageType::LanceDB => {
                    let mut lancedb = LanceDBStorage::new();
                    lancedb.init(storage_config).await?;
                    Arc::new(lancedb) as Arc<dyn IStorage>
                }
                StorageType::SQLite | StorageType::SQLiteVector => {
                    let mut sqlite = crate::storage::SQLiteStorage::new();
                    sqlite.init(storage_config).await?;
                    Arc::new(sqlite) as Arc<dyn IStorage>
                }
            };
            self.storage = Some(storage);
        }
        
        let context = PluginContext {
            auth: self.auth.clone().map(|a| Box::new(a.as_ref()) as Box<dyn IAuth>),
            storage: self.storage.clone().map(|s| Box::new(s.as_ref()) as Box<dyn IStorage>),
            config: config.plugin_config,
        };
        
        self.plugin_manager = Some(Arc::new(PluginManager::new(context)));
        
        Ok(())
    }
    
    pub fn get_auth(&self) -> Option<&Arc<dyn IAuth>> {
        self.auth.as_ref()
    }
    
    pub fn get_storage(&self) -> Option<&Arc<dyn IStorage>> {
        self.storage.as_ref()
    }
    
    pub fn get_plugin_manager(&self) -> Option<&Arc<dyn IPluginManager>> {
        self.plugin_manager.as_ref()
    }
}

#[derive(Debug, Clone)]
pub struct SDKConfig {
    pub auth_config: Option<AuthConfig>,
    pub storage_config: Option<StorageConfig>,
    pub plugin_config: std::collections::HashMap<String, String>,
}

#[derive(Debug, Clone)]
pub struct AuthConfig {
    pub model_path: String,
    pub policy_path: String,
}

#[derive(Debug)]
pub enum SDKError {
    AuthError(crate::core::interfaces::AuthError),
    StorageError(crate::core::interfaces::StorageError),
    PluginError(crate::core::interfaces::PluginError),
    InvalidConfig(String),
}