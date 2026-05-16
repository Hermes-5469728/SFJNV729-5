use async_trait::async_trait;
use std::any::Any;

use digital_twin_sdk::core::interfaces::{
    IPlugin, PluginContext, PluginError, PluginRequest, PluginResponse,
};

pub struct DADSPlugin;

impl DADSPlugin {
    pub fn new() -> Self {
        Self
    }
}

#[async_trait]
impl IPlugin for DADSPlugin {
    fn as_any(&self) -> &dyn Any {
        self
    }
    
    fn get_id(&self) -> &str {
        "dads-plugin"
    }
    
    fn get_name(&self) -> &str {
        "DADS Medical Assistant"
    }
    
    fn get_version(&self) -> &str {
        "1.0.0"
    }
    
    fn get_description(&self) -> &str {
        "医疗助手插件 - 基于个人数字孪生底座的医疗知识服务"
    }
    
    async fn initialize(&self, context: &PluginContext) -> Result<(), PluginError> {
        Ok(())
    }
    
    async fn execute(
        &self,
        request: PluginRequest,
    ) -> Result<PluginResponse, PluginError> {
        match request.action.as_str() {
            "query_medical_knowledge" => {
                let query = request.params.get("query").ok_or_else(|| {
                    PluginError::InvalidInput("Missing query parameter".to_string())
                })?;
                
                Ok(PluginResponse {
                    success: true,
                    message: Some(format!("Querying medical knowledge for: {}", query)),
                    data: None,
                })
            }
            _ => Err(PluginError::InvalidInput(
                format!("Unknown action: {}", request.action),
            )),
        }
    }
    
    async fn shutdown(&self) -> Result<(), PluginError> {
        Ok(())
    }
}