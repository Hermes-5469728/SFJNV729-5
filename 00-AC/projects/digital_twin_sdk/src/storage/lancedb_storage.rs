use async_trait::async_trait;
use lancedb::{Connection, Table};
use std::any::Any;
use std::collections::HashMap;

use crate::core::interfaces::{
    IVectorStorage, Query, QueryResult, StorageConfig, StorageError, StorageType,
    VectorSearchResult,
};

pub struct LanceDBStorage {
    connection: Option<Connection>,
    tables: HashMap<String, Table>,
}

impl LanceDBStorage {
    pub fn new() -> Self {
        Self {
            connection: None,
            tables: HashMap::new(),
        }
    }
}

#[async_trait]
impl IVectorStorage for LanceDBStorage {
    async fn insert_vector(
        &self,
        collection: &str,
        vector: &[f32],
        metadata: Option<&HashMap<String, String>>,
    ) -> Result<String, StorageError> {
        let table = self.tables.get(collection)
            .ok_or_else(|| StorageError::CollectionNotFound(collection.to_string()))?;
        
        let mut row = lancedb::Row::new();
        row.push("vector", vector);
        
        if let Some(meta) = metadata {
            for (key, value) in meta {
                row.push(key, value);
            }
        }
        
        table.insert(&[row]).await
            .map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        Ok("inserted".to_string())
    }
    
    async fn search_vectors(
        &self,
        collection: &str,
        query_vector: &[f32],
        top_k: usize,
    ) -> Result<Vec<VectorSearchResult>, StorageError> {
        let table = self.tables.get(collection)
            .ok_or_else(|| StorageError::CollectionNotFound(collection.to_string()))?;
        
        let results = table.query()
            .vector_search(query_vector, top_k)
            .execute()
            .await
            .map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        let mut output = Vec::new();
        for result in results {
            let vector: Vec<f32> = result.get("vector").unwrap_or_default();
            let score: f32 = result.get("score").unwrap_or(0.0);
            
            output.push(VectorSearchResult {
                id: result.get("_row_id").unwrap_or_default(),
                vector,
                metadata: None,
                score,
            });
        }
        
        Ok(output)
    }
}

#[async_trait]
impl crate::core::interfaces::IStorage for LanceDBStorage {
    fn as_any(&self) -> &dyn Any {
        self
    }
    
    async fn init(&self, config: &StorageConfig) -> Result<(), StorageError> {
        if config.storage_type != StorageType::LanceDB {
            return Err(StorageError::InvalidInput(
                "Invalid storage type for LanceDB".to_string(),
            ));
        }
        
        let connection = Connection::open(&config.connection_string)
            .await
            .map_err(|e| StorageError::ConnectionError(e.to_string()))?;
        
        let self_mut = unsafe {
            let ptr = self as *const Self as *mut Self;
            &mut *ptr
        };
        self_mut.connection = Some(connection);
        
        Ok(())
    }
    
    async fn insert(&self, collection: &str, data: &[u8]) -> Result<String, StorageError> {
        let table = self.tables.get(collection)
            .ok_or_else(|| StorageError::CollectionNotFound(collection.to_string()))?;
        
        let row = lancedb::Row::new();
        table.insert(&[row]).await
            .map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        Ok("inserted".to_string())
    }
    
    async fn query(&self, collection: &str, query: &Query) -> Result<Vec<QueryResult>, StorageError> {
        let table = self.tables.get(collection)
            .ok_or_else(|| StorageError::CollectionNotFound(collection.to_string()))?;
        
        let mut query_builder = table.query();
        
        if let Some(limit) = query.limit {
            query_builder = query_builder.limit(limit);
        }
        
        let results = query_builder.execute()
            .await
            .map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        let mut output = Vec::new();
        for result in results {
            output.push(QueryResult {
                id: result.get("_row_id").unwrap_or_default(),
                data: Vec::new(),
                score: None,
            });
        }
        
        Ok(output)
    }
    
    async fn update(&self, collection: &str, id: &str, data: &[u8]) -> Result<(), StorageError> {
        Err(StorageError::QueryError(
            "Update not supported in LanceDB".to_string(),
        ))
    }
    
    async fn delete(&self, collection: &str, id: &str) -> Result<(), StorageError> {
        Err(StorageError::QueryError(
            "Delete not supported in LanceDB".to_string(),
        ))
    }
    
    async fn create_collection(&self, name: &str, _schema: Option<&str>) -> Result<(), StorageError> {
        let connection = self.connection.as_ref()
            .ok_or_else(|| StorageError::ConnectionError("Not connected".to_string()))?;
        
        let schema = lancedb::Schema::new()
            .with_column("vector", lancedb::Type::FixedSizeList(1536))
            .with_column("id", lancedb::Type::Utf8);
        
        let table = connection.create_table(name, schema)
            .await
            .map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        let self_mut = unsafe {
            let ptr = self as *const Self as *mut Self;
            &mut *ptr
        };
        self_mut.tables.insert(name.to_string(), table);
        
        Ok(())
    }
    
    async fn drop_collection(&self, name: &str) -> Result<(), StorageError> {
        let connection = self.connection.as_ref()
            .ok_or_else(|| StorageError::ConnectionError("Not connected".to_string()))?;
        
        connection.drop_table(name)
            .await
            .map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        let self_mut = unsafe {
            let ptr = self as *const Self as *mut Self;
            &mut *ptr
        };
        self_mut.tables.remove(name);
        
        Ok(())
    }
}