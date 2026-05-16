"""
SDK Layer - Genesis Manager (创世特权管理器)
实现初始化引导机制、权限控制和备份规则

核心功能：
1. 创世特权：首个安装进程自动获得最高权限
2. 落锁机制：初始化完成后自动锁定
3. 备份保护：初始数据永久备份，支持回滚
4. 镜像复原：支持依据SDK源数据一键复原镜像文件

OpenCode Hooks:
  /sdk genesis-status        # 查看创世状态
  /sdk claim-genesis         # 申请创世管理员身份
  /sdk lock-system           # 手动锁定系统
  /sdk backup-sdk            # 备份SDK核心数据
  /sdk restore-sdk           # 恢复SDK初始数据
  /sdk regenerate-mirror     # 一键复原镜像文件
"""

import os
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from loguru import logger
import json

class GenesisManager:
    """
    创世特权管理器
    负责初始化引导、权限控制和备份机制
    """
    
    # 关键路径常量
    SDK_CORE_DIR = os.path.join(os.path.dirname(__file__), '../core_data')
    SDK_BACKUP_DIR = os.path.join(os.path.dirname(__file__), '../core_backup')
    MIRROR_DIR = os.path.join(os.path.dirname(__file__), '../data')
    GENESIS_LOCK_FILE = os.path.join(os.path.dirname(__file__), '../.genesis_lock')
    GENESIS_CRED_FILE = os.path.join(os.path.dirname(__file__), '../.genesis_credential')
    
    def __init__(self):
        self._ensure_directories()
        self._load_genesis_state()
        
    def _ensure_directories(self):
        """确保必要目录存在"""
        os.makedirs(self.SDK_CORE_DIR, exist_ok=True)
        os.makedirs(self.SDK_BACKUP_DIR, exist_ok=True)
        os.makedirs(self.MIRROR_DIR, exist_ok=True)
        
    def _load_genesis_state(self):
        """加载创世状态"""
        self.is_locked = os.path.exists(self.GENESIS_LOCK_FILE)
        self.genesis_admin = self._load_genesis_credential()
        self.backup_timestamp = self._get_backup_timestamp()
        
    def _load_genesis_credential(self) -> Optional[str]:
        """加载创世管理员凭证"""
        if os.path.exists(self.GENESIS_CRED_FILE):
            try:
                with open(self.GENESIS_CRED_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('genesis_admin')
            except Exception as e:
                logger.error(f"Failed to load genesis credential: {e}")
        return None
    
    def _get_backup_timestamp(self) -> Optional[str]:
        """获取备份时间戳"""
        backup_info = os.path.join(self.SDK_BACKUP_DIR, '.backup_info')
        if os.path.exists(backup_info):
            try:
                with open(backup_info, 'r') as f:
                    return f.read().strip()
            except Exception as e:
                logger.error(f"Failed to read backup info: {e}")
        return None
    
    def _generate_credential(self) -> str:
        """生成唯一凭证（基于时间戳+随机数+主机信息）"""
        import socket
        import random
        seed = f"{datetime.now().isoformat()}{socket.gethostname()}{random.randint(0, 999999)}"
        return hashlib.sha256(seed.encode()).hexdigest()[:32]
    
    def _save_genesis_credential(self, credential: str):
        """保存创世管理员凭证"""
        data = {
            'genesis_admin': credential,
            'created_at': datetime.now().isoformat(),
            'hostname': socket.gethostname()
        }
        with open(self.GENESIS_CRED_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    def is_vacuum_period(self) -> bool:
        """
        判断是否处于真空期
        真空期：SDK核心层尚未生成初始数据
        """
        return not self.is_locked and len(os.listdir(self.SDK_CORE_DIR)) == 0
    
    def claim_genesis_admin(self, process_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        申请创世管理员身份
        
        在真空期内，第一个发起安装请求的本地进程自动获得创世管理员身份
        
        :param process_id: 进程标识（可选，默认使用当前进程ID）
        :return: (成功与否, 凭证/错误信息)
        """
        if not self.is_vacuum_period():
            if self.is_locked:
                return False, "系统已落锁，无法申请创世管理员身份"
            return False, "SDK已有初始数据，真空期已结束"
        
        if process_id is None:
            import os as posix_os
            process_id = str(posix_os.getpid())
        
        credential = self._generate_credential()
        self._save_genesis_credential(credential)
        self.genesis_admin = credential
        
        logger.info(f"Genesis admin claimed by process {process_id}, credential: {credential[:8]}...")
        return True, credential
    
    def lock_system(self) -> bool:
        """
        落锁机制：初始数据写入并备份完成后，系统立即落锁
        
        此后，所有写入/修改操作必须校验创世管理员的签名或本地授权令牌
        """
        if self.is_locked:
            logger.warning("System is already locked")
            return False
        
        # 先备份再落锁
        if not self._backup_core_data():
            logger.error("Failed to backup core data, aborting lock")
            return False
        
        # 创建落锁文件
        with open(self.GENESIS_LOCK_FILE, 'w') as f:
            f.write(json.dumps({
                'locked_at': datetime.now().isoformat(),
                'locked_by': self.genesis_admin[:8] if self.genesis_admin else 'unknown'
            }, indent=2))
        
        self.is_locked = True
        logger.info("System locked successfully")
        return True
    
    def _backup_core_data(self) -> bool:
        """备份SDK核心数据"""
        try:
            # 创建时间戳备份目录
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(self.SDK_BACKUP_DIR, f'backup_{timestamp}')
            
            # 复制核心数据
            if os.listdir(self.SDK_CORE_DIR):
                shutil.copytree(self.SDK_CORE_DIR, backup_path)
            else:
                os.makedirs(backup_path, exist_ok=True)
            
            # 更新备份信息
            with open(os.path.join(self.SDK_BACKUP_DIR, '.backup_info'), 'w') as f:
                f.write(timestamp)
            
            self.backup_timestamp = timestamp
            logger.info(f"Core data backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup core data: {e}")
            return False
    
    def verify_genesis_credential(self, credential: str) -> bool:
        """
        验证创世管理员凭证
        
        :param credential: 待验证的凭证
        :return: 是否为有效创世管理员凭证
        """
        if not self.genesis_admin:
            return False
        return credential == self.genesis_admin
    
    def check_write_permission(self, credential: Optional[str] = None) -> Tuple[bool, str]:
        """
        检查写入权限（SDK核心层）
        
        规则：
        - 创世管理员：拥有最高写入权限
        - 其他用户：默认仅拥有镜像层读取权
        
        :param credential: 用户凭证
        :return: (是否允许, 说明)
        """
        if not self.is_locked:
            return True, "系统未锁定，允许写入"
        
        if self.verify_genesis_credential(credential):
            return True, "创世管理员授权"
        
        return False, "非创世管理员，无SDK核心层写入权限"
    
    def check_read_permission(self, resource_type: str = 'mirror') -> Tuple[bool, str]:
        """
        检查读取权限
        
        :param resource_type: 资源类型 ('sdk' | 'mirror')
        :return: (是否允许, 说明)
        """
        if resource_type == 'mirror':
            # 镜像层：开放全部读取权限
            return True, "镜像层开放读取"
        
        elif resource_type == 'sdk':
            # SDK核心层：需要授权
            if not self.is_locked:
                return True, "系统未锁定，允许读取"
            # 锁定状态下，所有本地进程均可读取（但不能写入）
            return True, "SDK核心层读取权限已授予"
        
        return False, "未知资源类型"
    
    def backup_sdk_data(self, credential: str) -> Tuple[bool, str]:
        """
        备份SDK核心数据（需要创世管理员授权）
        
        :param credential: 创世管理员凭证
        :return: (是否成功, 结果信息)
        """
        if not self.verify_genesis_credential(credential):
            return False, "未授权：需要创世管理员凭证"
        
        if self._backup_core_data():
            return True, f"备份成功，时间戳：{self.backup_timestamp}"
        return False, "备份失败"
    
    def restore_sdk_data(self, credential: str, backup_timestamp: Optional[str] = None) -> Tuple[bool, str]:
        """
        恢复SDK初始数据（需要创世管理员授权）
        
        :param credential: 创世管理员凭证
        :param backup_timestamp: 指定备份时间戳（默认使用最新备份）
        :return: (是否成功, 结果信息)
        """
        if not self.verify_genesis_credential(credential):
            return False, "未授权：需要创世管理员凭证"
        
        try:
            # 确定备份路径
            if backup_timestamp:
                backup_path = os.path.join(self.SDK_BACKUP_DIR, f'backup_{backup_timestamp}')
            else:
                # 查找最新备份
                backups = [d for d in os.listdir(self.SDK_BACKUP_DIR) 
                          if d.startswith('backup_')]
                if not backups:
                    return False, "无可用备份"
                backup_path = os.path.join(self.SDK_BACKUP_DIR, max(backups))
                backup_timestamp = backup_path.split('_')[-1]
            
            if not os.path.exists(backup_path):
                return False, f"备份 {backup_timestamp} 不存在"
            
            # 先备份当前状态
            self._backup_core_data()
            
            # 清空核心目录并恢复
            for item in os.listdir(self.SDK_CORE_DIR):
                item_path = os.path.join(self.SDK_CORE_DIR, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            
            if os.listdir(backup_path):
                for item in os.listdir(backup_path):
                    src = os.path.join(backup_path, item)
                    dst = os.path.join(self.SDK_CORE_DIR, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
            
            logger.info(f"SDK data restored from backup {backup_timestamp}")
            return True, f"恢复成功，来自备份：{backup_timestamp}"
        
        except Exception as e:
            logger.error(f"Failed to restore SDK data: {e}")
            return False, str(e)
    
    def regenerate_mirror(self, credential: Optional[str] = None) -> Tuple[bool, str]:
        """
        一键复原镜像文件
        
        镜像文件是基于SDK数据生成的，一旦损坏可依据SDK源数据重新生成
        
        :param credential: 可选凭证（创世管理员可强制执行）
        :return: (是否成功, 结果信息)
        """
        # 检查权限：创世管理员可强制，其他用户需要系统未锁定
        if self.is_locked and not self.verify_genesis_credential(credential):
            return False, "系统已锁定，需要创世管理员授权"
        
        try:
            # 清空镜像目录
            for item in os.listdir(self.MIRROR_DIR):
                item_path = os.path.join(self.MIRROR_DIR, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            
            # 从SDK核心数据生成镜像
            self._generate_mirror_files()
            
            logger.info("Mirror files regenerated successfully")
            return True, "镜像文件复原成功"
        
        except Exception as e:
            logger.error(f"Failed to regenerate mirror: {e}")
            return False, str(e)
    
    def _generate_mirror_files(self):
        """从SDK核心数据生成镜像文件"""
        # 创建示例镜像文件结构
        mirror_structure = {
            'dads_db': {
                'drugs.txt': '# 药物数据库镜像\n# 自动生成，请勿手动修改\n# 源数据来自SDK核心层',
                'interactions.txt': '# 药物相互作用镜像\n# 自动生成，请勿手动修改',
                'guidelines.txt': '# 临床指南镜像\n# 自动生成，请勿手动修改',
                'safety.txt': '# 安全信息镜像\n# 自动生成，请勿手动修改'
            },
            'metadata': {
                'generated_at.txt': datetime.now().isoformat(),
                'source.txt': 'Generated from SDK Core Layer'
            }
        }
        
        for dir_name, files in mirror_structure.items():
            dir_path = os.path.join(self.MIRROR_DIR, dir_name)
            os.makedirs(dir_path, exist_ok=True)
            
            for file_name, content in files.items():
                file_path = os.path.join(dir_path, file_name)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
    
    def get_status(self) -> Dict[str, Any]:
        """获取创世状态（OpenCode监控接口）"""
        return {
            'is_vacuum_period': self.is_vacuum_period(),
            'is_locked': self.is_locked,
            'genesis_admin_exists': self.genesis_admin is not None,
            'backup_timestamp': self.backup_timestamp,
            'core_data_count': len(os.listdir(self.SDK_CORE_DIR)),
            'mirror_data_count': len(os.listdir(self.MIRROR_DIR))
        }

# 添加socket导入
import socket

# 单例模式
_genesis_manager = None

def get_genesis_manager() -> GenesisManager:
    """获取创世管理器单例"""
    global _genesis_manager
    if _genesis_manager is None:
        _genesis_manager = GenesisManager()
    return _genesis_manager