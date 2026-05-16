use async_trait::async_trait;
use rusqlite::{Connection, params};
use std::any::Any;
use std::collections::HashMap;

use crate::core::interfaces::{
    IVectorStorage, Query, QueryResult, StorageConfig, StorageError, StorageType,
    VectorSearchResult,
};

pub struct SQLiteStorage {
    connection: Option<Connection>,
}

impl SQLiteStorage {
    pub fn new() -> Self {
        Self {
            connection: None,
        }
    }
}

#[async_trait]
impl IVectorStorage for SQLiteStorage {
    async fn insert_vector(
        &self,
        collection: &str,
        vector: &[f32],
        metadata: Option<&HashMap<String, String>>,
    ) -> Result<String, StorageError> {
        let conn = self.connection.as_ref()
            .ok_or_else(|| StorageError::ConnectionError("Not connected".to_string()))?;
        
        let vector_blob = bincode::serialize(vector)
            .map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        let meta_json = if let Some(meta) = metadata {
            serde_json::to_string(meta)
                .map_err(|e| StorageError::QueryError(e.to_string()))?
        } else {
            "{}".to_string()
        };
        
        let mut stmt = conn.prepare(&format!(
            "INSERT INTO {} (vector, metadata) VALUES (?, ?)",
            collection
        )).map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        let id = stmt.insert(params![vector_blob, meta_json])
            .map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        Ok(id.to_string())
    }
    
    async fn search_vectors(
        &self,
        collection: &str,
        query_vector: &[f32],
        top_k: usize,
    ) -> Result<Vec<VectorSearchResult>, StorageError> {
        let conn = self.connection.as_ref()
            .ok_or_else(|| StorageError::ConnectionError("Not connected".to_string()))?;
        
        let results = conn.query_map(&format!(
            "SELECT id, vector, metadata FROM {} ORDER BY vector MATCH ? LIMIT {}",
            collection, top_k
        ), params![bincode::serialize(query_vector).unwrap()], |row| {
            let id: i64 = row.get(0)?;
            let vector_blob: Vec<u8> = row.get(1)?;
            let vector: Vec<f32> = bincode::deserialize(&vector_blob).unwrap();
            
            Ok((id, vector))
        }).map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        let mut output = Vec::new();
        for result in results {
            let (id, vector) = result.map_err(|e| StorageError::QueryError(e.to_string()))?;
            output.push(VectorSearchResult {
                id: id.to_string(),
                vector,
                metadata: None,
                score: 0.0,
            });
        }
        
        Ok(output)
    }
}

#[async_trait]
impl crate::core::interfaces::IStorage for SQLiteStorage {
    fn as_any(&self) -> &dyn Any {
        self
    }
    
    async fn init(&self, config: &StorageConfig) -> Result<(), StorageError> {
        if config.storage_type != StorageType::SQLite && 
           config.storage_type != StorageType::SQLiteVector {
            return Err(StorageError::InvalidInput(
                "Invalid storage type for SQLite".to_string(),
            ));
        }
        
        let connection = Connection::open(&config.connection_string)
            .map_err(|e| StorageError::ConnectionError(e.to_string()))?;
        
        if config.storage_type == StorageType::SQLiteVector {
            connection.execute("CREATE VIRTUAL TABLE IF NOT EXISTS vectors USING vec0(vector)", [])
                .map_err(|e| StorageError::ConnectionError(e.to_string()))?;
        }
        
        let self_mut = unsafe {
            let ptr = self as *const Self as *mut Self;
            &mut *ptr
        };
        self_mut.connection = Some(connection);
        
        Ok(())
    }
    
    async fn insert(&self, collection: &str, data: &[u8]) -> Result<String, StorageError> {
        let conn = self.connection.as_ref()
            .ok_or_else(|| StorageError::ConnectionError("Not connected".to_string()))?;
        
        let mut stmt = conn.prepare(&format!(
            "INSERT INTO {} (data) VALUES (?)",
            collection
        )).map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        let id = stmt.insert(params![data])
            .map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        Ok(id.to_string())
    }
    
    async fn query(&self, collection: &str, query: &Query) -> Result<Vec<QueryResult>, StorageError> {
        let conn = self.connection.as_ref()
            .ok_or_else(|| StorageError::ConnectionError("Not connected".to_string()))?;
        
        let limit = query.limit.unwrap_or(10);
        let offset = query.offset.unwrap_or(0);
        
        let results = conn.query_map(&format!(
            "SELECT id, data FROM {} LIMIT {} OFFSET {}",
            collection, limit, offset
        ), [], |row| {
            let id: i64 = row.get(0)?;
            let data: Vec<u8> = row.get(1)?;
            Ok((id, data))
        }).map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        let mut output = Vec::new();
        for result in results {
            let (id, data) = result.map_err(|e| StorageError::QueryError(e.to_string()))?;
            output.push(QueryResult {
                id: id.to_string(),
                data,
                score: None,
            });
        }
        
        Ok(output)
    }
    
    async fn update(&self, collection: &str, id: &str, data: &[u8]) -> Result<(), StorageError> {
        let conn = self.connection.as_ref()
            .ok_or_else(|| StorageError::ConnectionError("Not connected".to_string()))?;
        
        conn.execute(&format!(
            "UPDATE {} SET data = ? WHERE id = ?",
            collection
        ), params![data, id])
            .map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        Ok(())
    }
    
    async fn delete(&self, collection: &str, id: &str) -> Result<(), StorageError> {
        let conn = self.connection.as_ref()
            .ok_or_else(|| StorageError::ConnectionError("Not connected".to_string()))?;
        
        conn.execute(&format!("DELETE FROM {} WHERE id = ?", collection), params![id])
            .map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        Ok(())
    }
    
    async fn create_collection(&self, name: &str, _schema: Option<&str>) -> Result<(), StorageError> {
        let conn = self.connection.as_ref()
            .ok_or_else(|| StorageError::ConnectionError("Not connected".to_string()))?;
        
        conn.execute(&format!(
            "CREATE TABLE IF NOT EXISTS {} (id INTEGER PRIMARY KEY AUTOINCREMENT, data BLOB)",
            name
        ), [])
            .map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        Ok(())
    }
    
    async fn drop_collection(&self, name: &str) -> Result<(), StorageError> {
        let conn = self.connection.as_ref()
            .ok_or_else(|| StorageError::ConnectionError("Not connected".to_string()))?;
        
        conn.execute(&format!("DROP TABLE IF EXISTS {}", name), [])
            .map_err(|e| StorageError::QueryError(e.to_string()))?;
        
        Ok(())
    }
}