use std::collections::HashMap;

use digital_twin_sdk::core::interfaces::{PluginContext, PluginRequest, IPlugin};
use digital_twin_sdk::plugins::dads_plugin::DadsPlugin;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("=== DADS Plugin 双模式演示 ===\n");
    
    // ==================== Personal 模式（保命模式）====================
    println!("【模式1】Personal - 保命模式");
    println!("配置: dads_mode = \"personal\"\n");
    
    let personal_plugin = DadsPlugin::new();
    let mut personal_config = HashMap::new();
    personal_config.insert("dads_mode".to_string(), "personal".to_string());
    personal_config.insert("knowledge_base_path".to_string(), "./knowledge/personal".to_string());
    
    let personal_context = PluginContext {
        auth: None,
        storage: None,
        config: personal_config,
    };
    
    personal_plugin.initialize(&personal_context).await?;
    
    // 查询医保政策
    let request = PluginRequest {
        action: "query".to_string(),
        params: {
            let mut p = HashMap::new();
            p.insert("query".to_string(), "我的绩效考核有问题怎么办".to_string());
            p
        },
        data: None,
    };
    
    let response = personal_plugin.execute(request).await?;
    println!("用户问题：我的绩效考核有问题怎么办");
    println!("{}", response.message.unwrap_or_default());
    println!();
    
    personal_plugin.shutdown().await?;
    
    // ==================== Medical 模式（救人模式）====================
    println!("【模式2】Medical - 救人模式");
    println!("配置: dads_mode = \"medical\"\n");
    
    let medical_plugin = DadsPlugin::new();
    let mut medical_config = HashMap::new();
    medical_config.insert("dads_mode".to_string(), "medical".to_string());
    medical_config.insert("knowledge_base_path".to_string(), "./knowledge/medical".to_string());
    
    let medical_context = PluginContext {
        auth: None,
        storage: None,
        config: medical_config,
    };
    
    medical_plugin.initialize(&medical_context).await?;
    
    // 查询临床诊疗
    let request = PluginRequest {
        action: "query".to_string(),
        params: {
            let mut p = HashMap::new();
            p.insert("query".to_string(), "高血压患者的一线用药推荐".to_string());
            p
        },
        data: None,
    };
    
    let response = medical_plugin.execute(request).await?;
    println!("用户问题：高血压患者的一线用药推荐");
    println!("{}", response.message.unwrap_or_default());
    println!();
    
    medical_plugin.shutdown().await?;
    
    // ==================== 配置说明 ====================
    println!("=== 配置文件说明 ===");
    println!("请在 config.toml 中设置 dads_mode 来切换模式：");
    println!();
    println!("[dads]");
    println!("dads_mode = \"personal\"  # 或 \"medical\"");
    println!();
    println!("两种模式的知识库和输出风格完全不同：");
    println!("- Personal: 加载医保政策、绩效考核、劳动法、医疗纠纷判例");
    println!("- Medical:  加载临床诊疗指南、药典、典型病例库");
    
    Ok(())
}