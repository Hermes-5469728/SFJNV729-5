"""备份与冗余管理工具"""

import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional


def backup_database(db_path: str, backup_dir: str = "backups") -> str:
    """备份数据库文件"""
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_path / f"db_backup_{timestamp}.zip"
    
    try:
        with zipfile.ZipFile(backup_file, 'w') as zf:
            zf.write(db_path, Path(db_path).name)
        
        # 保留最近7份备份
        clean_old_backups(backup_dir, keep_count=7)
        
        return str(backup_file)
    except Exception as e:
        raise RuntimeError(f"备份失败: {str(e)}")


def backup_hermes(source_dir: str = "Hermes", backup_dir: str = "backups") -> str:
    """备份Hermes知识库"""
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_path / f"hermes_backup_{timestamp}.zip"
    
    try:
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(source_dir)
                    zf.write(file_path, arcname)
        
        # 保留最近5份备份
        clean_old_backups(backup_dir, prefix="hermes", keep_count=5)
        
        return str(backup_file)
    except Exception as e:
        raise RuntimeError(f"Hermes备份失败: {str(e)}")


def clean_old_backups(backup_dir: str, prefix: str = "db", keep_count: int = 7) -> None:
    """清理旧备份文件"""
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        return
    
    backups = sorted(
        [f for f in backup_path.iterdir() if f.name.startswith(prefix) and f.suffix == '.zip'],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    for backup in backups[keep_count:]:
        backup.unlink()


def sync_to_cloud(local_path: str, cloud_path: Optional[str] = None) -> bool:
    """同步到云端存储（占位函数）"""
    # 实际实现时可以集成OneDrive、Google Drive等
    print(f"同步 {local_path} 到云端")
    return True


def auto_backup() -> dict:
    """执行自动备份流程"""
    results = {
        "database": None,
        "hermes": None,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # 备份数据库
        db_path = "src/ac_platform.db"
        if os.path.exists(db_path):
            results["database"] = backup_database(db_path)
        
        # 备份Hermes
        results["hermes"] = backup_hermes()
        
        # 同步到云端
        sync_to_cloud("backups")
        
        return results
    except Exception as e:
        results["error"] = str(e)
        return results


def main():
    """命令行入口"""
    results = auto_backup()
    
    if "error" in results:
        print(f"备份失败: {results['error']}")
        exit(1)
    
    print("备份成功:")
    print(f"  数据库: {results['database']}")
    print(f"  Hermes: {results['hermes']}")
    print(f"  时间: {results['timestamp']}")


if __name__ == '__main__':
    main()
