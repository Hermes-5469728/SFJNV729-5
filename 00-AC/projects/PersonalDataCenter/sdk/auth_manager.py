"""
SDK Layer - Auth Manager (权限控制颗粒)
OpenCode Hook: /sdk auth-check <sub> <obj> <act>

权限模型：
- SDK核心层：创世管理员专属，落锁后仅创世管理员可写入
- 镜像层：开放全部读取权限，任何进程均可读取
- 默认用户：仅拥有镜像层读取权
"""

import casbin
import os
from loguru import logger
from typing import Dict, Any, Optional, Tuple

class AuthManager:
    """
    Casbin权限控制管理器 + 创世特权集成
    颗粒化模块：独立的权限控制接口
    
    权限层次：
    1. 创世管理员（Genesis Admin）：最高权限，可操作SDK核心层
    2. 授权用户：通过Casbin策略授权的用户
    3. 默认用户：仅镜像层读取权限
    """
    
    def __init__(self, model_path: str = None, policy_path: str = None):
        self.model_path = model_path or os.path.join(os.path.dirname(__file__), '../configs/rbac_model.conf')
        self.policy_path = policy_path or os.path.join(os.path.dirname(__file__), '../configs/rbac_policy.csv')
        self.enforcer = None
        self._init_enforcer()
        
        # 延迟导入以避免循环依赖
        from .genesis_manager import get_genesis_manager
        self.genesis_manager = get_genesis_manager()
    
    def _init_enforcer(self):
        """初始化Casbin enforcer"""
        try:
            self.enforcer = casbin.Enforcer(self.model_path, self.policy_path)
            self.enforcer.load_policy()
            logger.info(f"Casbin enforcer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Casbin enforcer: {e}")
            # 不抛出异常，允许降级到创世特权模式
    
    def enforce(self, subject: str, object: str, action: str, credential: Optional[str] = None) -> bool:
        """
        权限检查（集成创世特权）
        
        检查逻辑优先级：
        1. 创世管理员校验（最高优先级）
        2. Casbin策略校验
        3. 默认权限（镜像层读取）
        
        :param subject: 用户/角色
        :param object: 资源（支持前缀识别：'sdk:' 或 'mirror:'）
        :param action: 操作（read/write/execute）
        :param credential: 创世管理员凭证（可选）
        :return: True=允许访问, False=拒绝访问
        
        OpenCode Hook: /sdk auth-check <sub> <obj> <act>
        """
        # 1. 检查资源类型并应用对应策略
        if object.startswith('sdk:'):
            # SDK核心层：需要创世管理员授权
            return self._check_sdk_permission(action, credential)
        elif object.startswith('mirror:'):
            # 镜像层：开放读取权限
            return self._check_mirror_permission(action)
        else:
            # 其他资源：使用Casbin策略
            return self._check_casbin_policy(subject, object, action)
    
    def _check_sdk_permission(self, action: str, credential: Optional[str]) -> bool:
        """
        检查SDK核心层权限
        
        规则：
        - 系统未锁定：允许所有操作
        - 系统已锁定：仅创世管理员可写入
        - 读取权限：所有本地进程都有
        
        :param action: 操作类型
        :param credential: 创世管理员凭证
        :return: 是否允许
        """
        if action.lower() == 'read':
            # SDK核心层读取权限：所有本地进程均可读取
            return True
        
        # 写入/修改操作需要创世管理员授权
        allowed, reason = self.genesis_manager.check_write_permission(credential)
        logger.debug(f"SDK write permission check: {allowed} ({reason})")
        return allowed
    
    def _check_mirror_permission(self, action: str) -> bool:
        """
        检查镜像层权限
        
        规则：
        - 读取：开放全部权限
        - 写入：需要创世管理员授权（镜像文件应由系统自动生成）
        
        :param action: 操作类型
        :return: 是否允许
        """
        if action.lower() == 'read':
            # 镜像层：开放全部读取权限
            return True
        
        # 写入镜像层需要创世管理员授权
        # （镜像文件理论上应由系统自动生成，不建议手动修改）
        logger.warning(f"Attempt to write to mirror layer: {action}")
        return False
    
    def _check_casbin_policy(self, subject: str, object: str, action: str) -> bool:
        """
        使用Casbin策略检查权限
        
        :param subject: 用户/角色
        :param object: 资源
        :param action: 操作
        :return: 是否允许
        """
        if not self.enforcer:
            logger.warning("Enforcer not initialized, allowing access")
            return True
        
        try:
            result = self.enforcer.enforce(subject, object, action)
            logger.debug(f"Casbin auth check: {subject} {action} {object} -> {result}")
            return result
        except Exception as e:
            logger.error(f"Casbin auth check failed: {e}")
            return False
    
    def check_full_permission(self, subject: str, object: str, action: str, 
                             credential: Optional[str] = None) -> Tuple[bool, str]:
        """
        完整权限检查（返回详细信息）
        
        :param subject: 用户/角色
        :param object: 资源
        :param action: 操作
        :param credential: 创世管理员凭证
        :return: (是否允许, 原因)
        """
        if object.startswith('sdk:'):
            if action.lower() == 'read':
                return True, "SDK核心层读取权限已授予"
            return self.genesis_manager.check_write_permission(credential)
        
        elif object.startswith('mirror:'):
            if action.lower() == 'read':
                return True, "镜像层开放读取"
            return False, "镜像层写入需要创世管理员授权"
        
        else:
            result = self._check_casbin_policy(subject, object, action)
            if result:
                return True, "Casbin策略允许"
            return False, "Casbin策略拒绝"
    
    def add_policy(self, subject: str, object: str, action: str):
        """添加权限策略"""
        if self.enforcer:
            self.enforcer.add_policy(subject, object, action)
            self.enforcer.save_policy()
            logger.info(f"Added policy: {subject} {action} {object}")
    
    def remove_policy(self, subject: str, object: str, action: str):
        """移除权限策略"""
        if self.enforcer:
            self.enforcer.remove_policy(subject, object, action)
            self.enforcer.save_policy()
            logger.info(f"Removed policy: {subject} {action} {object}")
    
    def reload_policy(self):
        """重新加载策略"""
        if self.enforcer:
            self.enforcer.load_policy()
            logger.info("Policy reloaded")
    
    def get_all_policies(self) -> list:
        """获取所有策略"""
        if self.enforcer:
            return self.enforcer.get_policy()
        return []
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态（OpenCode监控接口）"""
        return {
            "initialized": self.enforcer is not None,
            "policy_count": len(self.get_all_policies()),
            "genesis_locked": self.genesis_manager.is_locked,
            "genesis_admin_exists": self.genesis_manager.genesis_admin is not None
        }