"""Database Migration Manager · 数据库迁移管理器

失忆预防铁律：
1. 任何操作 ac_platform.db 的代码，必须先校验 schema 版本（PRAGMA user_version）
2. schema 不匹配时不允许直接 CREATE/ALTER，必须走 migration 脚本
3. AI 必须在 migration 前输出 diff，经确认后执行
4. 涅槃快照必须包含 schema 版本号
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field

# ==================== 版本常量 ====================
CURRENT_SCHEMA_VERSION = 2
MIGRATION_DIR = Path(__file__).resolve().parent / "migrations"

# ==================== 数据结构 ====================

@dataclass
class Migration:
    """迁移脚本定义"""
    version: int
    name: str
    description: str
    operations: List[str]
    rollback_operations: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class MigrationResult:
    """迁移结果"""
    success: bool
    version_before: int
    version_after: int
    migrations_applied: List[int]
    error_message: Optional[str] = None
    diff_output: Optional[str] = None

@dataclass
class SchemaDiff:
    """Schema差异"""
    table_name: str
    action: str  # CREATE, ALTER, DROP
    before: Optional[str] = None
    after: Optional[str] = None
    columns_added: List[str] = field(default_factory=list)
    columns_removed: List[str] = field(default_factory=list)
    columns_changed: List[str] = field(default_factory=list)

# ==================== 迁移脚本库 ====================

MIGRATIONS: List[Migration] = [
    Migration(
        version=1,
        name="initial_schema",
        description="初始schema：专家表、治理日志表",
        operations=[
            """CREATE TABLE IF NOT EXISTS ac_experts (
                expert_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                trigger_words TEXT NOT NULL,
                role_definition TEXT NOT NULL,
                rules TEXT NOT NULL,
                constraints TEXT,
                is_generic INTEGER NOT NULL DEFAULT 1,
                version TEXT NOT NULL,
                priority VARCHAR(5) DEFAULT 'P5',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS ac_governance_log (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                command TEXT,
                input_preview TEXT,
                passed INTEGER,
                checks_json TEXT,
                corrected INTEGER,
                retries INTEGER,
                created_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS ac_schedule_log (
                log_id TEXT PRIMARY KEY,
                session_id TEXT,
                query_hash TEXT,
                query_preview TEXT,
                matched_expert TEXT,
                response_mode TEXT,
                scheduler_version TEXT,
                created_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS ac_truth (
                truth_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                source TEXT NOT NULL,
                content TEXT NOT NULL,
                truth_count INTEGER DEFAULT 1,
                verified INTEGER DEFAULT 0,
                tags TEXT,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS task_graphs (
                session_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                root_prompt TEXT NOT NULL,
                plan TEXT NOT NULL,
                agent_pool TEXT NOT NULL,
                shared_context TEXT,
                hitl_queue TEXT,
                metrics TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS migration_history (
                migration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                success INTEGER NOT NULL,
                error_message TEXT
            )"""
        ],
        rollback_operations=[
            "DROP TABLE IF EXISTS ac_experts",
            "DROP TABLE IF EXISTS ac_governance_log",
            "DROP TABLE IF EXISTS ac_schedule_log",
            "DROP TABLE IF EXISTS ac_truth",
            "DROP TABLE IF EXISTS task_graphs",
            "DROP TABLE IF EXISTS migration_history"
        ]
    ),
    Migration(
        version=2,
        name="encoding_columns",
        description="添加编码相关字段到治理日志表",
        operations=[
            "ALTER TABLE ac_governance_log ADD COLUMN encoding_sanitized INTEGER DEFAULT 0",
            "ALTER TABLE ac_governance_log ADD COLUMN encoding_events TEXT"
        ],
        rollback_operations=[
            "ALTER TABLE ac_governance_log DROP COLUMN encoding_sanitized",
            "ALTER TABLE ac_governance_log DROP COLUMN encoding_events"
        ]
    )
]

# ==================== 迁移管理器核心 ====================

class MigrationManager:
    """数据库迁移管理器"""
    
    def __init__(self, db_path: str = "ac_platform.db"):
        self.db_path = Path(db_path)
        self.conn = None
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self.conn is None:
            self.conn = sqlite3.connect(str(self.db_path), timeout=10)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL")
        return self.conn
    
    def get_current_version(self) -> int:
        """获取当前schema版本"""
        conn = self._get_connection()
        cur = conn.execute("PRAGMA user_version")
        return cur.fetchone()[0]
    
    def set_version(self, version: int):
        """设置schema版本"""
        conn = self._get_connection()
        conn.execute(f"PRAGMA user_version = {version}")
        conn.commit()
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """获取迁移历史"""
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM migration_history ORDER BY version DESC")
            return [dict(row) for row in cur.fetchall()]
        except sqlite3.OperationalError:
            return []
    
    def calculate_pending_migrations(self) -> List[Migration]:
        """计算待执行的迁移"""
        current_version = self.get_current_version()
        return [m for m in MIGRATIONS if m.version > current_version]
    
    def generate_diff(self, migration: Migration) -> str:
        """生成迁移diff输出"""
        conn = self._get_connection()
        diff_lines = []
        
        diff_lines.append(f"┌─────────────────────────────────────────────┐")
        diff_lines.append(f"│  Migration: v{migration.version} - {migration.name}")
        diff_lines.append(f"├─────────────────────────────────────────────┤")
        diff_lines.append(f"│ Description: {migration.description}")
        diff_lines.append(f"├─────────────────────────────────────────────┤")
        diff_lines.append(f"│ Operations ({len(migration.operations)}):")
        diff_lines.append(f"├─────────────────────────────────────────────┤")
        
        for i, op in enumerate(migration.operations, 1):
            op_type = op.split()[0].upper()
            table_name = self._extract_table_name(op)
            diff_lines.append(f"│ [{i}] {op_type} {table_name or ''}")
            diff_lines.append(f"│     {op[:80]}..." if len(op) > 80 else f"│     {op}")
        
        if migration.rollback_operations:
            diff_lines.append(f"├─────────────────────────────────────────────┤")
            diff_lines.append(f"│ Rollback ({len(migration.rollback_operations)}):")
            for i, op in enumerate(migration.rollback_operations, 1):
                op_type = op.split()[0].upper()
                diff_lines.append(f"│     [{i}] {op}")
        
        diff_lines.append(f"└─────────────────────────────────────────────┘")
        
        return "\n".join(diff_lines)
    
    def _extract_table_name(self, sql: str) -> Optional[str]:
        """从SQL语句中提取表名"""
        sql_upper = sql.upper()
        if "CREATE TABLE" in sql_upper:
            return sql_upper.split("TABLE")[1].strip().split()[0].strip()
        if "ALTER TABLE" in sql_upper:
            return sql_upper.split("TABLE")[1].strip().split()[0].strip()
        if "DROP TABLE" in sql_upper:
            return sql_upper.split("TABLE")[1].strip().split()[0].strip()
        return None
    
    def _extract_column_name(self, sql: str) -> Optional[str]:
        """从ALTER TABLE ADD COLUMN语句中提取列名"""
        sql_upper = sql.upper()
        if "ALTER TABLE" in sql_upper and "ADD COLUMN" in sql_upper:
            # ALTER TABLE xxx ADD COLUMN column_name type
            parts = sql_upper.replace("ADD COLUMN", "|").split("|")
            if len(parts) > 1:
                return parts[1].strip().split()[0].strip().lower()
        return None
    
    def _column_exists(self, conn, table_name: str, column_name: str) -> bool:
        """检查表中是否存在指定列"""
        try:
            cur = conn.execute(f"PRAGMA table_info({table_name})")
            columns = [row["name"].lower() for row in cur.fetchall()]
            return column_name.lower() in columns
        except sqlite3.OperationalError:
            return False
    
    def apply_migration(self, migration: Migration, confirm: bool = True) -> MigrationResult:
        """
        应用单个迁移
        
        Args:
            migration: 迁移脚本
            confirm: 是否需要确认
        
        Returns:
            MigrationResult: 迁移结果
        """
        conn = self._get_connection()
        version_before = self.get_current_version()
        
        # 输出diff
        diff_output = self.generate_diff(migration)
        print(f"\n📋 迁移预览 (v{version_before} → v{migration.version}):")
        print(diff_output)
        
        # 需要确认
        if confirm:
            while True:
                response = input("\n⚠️ 确认执行此迁移? [Y/N]: ").strip().upper()
                if response in ["Y", "YES"]:
                    break
                elif response in ["N", "NO"]:
                    return MigrationResult(
                        success=False,
                        version_before=version_before,
                        version_after=version_before,
                        migrations_applied=[],
                        error_message="用户取消迁移",
                        diff_output=diff_output
                    )
                else:
                    print("请输入 Y 或 N")
        
        # 执行迁移
        try:
            # 使用execute()包装事务，避免SQLite自动回滚问题
            conn.execute("BEGIN EXCLUSIVE")
            
            for op in migration.operations:
                # 在执行ALTER TABLE之前检查列是否已存在
                if op.upper().startswith("ALTER TABLE") and "ADD COLUMN" in op.upper():
                    table_name = self._extract_table_name(op)
                    column_name = self._extract_column_name(op)
                    if table_name and column_name and self._column_exists(conn, table_name, column_name):
                        print(f"   ⚠️ 列已存在，跳过: {table_name}.{column_name}")
                        continue
                conn.execute(op)
            
            # 记录迁移历史
            conn.execute(
                """INSERT INTO migration_history 
                   (version, name, applied_at, success, error_message) 
                   VALUES (?, ?, ?, ?, ?)""",
                (migration.version, migration.name, 
                 datetime.now(timezone.utc).isoformat(), 1, None)
            )
            
            # 更新版本号
            self.set_version(migration.version)
            
            conn.execute("COMMIT")
            
            return MigrationResult(
                success=True,
                version_before=version_before,
                version_after=migration.version,
                migrations_applied=[migration.version],
                diff_output=diff_output
            )
        
        except sqlite3.OperationalError as e:
            # 事务已自动回滚
            return MigrationResult(
                success=False,
                version_before=version_before,
                version_after=version_before,
                migrations_applied=[],
                error_message=str(e),
                diff_output=diff_output
            )
        except Exception as e:
            # 其他错误，尝试回滚
            try:
                conn.execute("ROLLBACK")
            except:
                pass
            return MigrationResult(
                success=False,
                version_before=version_before,
                version_after=version_before,
                migrations_applied=[],
                error_message=str(e),
                diff_output=diff_output
            )
    
    def run_migrations(self, confirm: bool = True) -> MigrationResult:
        """
        运行所有待执行的迁移
        
        Args:
            confirm: 是否需要确认每个迁移
        
        Returns:
            MigrationResult: 迁移结果
        """
        pending = self.calculate_pending_migrations()
        
        if not pending:
            current_version = self.get_current_version()
            return MigrationResult(
                success=True,
                version_before=current_version,
                version_after=current_version,
                migrations_applied=[],
                diff_output="数据库schema已是最新版本"
            )
        
        print(f"🔄 发现 {len(pending)} 个待执行迁移:")
        for m in pending:
            print(f"   • v{m.version}: {m.name}")
        
        version_before = self.get_current_version()
        applied_versions = []
        
        for migration in pending:
            result = self.apply_migration(migration, confirm)
            if result.success:
                applied_versions.append(migration.version)
            else:
                return MigrationResult(
                    success=False,
                    version_before=version_before,
                    version_after=self.get_current_version(),
                    migrations_applied=applied_versions,
                    error_message=result.error_message,
                    diff_output=result.diff_output
                )
        
        return MigrationResult(
            success=True,
            version_before=version_before,
            version_after=self.get_current_version(),
            migrations_applied=applied_versions
        )
    
    def validate_schema_version(self, required_version: Optional[int] = None) -> bool:
        """
        验证schema版本
        
        Args:
            required_version: 要求的版本号，None表示检查是否为最新
            
        Returns:
            bool: 是否通过验证
        """
        current_version = self.get_current_version()
        target_version = required_version or CURRENT_SCHEMA_VERSION
        
        if current_version == target_version:
            print(f"✅ Schema版本验证通过: v{current_version}")
            return True
        
        print(f"❌ Schema版本不匹配!")
        print(f"   当前版本: v{current_version}")
        print(f"   要求版本: v{target_version}")
        print(f"   请运行迁移脚本: python -m db_migration migrate")
        return False
    
    def get_snapshot(self) -> Dict[str, Any]:
        """获取涅槃快照（包含schema版本号）"""
        conn = self._get_connection()
        
        # 获取表结构信息
        tables_info = []
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row["name"] for row in cur.fetchall()]
        
        for table in tables:
            cur = conn.execute(f"PRAGMA table_info({table})")
            columns = [dict(row) for row in cur.fetchall()]
            cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cur.fetchone()[0]
            tables_info.append({
                "table_name": table,
                "column_count": len(columns),
                "row_count": row_count,
                "columns": columns
            })
        
        return {
            "schema_version": self.get_current_version(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_path": str(self.db_path),
            "tables": tables_info,
            "migration_history": self.get_migration_history(),
            "migration_status": {
                "current_version": self.get_current_version(),
                "latest_version": CURRENT_SCHEMA_VERSION,
                "pending_migrations": len(self.calculate_pending_migrations())
            }
        }
    
    def export_snapshot(self, output_path: Optional[str] = None) -> str:
        """导出涅槃快照到文件"""
        snapshot = self.get_snapshot()
        if output_path is None:
            output_path = f"snapshot_v{snapshot['schema_version']}_{int(datetime.now(timezone.utc).timestamp())}.json"
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        
        print(f"📸 涅槃快照已导出: {output_path}")
        return output_path

# ==================== 装饰器：强制版本校验 ====================

def require_schema_version(required_version: int = CURRENT_SCHEMA_VERSION):
    """
    装饰器：强制schema版本校验
    
    使用示例：
        @require_schema_version(2)
        def my_db_operation(conn):
            # 数据库操作
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # 查找conn参数
            conn = None
            for arg in args:
                if isinstance(arg, sqlite3.Connection):
                    conn = arg
                    break
            if "conn" in kwargs:
                conn = kwargs["conn"]
            
            if conn:
                cur = conn.execute("PRAGMA user_version")
                current_version = cur.fetchone()[0]
                if current_version != required_version:
                    raise SchemaVersionError(
                        f"Schema版本不匹配! 当前v{current_version}, 需要v{required_version}"
                    )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

class SchemaVersionError(Exception):
    """Schema版本错误"""
    pass

# ==================== CLI入口 ====================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Migration Manager · 数据库迁移管理器")
    subparsers = parser.add_subparsers(dest="command")
    
    # version命令
    version_parser = subparsers.add_parser("version", help="查看当前schema版本")
    
    # validate命令
    validate_parser = subparsers.add_parser("validate", help="验证schema版本")
    validate_parser.add_argument("--required", type=int, help="要求的版本号")
    
    # migrate命令
    migrate_parser = subparsers.add_parser("migrate", help="执行数据库迁移")
    migrate_parser.add_argument("--no-confirm", action="store_true", help="跳过确认")
    
    # diff命令
    diff_parser = subparsers.add_parser("diff", help="显示待执行迁移的diff")
    
    # snapshot命令
    snapshot_parser = subparsers.add_parser("snapshot", help="导出涅槃快照")
    snapshot_parser.add_argument("--output", "-o", help="输出文件路径")
    
    # history命令
    history_parser = subparsers.add_parser("history", help="查看迁移历史")
    
    args = parser.parse_args()
    
    manager = MigrationManager()
    
    if args.command == "version":
        version = manager.get_current_version()
        print(f"当前Schema版本: v{version}")
        print(f"最新Schema版本: v{CURRENT_SCHEMA_VERSION}")
    
    elif args.command == "validate":
        required = args.required if args.required else CURRENT_SCHEMA_VERSION
        success = manager.validate_schema_version(required)
        exit(0 if success else 1)
    
    elif args.command == "migrate":
        result = manager.run_migrations(confirm=not args.no_confirm)
        if result.success:
            print(f"\n✅ 迁移成功! v{result.version_before} → v{result.version_after}")
            print(f"   应用迁移: {result.migrations_applied}")
        else:
            print(f"\n❌ 迁移失败: {result.error_message}")
            if result.diff_output:
                print("\n迁移预览:")
                print(result.diff_output)
            exit(1)
    
    elif args.command == "diff":
        pending = manager.calculate_pending_migrations()
        if not pending:
            print("✅ 数据库schema已是最新版本")
        else:
            for migration in pending:
                print(manager.generate_diff(migration))
    
    elif args.command == "snapshot":
        output = manager.export_snapshot(args.output)
        print(f"📸 快照已导出到: {output}")
    
    elif args.command == "history":
        history = manager.get_migration_history()
        if not history:
            print("暂无迁移历史")
        else:
            print(f"迁移历史 ({len(history)}条):")
            for record in history:
                status = "✅" if record["success"] else "❌"
                print(f"   {status} v{record['version']}: {record['name']}")
                print(f"      {record['applied_at']}")
                if record["error_message"]:
                    print(f"      错误: {record['error_message']}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()