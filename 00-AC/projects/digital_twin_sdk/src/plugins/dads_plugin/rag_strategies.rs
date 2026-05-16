use async_trait::async_trait;
use std::collections::HashMap;

use crate::plugins::dads_plugin::dads_plugin::DadsConfig;
use crate::core::interfaces::PluginError;

/// RAG策略接口 - 策略模式
#[async_trait]
pub trait RagStrategy: Send + Sync {
    /// 初始化策略
    async fn initialize(&self, config: &DadsConfig) -> Result<(), PluginError>;
    
    /// 获取知识库列表
    fn get_knowledge_bases(&self) -> Vec<String>;
    
    /// 加载知识库
    async fn load_knowledge_base(&self) -> Result<Vec<KnowledgeDocument>, PluginError>;
    
    /// 检索相关文档
    async fn retrieve(&self, query: &str, knowledge_base: &[KnowledgeDocument]) -> Result<Vec<KnowledgeDocument>, PluginError>;
    
    /// 构建系统提示词
    fn build_system_prompt(&self) -> String;
    
    /// 生成回答
    async fn generate_response(&self, query: &str, context: &[KnowledgeDocument], system_prompt: &str) -> Result<String, PluginError>;
    
    /// 关闭策略
    async fn shutdown(&self) -> Result<(), PluginError>;
}

/// 知识文档结构
#[derive(Debug, Clone)]
pub struct KnowledgeDocument {
    pub id: String,
    pub source: String,
    pub content: String,
    pub metadata: HashMap<String, String>,
}

// ==================== Personal模式 - 保命模式 ====================

pub struct PersonalRagStrategy {
    knowledge_bases: Vec<String>,
}

impl PersonalRagStrategy {
    pub fn new() -> Self {
        Self {
            knowledge_bases: vec![
                "医保政策".to_string(),
                "绩效考核细则".to_string(),
                "劳动法".to_string(),
                "医疗纠纷判例".to_string(),
            ],
        }
    }
}

#[async_trait]
impl RagStrategy for PersonalRagStrategy {
    async fn initialize(&self, _config: &DadsConfig) -> Result<(), PluginError> {
        // 加载个人端知识库
        Ok(())
    }
    
    fn get_knowledge_bases(&self) -> Vec<String> {
        self.knowledge_bases.clone()
    }
    
    async fn load_knowledge_base(&self) -> Result<Vec<KnowledgeDocument>, PluginError> {
        // 模拟加载个人端知识库
        let docs = vec![
            KnowledgeDocument {
                id: "1".to_string(),
                source: "医保政策".to_string(),
                content: "医生应了解医保报销比例和违规处罚条款...".to_string(),
                metadata: HashMap::new(),
            },
            KnowledgeDocument {
                id: "2".to_string(),
                source: "绩效考核细则".to_string(),
                content: "绩效考核包括门诊量、手术量、患者满意度...".to_string(),
                metadata: HashMap::new(),
            },
            KnowledgeDocument {
                id: "3".to_string(),
                source: "劳动法".to_string(),
                content: "医生加班应获得相应补偿，年假权利...".to_string(),
                metadata: HashMap::new(),
            },
            KnowledgeDocument {
                id: "4".to_string(),
                source: "医疗纠纷判例".to_string(),
                content: "典型医疗纠纷案例分析及风险防范...".to_string(),
                metadata: HashMap::new(),
            },
        ];
        Ok(docs)
    }
    
    async fn retrieve(&self, query: &str, knowledge_base: &[KnowledgeDocument]) -> Result<Vec<KnowledgeDocument>, PluginError> {
        // 简单的关键词匹配检索
        let results: Vec<KnowledgeDocument> = knowledge_base
            .iter()
            .filter(|doc| {
                query.to_lowercase().contains(&doc.source.to_lowercase()) ||
                doc.content.to_lowercase().contains(&query.to_lowercase())
            })
            .cloned()
            .collect();
        
        if results.is_empty() {
            // 如果没有匹配，返回所有文档
            Ok(knowledge_base.to_vec())
        } else {
            Ok(results)
        }
    }
    
    fn build_system_prompt(&self) -> String {
        "你是一个经验丰富的医生职业顾问。请基于检索到的政策，帮助用户规避职业风险，优化绩效，或规划职业退路。\n\n输出风格要求：\n- 务实：给出具体可操作的建议\n- 谨慎：提醒潜在风险和注意事项\n- 保护性强：优先考虑医生的合法权益和职业安全".to_string()
    }
    
    async fn generate_response(&self, query: &str, context: &[KnowledgeDocument], system_prompt: &str) -> Result<String, PluginError> {
        // 构建提示词
        let context_str = context
            .iter()
            .map(|doc| format!("[{}]: {}", doc.source, doc.content))
            .collect::<Vec<_>>()
            .join("\n\n");
        
        let prompt = format!(
            "{system_prompt}\n\n参考知识库内容：\n{context}\n\n用户问题：{query}\n\n请基于以上信息，给出务实、谨慎、保护性强的建议：",
            system_prompt = system_prompt,
            context = context_str,
            query = query
        );
        
        // 这里应该调用LLM API，现在模拟返回
        Ok(format!(
            "【保命模式建议】\n\n基于您的查询，我为您整理了以下建议：\n\n1. 风险识别：建议先了解当前医院的绩效考核细则和医保政策要求...\n\n2. 应对策略：\n   - 保留相关工作记录和沟通记录\n   - 了解劳动法规保护条款\n   - 必要时寻求专业法律咨询\n\n3. 长期规划：\n   - 建立个人职业风险档案\n   - 关注行业动态和政策变化\n   - 考虑多元化职业发展路径\n\n[基于知识库：{}]",
            self.knowledge_bases.join(", ")
        ))
    }
    
    async fn shutdown(&self) -> Result<(), PluginError> {
        Ok(())
    }
}

// ==================== Medical模式 - 救人模式 ====================

pub struct MedicalRagStrategy {
    knowledge_bases: Vec<String>,
}

impl MedicalRagStrategy {
    pub fn new() -> Self {
        Self {
            knowledge_bases: vec![
                "临床诊疗指南".to_string(),
                "药典".to_string(),
                "典型病例库".to_string(),
            ],
        }
    }
}

#[async_trait]
impl RagStrategy for MedicalRagStrategy {
    async fn initialize(&self, _config: &DadsConfig) -> Result<(), PluginError> {
        // 加载医疗端知识库
        Ok(())
    }
    
    fn get_knowledge_bases(&self) -> Vec<String> {
        self.knowledge_bases.clone()
    }
    
    async fn load_knowledge_base(&self) -> Result<Vec<KnowledgeDocument>, PluginError> {
        // 模拟加载医疗端知识库
        let docs = vec![
            KnowledgeDocument {
                id: "1".to_string(),
                source: "临床诊疗指南".to_string(),
                content: "根据最新指南，对于XX疾病的诊断标准包括...".to_string(),
                metadata: HashMap::new(),
            },
            KnowledgeDocument {
                id: "2".to_string(),
                source: "药典".to_string(),
                content: "药物剂量、禁忌症、相互作用...".to_string(),
                metadata: HashMap::new(),
            },
            KnowledgeDocument {
                id: "3".to_string(),
                source: "典型病例库".to_string(),
                content: "类似病例的诊疗经验和预后分析...".to_string(),
                metadata: HashMap::new(),
            },
        ];
        Ok(docs)
    }
    
    async fn retrieve(&self, query: &str, knowledge_base: &[KnowledgeDocument]) -> Result<Vec<KnowledgeDocument>, PluginError> {
        // 专业的医学检索逻辑
        let results: Vec<KnowledgeDocument> = knowledge_base
            .iter()
            .filter(|doc| {
                query.to_lowercase().contains(&doc.source.to_lowercase()) ||
                doc.content.to_lowercase().contains(&query.to_lowercase())
            })
            .cloned()
            .collect();
        
        if results.is_empty() {
            Ok(knowledge_base.to_vec())
        } else {
            Ok(results)
        }
    }
    
    fn build_system_prompt(&self) -> String {
        "你是一个严谨的临床辅助专家。请基于最新指南，为医生提供诊断建议和用药参考。\n\n输出风格要求：\n- 专业：使用准确的医学术语和最新诊疗标准\n- 精准：基于循证医学证据给出建议\n- 符合医学规范：遵循临床诊疗指南和药典要求\n\n重要提示：本建议仅供参考，最终诊疗决策应由主治医生根据患者具体情况做出。".to_string()
    }
    
    async fn generate_response(&self, query: &str, context: &[KnowledgeDocument], system_prompt: &str) -> Result<String, PluginError> {
        let context_str = context
            .iter()
            .map(|doc| format!("[{}]: {}", doc.source, doc.content))
            .collect::<Vec<_>>()
            .join("\n\n");
        
        let prompt = format!(
            "{system_prompt}\n\n参考知识库内容：\n{context}\n\n临床问题：{query}\n\n请基于以上信息，给出专业、精准的诊疗建议：",
            system_prompt = system_prompt,
            context = context_str,
            query = query
        );
        
        Ok(format!(
            "【救人模式建议】\n\n基于最新临床诊疗指南，为您提供以下参考：\n\n1. 诊断参考：\n   - 请结合患者症状、体征和辅助检查综合判断\n   - 注意鉴别诊断，排除相关疾病\n\n2. 治疗建议：\n   - 首选治疗方案应符合当前临床指南推荐\n   - 注意药物剂量调整和禁忌症筛查\n\n3. 注意事项：\n   - 密切监测患者病情变化\n   - 必要时请相关科室会诊\n\n[基于知识库：{}]\n\n⚠️ 免责声明：本建议仅供参考，不构成最终诊疗决策。",
            self.knowledge_bases.join(", ")
        ))
    }
    
    async fn shutdown(&self) -> Result<(), PluginError> {
        Ok(())
    }
}

// ==================== 策略工厂（便于扩展第三种模式） ====================

pub struct RagStrategyFactory;

impl RagStrategyFactory {
    pub fn create_strategy(mode: &str) -> Result<Box<dyn RagStrategy>, PluginError> {
        match mode.to_lowercase().as_str() {
            "personal" => Ok(Box::new(PersonalRagStrategy::new())),
            "medical" => Ok(Box::new(MedicalRagStrategy::new())),
            // 未来可以在这里添加第三种模式
            // "research" => Ok(Box::new(ResearchRagStrategy::new())),
            _ => Err(PluginError::InvalidInput(format!(
                "Unknown RAG strategy mode: {}. Available: personal, medical",
                mode
            ))),
        }
    }
}