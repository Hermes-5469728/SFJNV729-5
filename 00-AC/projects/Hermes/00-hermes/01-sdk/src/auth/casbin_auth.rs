use async_trait::async_trait;
use casbin::{CoreApi, DefaultModel, FileAdapter, Result};
use std::any::Any;
use std::sync::Arc;

use crate::core::interfaces::{AuthError, IAuth};

pub struct CasbinAuth {
    enforcer: Arc<casbin::Enforcer>,
}

impl CasbinAuth {
    pub async fn new(model_path: &str, policy_path: &str) -> Result<Self, AuthError> {
        let model = DefaultModel::from_file(model_path)
            .map_err(|e| AuthError::CasbinError(e.to_string()))?;
        
        let adapter = FileAdapter::new(policy_path);
        
        let enforcer = casbin::Enforcer::new(model, adapter)
            .await
            .map_err(|e| AuthError::CasbinError(e.to_string()))?;
        
        Ok(Self {
            enforcer: Arc::new(enforcer),
        })
    }
    
    pub async fn from_enforcer(enforcer: casbin::Enforcer) -> Self {
        Self {
            enforcer: Arc::new(enforcer),
        }
    }
}

#[async_trait]
impl IAuth for CasbinAuth {
    fn as_any(&self) -> &dyn Any {
        self
    }
    
    async fn enforce(
        &self,
        subject: &str,
        object: &str,
        action: &str,
    ) -> Result<bool, AuthError> {
        self.enforcer
            .enforce((subject, object, action))
            .await
            .map_err(|e| AuthError::CasbinError(e.to_string()))
    }
    
    async fn add_policy(
        &self,
        subject: &str,
        object: &str,
        action: &str,
    ) -> Result<(), AuthError> {
        self.enforcer
            .add_policy(vec![
                subject.to_string(),
                object.to_string(),
                action.to_string(),
            ])
            .await
            .map_err(|e| AuthError::CasbinError(e.to_string()))
    }
    
    async fn remove_policy(
        &self,
        subject: &str,
        object: &str,
        action: &str,
    ) -> Result<(), AuthError> {
        self.enforcer
            .remove_policy(vec![
                subject.to_string(),
                object.to_string(),
                action.to_string(),
            ])
            .await
            .map_err(|e| AuthError::CasbinError(e.to_string()))
    }
    
    async fn load_policy(&self) -> Result<(), AuthError> {
        self.enforcer
            .load_policy()
            .await
            .map_err(|e| AuthError::CasbinError(e.to_string()))
    }
    
    async fn save_policy(&self) -> Result<(), AuthError> {
        self.enforcer
            .save_policy()
            .await
            .map_err(|e| AuthError::CasbinError(e.to_string()))
    }
}