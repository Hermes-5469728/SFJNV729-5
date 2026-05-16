
#!/usr/bin/env python3
"""
隐蔽数据中心 - 原始数据恢复工具
Recovery Center - Raw Data Recovery Tool

使用方法:
    python restore.py --backup <备份文件> --target <目标目录>
    python restore.py --list  # 列出所有备份
    python restore.py --verify  # 验证备份完整性
"""

import os
import sys
import json
import shutil
import hashlib
import argparse
from datetime import datetime
from pathlib import Path

# 配置
BACKUP_DIR = Path(__file__).parent.parent / "backups"
METADATA_DIR = Path(__file__).parent.parent / "metadata"
LOG_DIR = Path(__file__).parent.parent / "logs"

def generate_hash(file_path):
    """生成文件SHA256哈希值"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def create_backup(source_path, backup_name=None):
    """创建备份"""
    source_path = Path(source_path)
    if not source_path.exists():
        print(f"错误: 源路径不存在 - {source_path}")
        return False
    
    if backup_name is None:
        backup_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    backup_dir = BACKUP_DIR / backup_name
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        if source_path.is_dir():
            shutil.copytree(source_path, backup_dir / source_path.name)
        else:
            shutil.copy2(source_path, backup_dir)
        
        # 创建元数据
        metadata = {
            "backup_name": backup_name,
            "source_path": str(source_path),
            "backup_time": datetime.now().isoformat(),
            "files": [],
            "hash": ""
        }
        
        # 计算所有文件哈希
        all_hashes = []
        for file_path in backup_dir.rglob("*"):
            if file_path.is_file():
                file_hash = generate_hash(file_path)
                metadata["files"].append({
                    "path": str(file_path.relative_to(backup_dir)),
                    "hash": file_hash
                })
                all_hashes.append(file_hash)
        
        metadata["hash"] = hashlib.sha256("|".join(sorted(all_hashes)).encode()).hexdigest()
        
        # 保存元数据
        with open(METADATA_DIR / f"{backup_name}.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # 记录日志
        with open(LOG_DIR / "backup.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] 创建备份: {backup_name} -> {source_path}\n")
        
        print(f"✅ 备份成功: {backup_dir}")
        return True
        
    except Exception as e:
        print(f"❌ 备份失败: {str(e)}")
        return False

def restore_backup(backup_name, target_path):
    """恢复备份"""
    backup_dir = BACKUP_DIR / backup_name
    target_path = Path(target_path)
    
    if not backup_dir.exists():
        print(f"错误: 备份不存在 - {backup_dir}")
        return False
    
    try:
        # 验证完整性
        if not verify_backup(backup_name):
            print("警告: 备份完整性校验失败，继续恢复可能导致数据损坏")
        
        # 创建目标目录
        target_path.mkdir(parents=True, exist_ok=True)
        
        # 恢复文件
        for item in backup_dir.iterdir():
            dest = target_path / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        
        # 记录日志
        with open(LOG_DIR / "restore.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] 恢复备份: {backup_name} -> {target_path}\n")
        
        print(f"✅ 恢复成功: {target_path}")
        return True
        
    except Exception as e:
        print(f"❌ 恢复失败: {str(e)}")
        return False

def verify_backup(backup_name):
    """验证备份完整性"""
    backup_dir = BACKUP_DIR / backup_name
    metadata_file = METADATA_DIR / f"{backup_name}.json"
    
    if not backup_dir.exists():
        print(f"错误: 备份不存在 - {backup_dir}")
        return False
    
    if not metadata_file.exists():
        print(f"警告: 元数据文件不存在 - {metadata_file}")
        return False
    
    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        # 验证每个文件
        all_hashes = []
        for file_info in metadata["files"]:
            file_path = backup_dir / file_info["path"]
            if file_path.exists():
                actual_hash = generate_hash(file_path)
                all_hashes.append(actual_hash)
                if actual_hash != file_info["hash"]:
                    print(f"❌ 文件损坏: {file_path}")
                    return False
            else:
                print(f"❌ 文件缺失: {file_path}")
                return False
        
        # 验证整体哈希
        expected_hash = metadata["hash"]
        actual_hash = hashlib.sha256("|".join(sorted(all_hashes)).encode()).hexdigest()
        
        if actual_hash != expected_hash:
            print("❌ 整体完整性校验失败")
            return False
        
        print(f"✅ 备份完整性验证通过: {backup_name}")
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")
        return False

def list_backups():
    """列出所有备份"""
    if not BACKUP_DIR.exists():
        print("没有找到备份目录")
        return
    
    backups = sorted(BACKUP_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not backups:
        print("没有找到任何备份")
        return
    
    print("=" * 80)
    print(f"{'备份名称':<20} {'大小':<15} {'修改时间':<25} {'完整性'}")
    print("=" * 80)
    
    for backup in backups:
        if backup.is_dir():
            size = sum(f.stat().st_size for f in backup.rglob("*") if f.is_file())
            size_str = f"{size / 1024 / 1024:.2f} MB"
            mtime = datetime.fromtimestamp(backup.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            is_valid = "✅" if verify_backup(backup.name) else "❌"
            print(f"{backup.name:<20} {size_str:<15} {mtime:<25} {is_valid}")

def main():
    parser = argparse.ArgumentParser(description="隐蔽数据中心 - 原始数据恢复工具")
    parser.add_argument("--backup", help="创建备份，指定源路径")
    parser.add_argument("--restore", help="恢复备份，指定备份名称")
    parser.add_argument("--target", help="恢复目标路径")
    parser.add_argument("--list", action="store_true", help="列出所有备份")
    parser.add_argument("--verify", nargs="?", const=True, help="验证备份完整性")
    
    args = parser.parse_args()
    
    if args.backup:
        create_backup(args.backup)
    
    elif args.restore:
        if not args.target:
            print("错误: 恢复需要指定 --target 参数")
            sys.exit(1)
        restore_backup(args.restore, args.target)
    
    elif args.list:
        list_backups()
    
    elif args.verify is not None:
        if args.verify is True:
            # 验证所有备份
            for backup in BACKUP_DIR.iterdir():
                if backup.is_dir():
                    verify_backup(backup.name)
        else:
            verify_backup(args.verify)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    # 确保目录存在
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    main()
