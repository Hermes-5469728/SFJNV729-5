use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

use crate::core::interfaces::{
    IPlugin, IPluginManager, PluginContext, PluginError, PluginInfo, PluginRequest,
    PluginResponse, PluginStatus,
};

pub struct PluginManager {
    plugins: Arc<RwLock<HashMap<String, Box<dyn IPlugin>>>>,
    plugin_info: Arc<RwLock<HashMap<String, PluginInfo>>>,
    context: PluginContext,
}

impl PluginManager {
    pub fn new(context: PluginContext) -> Self {
        Self {
            plugins: Arc::new(RwLock::new(HashMap::new())),
            plugin_info: Arc::new(RwLock::new(HashMap::new())),
            context,
        }
    }
}

#[async_trait]
impl IPluginManager for PluginManager {
    async fn load_plugin(&self, path: &str) -> Result<String, PluginError> {
        let plugin = self.load_plugin_from_path(path).await?;
        let plugin_id = plugin.get_id().to_string();
        
        let info = PluginInfo {
            id: plugin_id.clone(),
            name: plugin.get_name().to_string(),
            version: plugin.get_version().to_string(),
            description: plugin.get_description().to_string(),
            status: PluginStatus::Loaded,
        };
        
        self.plugins.write().unwrap().insert(plugin_id.clone(), plugin);
        self.plugin_info.write().unwrap().insert(plugin_id.clone(), info);
        
        Ok(plugin_id)
    }
    
    async fn unload_plugin(&self, plugin_id: &str) -> Result<(), PluginError> {
        let plugin = self.plugins.write().unwrap().remove(plugin_id)
            .ok_or_else(|| PluginError::PluginNotFound(plugin_id.to_string()))?;
        
        plugin.shutdown().await?;
        self.plugin_info.write().unwrap().remove(plugin_id);
        
        Ok(())
    }
    
    async fn get_plugin(&self, plugin_id: &str) -> Option<Box<dyn IPlugin>> {
        self.plugins.read().unwrap().get(plugin_id).cloned()
    }
    
    async fn list_plugins(&self) -> Vec<PluginInfo> {
        self.plugin_info.read().unwrap().values().cloned().collect()
    }
    
    async fn execute_plugin(
        &self,
        plugin_id: &str,
        request: PluginRequest,
    ) -> Result<PluginResponse, PluginError> {
        let plugin = self.plugins.read().unwrap().get(plugin_id)
            .ok_or_else(|| PluginError::PluginNotFound(plugin_id.to_string()))?;
        
        plugin.execute(request).await
    }
}

impl PluginManager {
    async fn load_plugin_from_path(&self, path: &str) -> Result<Box<dyn IPlugin>, PluginError> {
        Err(PluginError::LoadError(
            format!("Plugin loading from {} not implemented", path),
        ))
    }
}