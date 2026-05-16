use async_trait::async_trait;
use std::any::Any;
use std::collections::HashMap;
use std::sync::Arc;

use crate::core::interfaces::{IPlugin, PluginContext, PluginError, PluginRequest, PluginResponse};
use crate::plugins::dads_plugin::rag_strategies::{RagStrategy, PersonalRagStrategy, MedicalRagStrategy};

/// DADS插件运行模式
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DadsMode {
    /// 个人端 - 保命模式
    Personal,
    /// 医疗端 - 救人模式
    Medical,
}

impl DadsMode {
    pub fn from_str(mode: &str) -> Result<Self, PluginError> {
        match mode.to_lowercase().as_str() {
            "personal" => Ok(DadsMode::Personal),
            "medical" => Ok(DadsMode::Medical),
            _ => Err(PluginError::InvalidInput(
                format!("Unknown dads_mode: {}", mode)
            )),
        }
    }
}

/// DADS插件配置
#[derive(Debug, Clone)]
pub struct DadsConfig {
    pub mode: DadsMode,
    pub knowledge_base_path: String,
    pub model_endpoint: String,
}

impl DadsConfig {
    pub fn from_hashmap(config: &HashMap<String, String>) -> Result<Self, PluginError> {
        let mode_str = config.get("dads_mode")
            .map(|s| s.as_str())
            .unwrap_or("personal");
        
        let mode = DadsMode::from_str(mode_str)?;
        
        Ok(Self {
            mode,
            knowledge_base_path: config.get("knowledge_base_path")
                .cloned()
                .unwrap_or_else(|| "./knowledge".to_string()),
            model_endpoint: config.get("model_endpoint")
                .cloned()
                .unwrap_or_else(|| "http://localhost:8080".to_string()),
        })
    }
}

/// DADS插件主结构
pub struct DadsPlugin {
    id: String,
    name: String,
    version: String,
    description: String,
    config: Option<DadsConfig>,
    rag_strategy: Option<Arc<dyn RagStrategy>>,
}

impl DadsPlugin {
    pub fn new() -> Self {
        Self {
            id: "dads-plugin".to_string(),
            name: "DADS Dual-Mode Assistant".to_string(),
            version: "1.0.0".to_string(),
            description: "医疗/个人双模式智能助手插件".to_string(),
            config: None,
            rag_strategy: None,
        }
    }
    
    /// 根据模式创建对应的RAG策略
    fn create_rag_strategy(mode: &DadsMode) -> Arc<dyn RagStrategy> {
        match mode {
            DadsMode::Personal => Arc::new(PersonalRagStrategy::new()),
            DadsMode::Medical => Arc::new(MedicalRagStrategy::new()),
        }
    }
    
    /// 处理查询请求（核心RAG路由）
    async fn handle_query(&self, query: &str, context: &HashMap<String, String>) -> Result<PluginResponse, PluginError> {
        let strategy = self.rag_strategy.as_ref()
            .ok_or_else(|| PluginError::ExecuteError("RAG strategy not initialized".to_string()))?;
        
        // 1. 加载知识库
        let knowledge_base = strategy.load_knowledge_base().await?;
        
        // 2. 执行RAG检索
        let retrieved_docs = strategy.retrieve(query, &knowledge_base).await?;
        
        // 3. 构建系统提示词
        let system_prompt = strategy.build_system_prompt();
        
        // 4. 生成回答
        let response = strategy.generate_response(query, &retrieved_docs, &system_prompt).await?;
        
        Ok(PluginResponse {
            success: true,
            message: Some(response),
            data: None,
        })
    }
}

#[async_trait]
impl IPlugin for DadsPlugin {
    fn as_any(&self) -> &dyn Any {
        self
    }
    
    fn get_id(&self) -> &str {
        &self.id
    }
    
    fn get_name(&self) -> &str {
        &self.name
    }
    
    fn get_version(&self) -> &str {
        &self.version
    }
    
    fn get_description(&self) -> &str {
        &self.description
    }
    
    async fn initialize(&self, context: &PluginContext) -> Result<(), PluginError> {
        // 从配置中解析DadsConfig
        let config = DadsConfig::from_hashmap(&context.config)?;
        
        // 创建对应的RAG策略
        let strategy = Self::create_rag_strategy(&config.mode);
        
        // 初始化策略（加载知识库等）
        strategy.initialize(&config).await?;
        
        let self_mut = unsafe {
            let ptr = self as *const Self as *mut Self;
            &mut *ptr
        };
        self_mut.config = Some(config);
        self_mut.rag_strategy = Some(strategy);
        
        Ok(())
    }
    
    async fn execute(&self, request: PluginRequest) -> Result<PluginResponse, PluginError> {
        match request.action.as_str() {
            "query" => {
                let query = request.params.get("query")
                    .ok_or_else(|| PluginError::InvalidInput("Missing query parameter".to_string()))?;
                self.handle_query(query, &request.params).await
            }
            "get_mode" => {
                let mode = self.config.as_ref()
                    .map(|c| format!("{:?}", c.mode))
                    .unwrap_or_else(|| "Unknown".to_string());
                Ok(PluginResponse {
                    success: true,
                    message: Some(format!("Current mode: {}", mode)),
                    data: None,
                })
            }
            "switch_mode" => {
                // 动态切换模式（需要重新初始化）
                let new_mode = request.params.get("mode")
                    .ok_or_else(|| PluginError::InvalidInput("Missing mode parameter".to_string()))?;
                
                Err(PluginError::ExecuteError(
                    format!("Mode switching not supported at runtime. Please restart with dads_mode='{}'", new_mode)
                ))
            }
            _ => Err(PluginError::InvalidInput(format!("Unknown action: {}", request.action))),
        }
    }
    
    async fn shutdown(&self) -> Result<(), PluginError> {
        if let Some(strategy) = &self.rag_strategy {
            strategy.shutdown().await?;
        }
        Ok(())
    }
}