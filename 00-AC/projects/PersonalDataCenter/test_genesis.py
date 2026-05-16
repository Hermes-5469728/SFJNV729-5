"""
测试创世特权管理器
验证初始化引导、权限控制和备份机制
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdk.genesis_manager import get_genesis_manager, GenesisManager
from sdk.auth_manager import AuthManager

def test_genesis_workflow():
    """测试创世特权完整流程"""
    print("=" * 60)
    print("创世特权管理器测试")
    print("=" * 60)
    
    # 获取创世管理器实例
    gm = get_genesis_manager()
    am = AuthManager()
    
    # 1. 检查初始状态
    print("\n1. 检查初始状态")
    status = gm.get_status()
    print(f"   真空期: {status['is_vacuum_period']}")
    print(f"   是否已锁定: {status['is_locked']}")
    print(f"   创世管理员存在: {status['genesis_admin_exists']}")
    print(f"   核心数据数量: {status['core_data_count']}")
    print(f"   镜像数据数量: {status['mirror_data_count']}")
    
    # 2. 测试创世管理员申请
    print("\n2. 测试创世管理员申请")
    if status['is_vacuum_period']:
        success, credential = gm.claim_genesis_admin()
        if success:
            print(f"   ✓ 成功申请创世管理员")
            print(f"   凭证: {credential[:8]}...")
        else:
            print(f"   ✗ 申请失败: {credential}")
    else:
        print(f"   - 非真空期，跳过申请")
    
    # 更新状态
    status = gm.get_status()
    
    # 3. 测试权限检查
    print("\n3. 测试权限检查")
    
    # 测试SDK核心层读取权限
    allowed, reason = am.check_full_permission('user1', 'sdk:core_data', 'read')
    print(f"   SDK读取权限: {'允许' if allowed else '拒绝'} ({reason})")
    
    # 测试SDK核心层写入权限（无凭证）
    allowed, reason = am.check_full_permission('user1', 'sdk:core_data', 'write')
    print(f"   SDK写入权限(无凭证): {'允许' if allowed else '拒绝'} ({reason})")
    
    # 测试SDK核心层写入权限（有凭证）
    if gm.genesis_admin:
        allowed, reason = am.check_full_permission('user1', 'sdk:core_data', 'write', gm.genesis_admin)
        print(f"   SDK写入权限(有凭证): {'允许' if allowed else '拒绝'} ({reason})")
    
    # 测试镜像层读取权限
    allowed, reason = am.check_full_permission('user1', 'mirror:docs', 'read')
    print(f"   镜像读取权限: {'允许' if allowed else '拒绝'} ({reason})")
    
    # 测试镜像层写入权限
    allowed, reason = am.check_full_permission('user1', 'mirror:docs', 'write')
    print(f"   镜像写入权限: {'允许' if allowed else '拒绝'} ({reason})")
    
    # 4. 测试备份功能
    print("\n4. 测试备份功能")
    if gm.genesis_admin:
        success, msg = gm.backup_sdk_data(gm.genesis_admin)
        print(f"   备份结果: {'成功' if success else '失败'} - {msg}")
    else:
        print("   - 无创世管理员，跳过备份测试")
    
    # 5. 测试落锁机制
    print("\n5. 测试落锁机制")
    if not gm.is_locked:
        success = gm.lock_system()
        print(f"   落锁结果: {'成功' if success else '失败'}")
        
        # 更新状态
        status = gm.get_status()
        print(f"   落锁后状态 - 已锁定: {status['is_locked']}, 备份时间: {status['backup_timestamp']}")
    else:
        print("   - 系统已锁定，跳过落锁测试")
    
    # 6. 测试落锁后的权限
    print("\n6. 测试落锁后的权限")
    if gm.is_locked:
        # 无凭证写入SDK
        allowed, reason = am.check_full_permission('user1', 'sdk:core_data', 'write')
        print(f"   无凭证写入SDK: {'允许' if allowed else '拒绝'} ({reason})")
        
        # 有凭证写入SDK
        if gm.genesis_admin:
            allowed, reason = am.check_full_permission('user1', 'sdk:core_data', 'write', gm.genesis_admin)
            print(f"   有凭证写入SDK: {'允许' if allowed else '拒绝'} ({reason})")
    
    # 7. 测试镜像复原
    print("\n7. 测试镜像复原")
    if gm.genesis_admin:
        success, msg = gm.regenerate_mirror(gm.genesis_admin)
        print(f"   镜像复原: {'成功' if success else '失败'} - {msg}")
    else:
        print("   - 无创世管理员，跳过镜像复原测试")
    
    # 8. 最终状态
    print("\n8. 最终状态")
    status = gm.get_status()
    print(f"   真空期: {status['is_vacuum_period']}")
    print(f"   是否已锁定: {status['is_locked']}")
    print(f"   创世管理员存在: {status['genesis_admin_exists']}")
    print(f"   备份时间戳: {status['backup_timestamp']}")
    print(f"   核心数据数量: {status['core_data_count']}")
    print(f"   镜像数据数量: {status['mirror_data_count']}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_genesis_workflow()