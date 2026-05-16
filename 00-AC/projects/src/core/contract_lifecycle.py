"""契约生命周期管理系统 - 状态流转与归档策略"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, field_validator
from enum import Enum
import json
from pathlib import Path
import zipfile
import shutil


class ContractStatus(str, Enum):
    """契约状态枚举"""
    DRAFT = "draft"  # 草稿 - 正在编辑
    PENDING = "pending"  # 待审核 - 等待Trae分析
    APPROVED = "approved"  # 已批准 - 可以执行
    EXECUTING = "executing"  # 执行中
    EXECUTED = "executed"  # 已执行 - 完成
    DEPRECATED = "deprecated"  # 已废弃 - 过时或取消
    ARCHIVED = "archived"  # 已归档 - 压缩存储


class ContractStatusTransition(BaseModel):
    """状态转换规则"""
    from_status: ContractStatus
    to_status: ContractStatus
    allowed: bool = True
    required_permission: Optional[str] = None
    description: str = ""


class ArchiveMetadata(BaseModel):
    """归档元数据"""
    archive_id: str
    original_task_id: str
    archive_date: datetime
    expiration_date: Optional[datetime] = None
    compressed_size: int = 0
    original_size: int = 0
    storage_path: str = ""
    tags: List[str] = []


class ContractLifecycleConfig(BaseModel):
    """生命周期配置"""
    # 状态转换规则
    transitions: List[ContractStatusTransition] = []
    
    # 归档策略
    auto_archive_after_days: int = 90  # 执行完成后自动归档天数
    auto_deprecate_after_days: int = 30  # 待审核超时自动废弃天数
    archive_retention_days: int = 365  # 归档保留天数
    
    # 压缩配置
    enable_compression: bool = True
    compression_format: str = "zip"  # zip, tar
    
    # 向量库归档配置
    archive_to_vector_db: bool = True
    vector_db_path: str = "data/vector_archive"


class ContractLifecycleManager:
    """契约生命周期管理器"""
    
    def __init__(self, config_path: str = "config/lifecycle.json"):
        self.config_path = Path(config_path)
        self.config = ContractLifecycleConfig()
        self._load_config()
        self._init_default_transitions()
    
    def _load_config(self):
        """加载配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.config = ContractLifecycleConfig(**data)
    
    def save_config(self):
        """保存配置"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config.dict(), f, ensure_ascii=False, indent=2, default=str)
    
    def _init_default_transitions(self):
        """初始化默认状态转换规则"""
        if not self.config.transitions:
            transitions = [
                # Draft
                ContractStatusTransition(
                    from_status=ContractStatus.DRAFT,
                    to_status=ContractStatus.PENDING,
                    description="提交审核"
                ),
                ContractStatusTransition(
                    from_status=ContractStatus.DRAFT,
                    to_status=ContractStatus.DEPRECATED,
                    description="放弃草稿"
                ),
                
                # Pending
                ContractStatusTransition(
                    from_status=ContractStatus.PENDING,
                    to_status=ContractStatus.APPROVED,
                    description="Trae审核通过",
                    required_permission="review"
                ),
                ContractStatusTransition(
                    from_status=ContractStatus.PENDING,
                    to_status=ContractStatus.DRAFT,
                    description="需要修改",
                    required_permission="review"
                ),
                ContractStatusTransition(
                    from_status=ContractStatus.PENDING,
                    to_status=ContractStatus.DEPRECATED,
                    description="拒绝",
                    required_permission="review"
                ),
                
                # Approved
                ContractStatusTransition(
                    from_status=ContractStatus.APPROVED,
                    to_status=ContractStatus.EXECUTING,
                    description="开始执行"
                ),
                ContractStatusTransition(
                    from_status=ContractStatus.APPROVED,
                    to_status=ContractStatus.DEPRECATED,
                    description="取消"
                ),
                
                # Executing
                ContractStatusTransition(
                    from_status=ContractStatus.EXECUTING,
                    to_status=ContractStatus.EXECUTED,
                    description="执行完成"
                ),
                ContractStatusTransition(
                    from_status=ContractStatus.EXECUTING,
                    to_status=ContractStatus.APPROVED,
                    description="暂停执行"
                ),
                ContractStatusTransition(
                    from_status=ContractStatus.EXECUTING,
                    to_status=ContractStatus.DEPRECATED,
                    description="终止执行"
                ),
                
                # Executed
                ContractStatusTransition(
                    from_status=ContractStatus.EXECUTED,
                    to_status=ContractStatus.ARCHIVED,
                    description="归档"
                ),
                
                # Deprecated
                ContractStatusTransition(
                    from_status=ContractStatus.DEPRECATED,
                    to_status=ContractStatus.ARCHIVED,
                    description="归档废弃契约"
                ),
                
                # Archived
                ContractStatusTransition(
                    from_status=ContractStatus.ARCHIVED,
                    to_status=ContractStatus.DRAFT,
                    description="从归档恢复",
                    required_permission="admin"
                )
            ]
            self.config.transitions = transitions
            self.save_config()
    
    def is_transition_allowed(self, from_status: ContractStatus, to_status: ContractStatus) -> bool:
        """检查状态转换是否允许"""
        transition = next(
            (t for t in self.config.transitions 
             if t.from_status == from_status and t.to_status == to_status),
            None
        )
        return transition is not None and transition.allowed
    
    def get_transition_description(self, from_status: ContractStatus, to_status: ContractStatus) -> str:
        """获取状态转换描述"""
        transition = next(
            (t for t in self.config.transitions 
             if t.from_status == from_status and t.to_status == to_status),
            None
        )
        return transition.description if transition else ""
    
    def get_allowed_transitions(self, current_status: ContractStatus) -> List[ContractStatus]:
        """获取当前状态允许转换到的状态列表"""
        return [
            t.to_status for t in self.config.transitions
            if t.from_status == current_status and t.allowed
        ]
    
    def should_auto_deprecate(self, contract_created_at: datetime) -> bool:
        """检查是否应该自动废弃"""
        age = (datetime.now() - contract_created_at).days
        return age >= self.config.auto_deprecate_after_days
    
    def should_auto_archive(self, contract_executed_at: Optional[datetime]) -> bool:
        """检查是否应该自动归档"""
        if not contract_executed_at:
            return False
        age = (datetime.now() - contract_executed_at).days
        return age >= self.config.auto_archive_after_days
    
    def should_delete_archive(self, archive_date: datetime) -> bool:
        """检查归档是否应该删除"""
        age = (datetime.now() - archive_date).days
        return age >= self.config.archive_retention_days
    
    def create_archive(self, contract_data: dict, task_id: str) -> ArchiveMetadata:
        """创建归档"""
        archive_id = f"ARC-{datetime.now().strftime('%Y%m%d')}-{task_id.split('-')[-1]}"
        archive_dir = Path("data/contract_archives")
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建归档文件
        archive_path = archive_dir / f"{archive_id}.zip"
        
        # 写入契约数据
        with zipfile.ZipFile(archive_path, 'w') as zf:
            # 添加契约JSON
            contract_json = json.dumps(contract_data, ensure_ascii=False, indent=2)
            zf.writestr(f"contract.json", contract_json)
            
            # 添加元数据
            metadata = {
                "archive_id": archive_id,
                "original_task_id": task_id,
                "archive_date": datetime.now().isoformat(),
                "contract_hash": hash(json.dumps(contract_data, sort_keys=True))
            }
            zf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False))
        
        # 生成归档元数据
        metadata = ArchiveMetadata(
            archive_id=archive_id,
            original_task_id=task_id,
            archive_date=datetime.now(),
            compressed_size=archive_path.stat().st_size,
            original_size=len(json.dumps(contract_data).encode('utf-8')),
            storage_path=str(archive_path),
            tags=["contract", "archive"]
        )
        
        # 如果配置了，也存入向量库
        if self.config.archive_to_vector_db:
            self._archive_to_vector_db(contract_data, metadata)
        
        return metadata
    
    def _archive_to_vector_db(self, contract_data: dict, metadata: ArchiveMetadata):
        """将契约归档到向量库"""
        # 提取契约关键信息作为向量内容
        content = f"""
        Task ID: {contract_data.get('task_id', '')}
        Title: {contract_data.get('title', '')}
        Description: {contract_data.get('description', '')}
        Requirements: {', '.join(contract_data.get('requirements', []))}
        Status: {contract_data.get('status', '')}
        Created At: {contract_data.get('created_at', '')}
        """
        
        # 这里应该调用向量存储的添加方法
        # vector_store.add_documents([{
        #     "id": metadata.archive_id,
        #     "content": content,
        #     "metadata": metadata.dict()
        # }])
        pass
    
    def restore_from_archive(self, archive_id: str) -> Optional[dict]:
        """从归档恢复契约"""
        archive_dir = Path("data/contract_archives")
        archive_path = archive_dir / f"{archive_id}.zip"
        
        if not archive_path.exists():
            return None
        
        with zipfile.ZipFile(archive_path, 'r') as zf:
            with zf.open("contract.json") as f:
                return json.load(f)
    
    def cleanup_old_archives(self) -> int:
        """清理过期归档"""
        archive_dir = Path("data/contract_archives")
        if not archive_dir.exists():
            return 0
        
        deleted_count = 0
        
        for archive_file in archive_dir.glob("*.zip"):
            # 从文件名提取归档ID和日期
            archive_id = archive_file.stem
            try:
                # 解析归档日期 ARC-YYYYMMDD-XXX
                date_str = archive_id.split('-')[1]
                archive_date = datetime.strptime(date_str, "%Y%m%d")
                
                if self.should_delete_archive(archive_date):
                    archive_file.unlink()
                    deleted_count += 1
            except Exception:
                continue
        
        return deleted_count
    
    def get_lifecycle_report(self, contracts: List[dict]) -> Dict[str, Any]:
        """生成生命周期报告"""
        status_counts = {}
        for status in ContractStatus:
            status_counts[status.value] = 0
        
        for contract in contracts:
            status = contract.get('status', 'draft')
            if status in status_counts:
                status_counts[status] += 1
        
        # 计算需要自动处理的契约
        pending_count = 0
        executed_count = 0
        
        for contract in contracts:
            created_at = contract.get('created_at')
            executed_at = contract.get('executed_at')
            
            if created_at and contract.get('status') == 'pending':
                try:
                    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if self.should_auto_deprecate(created_date):
                        pending_count += 1
                except Exception:
                    pass
            
            if executed_at and contract.get('status') == 'executed':
                try:
                    executed_date = datetime.fromisoformat(executed_at.replace('Z', '+00:00'))
                    if self.should_auto_archive(executed_date):
                        executed_count += 1
                except Exception:
                    pass
        
        return {
            "total_contracts": len(contracts),
            "status_distribution": status_counts,
            "pending_for_deprecation": pending_count,
            "executed_for_archiving": executed_count
        }


# 状态流转图数据（用于Mermaid渲染）
def get_status_flowchart() -> str:
    """生成状态流转图的Mermaid代码"""
    return """
```mermaid
flowchart TD
    subgraph Draft状态
        A[Draft] -->|提交审核| B[Pending]
        A -->|放弃| I[Deprecated]
    end
    
    subgraph Pending状态
        B -->|审核通过| C[Approved]
        B -->|需要修改| A
        B -->|拒绝| I
        B -->|超时| I
    end
    
    subgraph Approved状态
        C -->|开始执行| D[Executing]
        C -->|取消| I
    end
    
    subgraph Executing状态
        D -->|完成| E[Executed]
        D -->|暂停| C
        D -->|终止| I
    end
    
    subgraph Executed状态
        E -->|自动归档| F[Archived]
        E -->|手动归档| F
    end
    
    subgraph Deprecated状态
        I -->|归档| F
    end
    
    subgraph Archived状态
        F -->|恢复| A
    end
    
    style A fill:#fef3c7,stroke:#f59e0b
    style B fill:#dbeafe,stroke:#3b82f6
    style C fill:#dcfce7,stroke:#22c55e
    style D fill:#fce7f3,stroke:#ec4899
    style E fill:#e0e7ff,stroke:#6366f1
    style I fill:#f3f4f6,stroke:#6b7280
    style F fill:#e0e7ff,stroke:#8b5cf6
```
"""


# 示例使用
if __name__ == "__main__":
    manager = ContractLifecycleManager()
    
    # 获取允许的状态转换
    print("Draft状态允许转换到:", manager.get_allowed_transitions(ContractStatus.DRAFT))
    
    # 检查特定转换
    print("Draft -> Pending 是否允许:", manager.is_transition_allowed(
        ContractStatus.DRAFT, ContractStatus.PENDING))
    
    # 生成状态流转图
    print("\n状态流转图:")
    print(get_status_flowchart())
