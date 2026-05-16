use digital_twin_sdk::auth::CasbinAuth;
use digital_twin_sdk::core::interfaces::IAuth;
use std::sync::Arc;

#[tokio::test]
async fn test_casbin_auth() {
    let auth = CasbinAuth::new(
        "examples/rbac_model.conf",
        "examples/rbac_policy.csv",
    ).await.expect("Failed to create CasbinAuth");
    
    let result = auth.enforce("alice", "data1", "read").await.unwrap();
    assert!(result);
    
    let result = auth.enforce("alice", "data2", "write").await.unwrap();
    assert!(!result);
}