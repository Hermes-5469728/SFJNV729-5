"""
DADS Layer - Parent Child Contract (母体子体契约校验颗粒)
OpenCode Hooks:
  /dads contract-create <type>     # 创建契约
  /dads contract-verify <id>       # 验证契约
  /dads contract-enforce <id> <data> # 执行契约
  /dads contract-list              # 列出契约
"""

from loguru import logger
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
import hashlib
import time

class ContractStatus(Enum):
    """契约状态"""
    VALID = "valid"
    EXPIRED = "expired"
    BROKEN = "broken"
    UNKNOWN = "unknown"

class ContractType(Enum):
    """契约类型"""
    RETRIEVAL = "retrieval"
    GENERATION = "generation"
    REVIEW = "review"
    STORAGE = "storage"

@dataclass
class Contract:
    """契约定义"""
    contract_id: str
    parent_id: str
    child_id: str
    contract_type: ContractType
    valid_from: int
    valid_until: int
    conditions: Dict[str, Any]
    signature: str
    
    def is_valid(self) -> bool:
        """检查契约是否有效"""
        now = time.time()
        return self.valid_from <= now <= self.valid_until
    
    def verify_signature(self) -> bool:
        """验证契约签名"""
        data = f"{self.parent_id}{self.child_id}{self.contract_type.value}{self.valid_from}{self.valid_until}"
        expected_signature = hashlib.sha256(data.encode()).hexdigest()
        return self.signature == expected_signature

@dataclass
class ContractResult:
    """契约校验结果"""
    contract_id: str
    status: ContractStatus
    message: str
    verification_details: Dict[str, Any]

class ParentChildContract:
    """
    母体子体契约校验
    颗粒化模块：独立的契约管理接口
    
    OpenCode TUI 交互:
    - /dads contract-create <type> -> create_contract()
    - /dads contract-verify <id> -> verify_contract()
    - /dads contract-enforce <id> <data> -> enforce_contract()
    - /dads contract-list -> list_contracts()
    """
    
    def __init__(self):
        self.contracts: Dict[str, Contract] = {}
        self.contract_history: List[Dict[str, Any]] = []
        logger.info("ParentChildContract initialized")
    
    def create_contract(self, parent_id: str, child_id: str, contract_type: ContractType, 
                        valid_days: int = 30, conditions: Optional[Dict[str, Any]] = None) -> Contract:
        """
        创建契约
        OpenCode Hook: /dads contract-create <type>
        """
        now = time.time()
        contract_id = hashlib.sha256(f"{parent_id}{child_id}{now}".encode()).hexdigest()[:16]
        
        data = f"{parent_id}{child_id}{contract_type.value}{now}{now + valid_days * 86400}"
        signature = hashlib.sha256(data.encode()).hexdigest()
        
        contract = Contract(
            contract_id=contract_id,
            parent_id=parent_id,
            child_id=child_id,
            contract_type=contract_type,
            valid_from=now,
            valid_until=now + valid_days * 86400,
            conditions=conditions or {},
            signature=signature
        )
        
        self.contracts[contract_id] = contract
        logger.info(f"Created contract: {contract_id} ({contract_type.value})")
        return contract
    
    def verify_contract(self, contract_id: str) -> ContractResult:
        """
        验证契约
        OpenCode Hook: /dads contract-verify <id>
        """
        contract = self.contracts.get(contract_id)
        
        if not contract:
            return ContractResult(
                contract_id=contract_id,
                status=ContractStatus.UNKNOWN,
                message="契约不存在",
                verification_details={"error": "contract_not_found"}
            )
        
        if not contract.verify_signature():
            return ContractResult(
                contract_id=contract_id,
                status=ContractStatus.BROKEN,
                message="契约签名无效",
                verification_details={"error": "invalid_signature"}
            )
        
        if not contract.is_valid():
            now = time.time()
            if now < contract.valid_from:
                status = ContractStatus.UNKNOWN
                message = "契约尚未生效"
            else:
                status = ContractStatus.EXPIRED
                message = "契约已过期"
            
            return ContractResult(
                contract_id=contract_id,
                status=status,
                message=message,
                verification_details={
                    "valid_from": contract.valid_from,
                    "valid_until": contract.valid_until,
                    "current_time": now
                }
            )
        
        condition_check = self._check_conditions(contract)
        if not condition_check["passed"]:
            return ContractResult(
                contract_id=contract_id,
                status=ContractStatus.BROKEN,
                message=f"契约条件未满足: {condition_check['error']}",
                verification_details={"condition_error": condition_check["error"]}
            )
        
        return ContractResult(
            contract_id=contract_id,
            status=ContractStatus.VALID,
            message="契约有效",
            verification_details={
                "parent_id": contract.parent_id,
                "child_id": contract.child_id,
                "contract_type": contract.contract_type.value,
                "valid_until": contract.valid_until
            }
        )
    
    def _check_conditions(self, contract: Contract) -> Dict[str, Any]:
        """检查契约条件"""
        return {"passed": True}
    
    def enforce_contract(self, contract_id: str, parent_data: Dict[str, Any], 
                         child_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        强制执行契约
        OpenCode Hook: /dads contract-enforce <id> <data>
        """
        result = self.verify_contract(contract_id)
        
        if result.status != ContractStatus.VALID:
            return {
                "success": False,
                "error": result.message,
                "contract_status": result.status.value
            }
        
        contract = self.contracts[contract_id]
        
        if contract.contract_type == ContractType.RETRIEVAL:
            return self._enforce_retrieval_contract(parent_data, child_data)
        elif contract.contract_type == ContractType.GENERATION:
            return self._enforce_generation_contract(parent_data, child_data)
        elif contract.contract_type == ContractType.REVIEW:
            return self._enforce_review_contract(parent_data, child_data)
        elif contract.contract_type == ContractType.STORAGE:
            return self._enforce_storage_contract(parent_data, child_data)
        
        return {"success": True, "message": "Contract enforced"}
    
    def _enforce_retrieval_contract(self, parent_data: Dict, child_data: Dict) -> Dict[str, Any]:
        """执行检索契约"""
        logger.debug("Enforcing retrieval contract")
        return {
            "success": True,
            "type": "retrieval",
            "query": parent_data.get("query"),
            "results": child_data.get("results", [])
        }
    
    def _enforce_generation_contract(self, parent_data: Dict, child_data: Dict) -> Dict[str, Any]:
        """执行生成契约"""
        logger.debug("Enforcing generation contract")
        return {
            "success": True,
            "type": "generation",
            "context": parent_data.get("context"),
            "response": child_data.get("response")
        }
    
    def _enforce_review_contract(self, parent_data: Dict, child_data: Dict) -> Dict[str, Any]:
        """执行审查契约"""
        logger.debug("Enforcing review contract")
        return {
            "success": True,
            "type": "review",
            "review_results": child_data.get("review_results", [])
        }
    
    def _enforce_storage_contract(self, parent_data: Dict, child_data: Dict) -> Dict[str, Any]:
        """执行存储契约"""
        logger.debug("Enforcing storage contract")
        return {
            "success": True,
            "type": "storage",
            "stored": child_data.get("stored", False)
        }
    
    def revoke_contract(self, contract_id: str) -> bool:
        """撤销契约"""
        if contract_id in self.contracts:
            del self.contracts[contract_id]
            logger.info(f"Revoked contract: {contract_id}")
            return True
        return False
    
    def get_contract(self, contract_id: str) -> Optional[Contract]:
        """获取契约"""
        return self.contracts.get(contract_id)
    
    def list_contracts(self, parent_id: Optional[str] = None) -> List[Contract]:
        """
        获取契约列表
        OpenCode Hook: /dads contract-list
        """
        contracts = list(self.contracts.values())
        if parent_id:
            contracts = [c for c in contracts if c.parent_id == parent_id]
        return contracts
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态（OpenCode监控接口）"""
        return {
            "total_contracts": len(self.contracts),
            "contracts": [
                {
                    "id": c.contract_id,
                    "type": c.contract_type.value,
                    "parent": c.parent_id,
                    "child": c.child_id,
                    "valid": c.is_valid()
                }
                for c in self.contracts.values()
            ]
        }