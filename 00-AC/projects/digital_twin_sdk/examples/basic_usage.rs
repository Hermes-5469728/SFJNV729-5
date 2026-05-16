use digital_twin_sdk::core::interfaces::StorageType;
use digital_twin_sdk::{DigitalTwinSDK, SDKConfig};
use std::collections::HashMap;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let storage_config = digital_twin_sdk::core::interfaces::StorageConfig {
        storage_type: StorageType::LanceDB,
        connection_string: "./data".to_string(),
        options: HashMap::new(),
    };
    
    let mut sdk = DigitalTwinSDK::new();
    
    let config = SDKConfig {
        auth_config: None,
        storage_config: Some(storage_config),
        plugin_config: HashMap::new(),
    };
    
    sdk.initialize(config).await?;
    
    println!("SDK initialized successfully!");
    
    if let Some(storage) = sdk.get_storage() {
        storage.create_collection("medical_records", None).await?;
        println!("Collection created");
    }
    
    Ok(())
}