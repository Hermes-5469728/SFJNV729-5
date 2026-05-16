use digital_twin_sdk::core::interfaces::{StorageConfig, StorageType};
use digital_twin_sdk::storage::LanceDBStorage;
use std::collections::HashMap;

#[tokio::test]
async fn test_lancedb_storage() {
    let mut storage = LanceDBStorage::new();
    
    let config = StorageConfig {
        storage_type: StorageType::LanceDB,
        connection_string: "./test_data".to_string(),
        options: HashMap::new(),
    };
    
    storage.init(&config).await.expect("Failed to init storage");
    
    storage.create_collection("test_collection", None).await.expect("Failed to create collection");
    
    let vector = vec![0.1; 1536];
    storage.insert_vector("test_collection", &vector, None).await.expect("Failed to insert vector");
    
    let results = storage.search_vectors("test_collection", &vector, 5).await.expect("Failed to search");
    assert!(!results.is_empty());
    
    storage.drop_collection("test_collection").await.expect("Failed to drop collection");
}