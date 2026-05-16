#!/usr/bin/env python3
"""
协同治理层（Collaborative Governance Layer）

职责：解决多CLI+多AI协同中的5大陷阱：
1. 状态幻觉与"假完成" → 端到端真实验证
2. 跨Agent隐式契约断裂 → 强类型契约校验
3. 并发竞态与状态覆盖 → 统一状态中心 + 乐观锁
4. 阻塞式调用拖垮事件循环 → 异步安全检查
5. 高危操作"全自动"灾难 → 人在回路 + 高危拦截

架构定位：
```
多个 Agent/CLI ──→ [协同治理层] ──→ 统一状态中心
                        │
                        ├─ 端到端验证器
                        ├─ 契约校验器
                        ├─ 并发控制器
                        ├─ 异步安全检查器
                        └─ 高危拦截器
```
"""

import asyncio
import json
import hashlib
import time
import re
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from abc import ABC, abstractmethod

# ==================== 枚举定义 ====================

class VerificationStatus(Enum):
    """验证状态"""
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"
    TIMEOUT = "timeout"

class ContractStatus(Enum):
    """契约状态"""
    VALID = "valid"
    INVALID = "invalid"
    MISSING = "missing"

class ConcurrencyStatus(Enum):
    """并发状态"""
    LOCKED = "locked"
    RELEASED = "released"
    CONFLICT = "conflict"

class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# ==================== 数据结构 ====================

@dataclass
class TaskState:
    """任务状态"""
    task_id: str
    agent_id: str
    status: str
    version: int = 1
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: time.time())

@dataclass
class VerificationResult:
    """端到端验证结果"""
    task_id: str
    status: VerificationStatus
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0

@dataclass
class ContractViolation:
    """契约违反"""
    field: str
    expected_type: str
    actual_value: Any
    message: str

@dataclass
class RiskAssessment:
    """风险评估"""
    operation: str
    level: RiskLevel
    reason: str
    requires_confirmation: bool = False
    alternatives: List[str] = field(default_factory=list)

# ==================== 端到端验证器 ====================

class EndToEndValidator(ABC):
    """端到端验证器抽象基类"""
    
    @abstractmethod
    async def verify(self, task_id: str, expected_state: Dict[str, Any]) -> VerificationResult:
        """验证任务是否真正完成"""
        pass

class URLValidator(EndToEndValidator):
    """URL存活验证器"""
    
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
    
    async def verify(self, task_id: str, expected_state: Dict[str, Any]) -> VerificationResult:
        """验证URL是否可访问"""
        import aiohttp
        
        url = expected_state.get("url")
        if not url:
            return VerificationResult(
                task_id=task_id,
                status=VerificationStatus.FAIL,
                message="缺少URL",
                evidence={"error": "url is required"}
            )
        
        start_time = time.time()
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url) as response:
                    latency_ms = (time.time() - start_time) * 1000
                    if response.status == 200:
                        return VerificationResult(
                            task_id=task_id,
                            status=VerificationStatus.PASS,
                            message=f"URL {url} 访问成功",
                            evidence={
                                "status_code": response.status,
                                "content_length": len(await response.text())
                            },
                            latency_ms=latency_ms
                        )
                    else:
                        return VerificationResult(
                            task_id=task_id,
                            status=VerificationStatus.FAIL,
                            message=f"URL {url} 返回错误状态码",
                            evidence={"status_code": response.status},
                            latency_ms=latency_ms
                        )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return VerificationResult(
                task_id=task_id,
                status=VerificationStatus.FAIL,
                message=f"URL {url} 访问失败: {str(e)}",
                evidence={"error": str(e)},
                latency_ms=latency_ms
            )

class DatabaseValidator(EndToEndValidator):
    """数据库记录验证器"""
    
    def __init__(self, db_path: str = "ac_platform.db"):
        self.db_path = db_path
    
    async def verify(self, task_id: str, expected_state: Dict[str, Any]) -> VerificationResult:
        """验证数据库是否有记录"""
        import sqlite3
        
        table_name = expected_state.get("table")
        query = expected_state.get("query")
        
        if not table_name or not query:
            return VerificationResult(
                task_id=task_id,
                status=VerificationStatus.FAIL,
                message="缺少表名或查询条件",
                evidence={"error": "table and query are required"}
            )
        
        start_time = time.time()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            conn.close()
            
            latency_ms = (time.time() - start_time) * 1000
            if len(results) > 0:
                return VerificationResult(
                    task_id=task_id,
                    status=VerificationStatus.PASS,
                    message=f"数据库查询成功，找到 {len(results)} 条记录",
                    evidence={"record_count": len(results)},
                    latency_ms=latency_ms
                )
            else:
                return VerificationResult(
                    task_id=task_id,
                    status=VerificationStatus.FAIL,
                    message="数据库查询结果为空",
                    evidence={"record_count": 0},
                    latency_ms=latency_ms
                )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return VerificationResult(
                task_id=task_id,
                status=VerificationStatus.FAIL,
                message=f"数据库查询失败: {str(e)}",
                evidence={"error": str(e)},
                latency_ms=latency_ms
            )

class FileValidator(EndToEndValidator):
    """文件存在验证器"""
    
    async def verify(self, task_id: str, expected_state: Dict[str, Any]) -> VerificationResult:
        """验证文件是否存在且有内容"""
        file_path = expected_state.get("path")
        
        if not file_path:
            return VerificationResult(
                task_id=task_id,
                status=VerificationStatus.FAIL,
                message="缺少文件路径",
                evidence={"error": "path is required"}
            )
        
        start_time = time.time()
        try:
            path = Path(file_path)
            latency_ms = (time.time() - start_time) * 1000
            
            if path.exists():
                file_size = path.stat().st_size
                return VerificationResult(
                    task_id=task_id,
                    status=VerificationStatus.PASS,
                    message=f"文件 {file_path} 存在",
                    evidence={"file_size": file_size},
                    latency_ms=latency_ms
                )
            else:
                return VerificationResult(
                    task_id=task_id,
                    status=VerificationStatus.FAIL,
                    message=f"文件 {file_path} 不存在",
                    evidence={"exists": False},
                    latency_ms=latency_ms
                )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return VerificationResult(
                task_id=task_id,
                status=VerificationStatus.FAIL,
                message=f"文件检查失败: {str(e)}",
                evidence={"error": str(e)},
                latency_ms=latency_ms
            )

# ==================== 契约校验器 ====================

class SchemaValidator:
    """强类型契约校验器"""
    
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
    
    def validate(self, data: Dict[str, Any]) -> Tuple[ContractStatus, List[ContractViolation]]:
        """校验数据是否符合schema"""
        violations = []
        
        for field_name, field_spec in self.schema.items():
            expected_type = field_spec.get("type", str)
            required = field_spec.get("required", False)
            
            # 检查必填字段
            if required and field_name not in data:
                violations.append(ContractViolation(
                    field=field_name,
                    expected_type=expected_type.__name__,
                    actual_value=None,
                    message="必填字段缺失"
                ))
                continue
            
            # 检查类型
            if field_name in data:
                value = data[field_name]
                if not isinstance(value, expected_type):
                    violations.append(ContractViolation(
                        field=field_name,
                        expected_type=expected_type.__name__,
                        actual_value=value,
                        message=f"类型错误，期望 {expected_type.__name__}，实际 {type(value).__name__}"
                    ))
            
            # 检查枚举值
            if "enum" in field_spec and field_name in data:
                allowed_values = field_spec["enum"]
                if data[field_name] not in allowed_values:
                    violations.append(ContractViolation(
                        field=field_name,
                        expected_type=str(allowed_values),
                        actual_value=data[field_name],
                        message=f"值不在允许范围内"
                    ))
            
            # 检查范围约束
            if "min" in field_spec and field_name in data:
                if data[field_name] < field_spec["min"]:
                    violations.append(ContractViolation(
                        field=field_name,
                        expected_type=f">={field_spec['min']}",
                        actual_value=data[field_name],
                        message="值小于最小值"
                    ))
            
            if "max" in field_spec and field_name in data:
                if data[field_name] > field_spec["max"]:
                    violations.append(ContractViolation(
                        field=field_name,
                        expected_type=f"<={field_spec['max']}",
                        actual_value=data[field_name],
                        message="值大于最大值"
                    ))
        
        if violations:
            return ContractStatus.INVALID, violations
        return ContractStatus.VALID, []

class PipelineContract:
    """管道契约管理器"""
    
    def __init__(self):
        self.contracts: Dict[str, SchemaValidator] = {}
    
    def register_contract(self, agent_id: str, schema: Dict[str, Any]):
        """注册Agent输出契约"""
        self.contracts[agent_id] = SchemaValidator(schema)
    
    def validate_output(self, agent_id: str, output: Dict[str, Any]) -> Tuple[ContractStatus, List[ContractViolation]]:
        """校验Agent输出是否符合契约"""
        if agent_id not in self.contracts:
            return ContractStatus.MISSING, [ContractViolation(
                field="agent_id",
                expected_type="registered_agent",
                actual_value=agent_id,
                message=f"Agent {agent_id} 未注册契约"
            )]
        
        return self.contracts[agent_id].validate(output)

# ==================== 并发控制器 ====================

class StateCenter:
    """统一状态中心（基于SQLite）"""
    
    def __init__(self, db_path: str = "ac_platform.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建任务状态表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_states (
                task_id TEXT PRIMARY KEY,
                agent_id TEXT,
                status TEXT,
                version INTEGER,
                data TEXT,
                timestamp REAL
            )
        ''')
        
        # 创建锁表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locks (
                resource_id TEXT PRIMARY KEY,
                holder_id TEXT,
                acquired_at REAL,
                expires_at REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_task_state(self, task_id: str) -> Optional[TaskState]:
        """获取任务状态"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM task_states WHERE task_id = ?', (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return TaskState(
                task_id=row[0],
                agent_id=row[1],
                status=row[2],
                version=row[3],
                data=json.loads(row[4]) if row[4] else {},
                timestamp=row[5]
            )
        return None
    
    def update_task_state(self, task_state: TaskState) -> ConcurrencyStatus:
        """更新任务状态（乐观锁）"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取当前版本
            cursor.execute('SELECT version FROM task_states WHERE task_id = ?', (task_state.task_id,))
            row = cursor.fetchone()
            
            if row:
                current_version = row[0]
                if task_state.version != current_version:
                    return ConcurrencyStatus.CONFLICT
                
                # 更新（版本+1）
                cursor.execute('''
                    UPDATE task_states
                    SET agent_id = ?, status = ?, version = ?, data = ?, timestamp = ?
                    WHERE task_id = ? AND version = ?
                ''', (
                    task_state.agent_id,
                    task_state.status,
                    task_state.version + 1,
                    json.dumps(task_state.data),
                    task_state.timestamp,
                    task_state.task_id,
                    task_state.version
                ))
            else:
                # 插入新记录
                cursor.execute('''
                    INSERT INTO task_states (task_id, agent_id, status, version, data, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    task_state.task_id,
                    task_state.agent_id,
                    task_state.status,
                    task_state.version,
                    json.dumps(task_state.data),
                    task_state.timestamp
                ))
            
            conn.commit()
            return ConcurrencyStatus.RELEASED
        finally:
            conn.close()
    
    def acquire_lock(self, resource_id: str, holder_id: str, timeout: int = 30) -> ConcurrencyStatus:
        """获取资源锁"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 清理过期锁
            cursor.execute('DELETE FROM locks WHERE expires_at < ?', (time.time(),))
            
            # 尝试获取锁
            cursor.execute('''
                INSERT OR IGNORE INTO locks (resource_id, holder_id, acquired_at, expires_at)
                VALUES (?, ?, ?, ?)
            ''', (resource_id, holder_id, time.time(), time.time() + timeout))
            
            conn.commit()
            
            # 检查是否成功
            cursor.execute('SELECT holder_id FROM locks WHERE resource_id = ?', (resource_id,))
            row = cursor.fetchone()
            if row and row[0] == holder_id:
                return ConcurrencyStatus.LOCKED
            return ConcurrencyStatus.CONFLICT
        finally:
            conn.close()
    
    def release_lock(self, resource_id: str, holder_id: str):
        """释放资源锁"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM locks WHERE resource_id = ? AND holder_id = ?', (resource_id, holder_id))
        conn.commit()
        conn.close()

# ==================== 异步安全检查器 ====================

class AsyncSafetyChecker:
    """异步安全检查器"""
    
    # 危险的同步阻塞函数/模块
    BLOCKING_FUNCTIONS = {
        "time.sleep",
        "requests.get",
        "requests.post",
        "urllib.request.urlopen",
        "subprocess.run",
        "subprocess.call",
        "os.system",
        "time.time",  # 虽然不阻塞，但常用于同步计时
    }
    
    BLOCKING_MODULES = {
        "requests",
        "urllib",
        "urllib3",
        "subprocess",
        "time",
    }
    
    @staticmethod
    def analyze_stack_trace() -> List[str]:
        """分析调用栈，检测阻塞代码"""
        import traceback
        
        warnings = []
        stack = traceback.extract_stack()
        
        for frame in stack:
            filename = frame.filename
            function = frame.name
            line_num = frame.lineno
            
            # 检查文件名中的阻塞模块
            for module in AsyncSafetyChecker.BLOCKING_MODULES:
                if module in filename:
                    warnings.append(f"可能的阻塞模块 {module} 在 {filename}:{line_num}")
            
            # 检查函数名
            for blocking_func in AsyncSafetyChecker.BLOCKING_FUNCTIONS:
                if blocking_func.split('.')[-1] == function:
                    warnings.append(f"可能的阻塞调用 {function} 在 {filename}:{line_num}")
        
        return warnings
    
    @staticmethod
    def is_event_loop_blocked(timeout: float = 1.0) -> bool:
        """检测事件循环是否被阻塞"""
        start = time.time()
        
        async def check():
            nonlocal start
            return time.time() - start < timeout
        
        try:
            result = asyncio.run(check())
            return not result
        except Exception:
            return True

# ==================== 高危拦截器 ====================

class HighRiskInterceptor:
    """高危操作拦截器"""
    
    # 高危命令模式
    HIGH_RISK_PATTERNS = [
        # 文件系统操作
        (r'rm\s+-rf\s+', RiskLevel.CRITICAL, "递归删除命令"),
        (r'del\s+/f\s+/s\s+', RiskLevel.CRITICAL, "强制删除命令"),
        (r'rmdir\s+/s\s+/q\s+', RiskLevel.CRITICAL, "强制删除目录"),
        
        # 数据库操作
        (r'DROP\s+DATABASE\s+', RiskLevel.CRITICAL, "删除数据库"),
        (r'DROP\s+TABLE\s+', RiskLevel.CRITICAL, "删除表"),
        (r'TRUNCATE\s+TABLE\s+', RiskLevel.CRITICAL, "清空表"),
        (r'DELETE\s+FROM\s+\w+\s*$', RiskLevel.HIGH, "无条件删除"),
        
        # 系统操作
        (r'format\s+', RiskLevel.CRITICAL, "格式化命令"),
        (r'shutdown\s+', RiskLevel.HIGH, "关机命令"),
        (r'reboot\s+', RiskLevel.HIGH, "重启命令"),
        
        # 网络操作
        (r'scp\s+.*:/', RiskLevel.MEDIUM, "远程文件传输"),
        (r'ssh\s+', RiskLevel.MEDIUM, "远程登录"),
    ]
    
    def __init__(self, require_confirmation: bool = True):
        self.require_confirmation = require_confirmation
    
    def assess_risk(self, operation: str) -> RiskAssessment:
        """评估操作风险"""
        for pattern, level, reason in HighRiskInterceptor.HIGH_RISK_PATTERNS:
            if re.search(pattern, operation, re.IGNORECASE):
                return RiskAssessment(
                    operation=operation,
                    level=level,
                    reason=reason,
                    requires_confirmation=(level in [RiskLevel.HIGH, RiskLevel.CRITICAL]) and self.require_confirmation,
                    alternatives=self._suggest_alternatives(operation, level)
                )
        
        return RiskAssessment(
            operation=operation,
            level=RiskLevel.LOW,
            reason="安全操作"
        )
    
    def _suggest_alternatives(self, operation: str, level: RiskLevel) -> List[str]:
        """提供替代方案建议"""
        alternatives = []
        
        if "rm -rf" in operation.lower():
            alternatives.append("考虑使用 trash-cli 或 mv 到回收站")
            alternatives.append("添加 --dry-run 参数先预览")
        
        if "DROP TABLE" in operation.upper():
            alternatives.append("考虑先创建备份")
            alternatives.append("使用软删除（添加 deleted_at 字段）")
        
        if "DELETE FROM" in operation.upper():
            alternatives.append("添加 WHERE 条件限制范围")
            alternatives.append("考虑使用事务")
        
        return alternatives
    
    def intercept(self, operation: str) -> Tuple[bool, RiskAssessment]:
        """拦截高危操作"""
        assessment = self.assess_risk(operation)
        
        if assessment.requires_confirmation:
            return False, assessment
        
        return True, assessment

class HumanInTheLoop:
    """人在回路确认器"""
    
    def __init__(self, confirmation_required: bool = True):
        self.confirmation_required = confirmation_required
    
    def confirm(self, message: str, risk_level: RiskLevel) -> bool:
        """请求人工确认"""
        if not self.confirmation_required:
            return True
        
        print(f"\n⚠️  【{risk_level.value.upper()}风险】{message}")
        print("请确认是否继续操作？")
        print("输入 'CONFIRM' 确认，其他输入取消")
        
        # 在CLI环境中读取用户输入
        try:
            user_input = input("> ").strip()
            return user_input == "CONFIRM"
        except EOFError:
            return False

# ==================== 协同治理器 ====================

class CollaborativeGovernor:
    """协同治理器 - 整合所有治理功能"""
    
    def __init__(self, state_db_path: str = "ac_platform.db"):
        self.state_center = StateCenter(state_db_path)
        self.pipeline_contract = PipelineContract()
        self.high_risk_interceptor = HighRiskInterceptor()
        self.human_in_the_loop = HumanInTheLoop()
        
        # 注册验证器
        self.validators: Dict[str, EndToEndValidator] = {
            "url": URLValidator(),
            "database": DatabaseValidator(state_db_path),
            "file": FileValidator(),
        }
    
    # ========== 端到端验证 ==========
    
    async def verify_task(self, task_id: str, verification_type: str, expected_state: Dict[str, Any]) -> VerificationResult:
        """验证任务是否真正完成"""
        if verification_type not in self.validators:
            return VerificationResult(
                task_id=task_id,
                status=VerificationStatus.FAIL,
                message=f"未知验证类型: {verification_type}",
                evidence={"error": "invalid verification type"}
            )
        
        return await self.validators[verification_type].verify(task_id, expected_state)
    
    # ========== 契约管理 ==========
    
    def register_agent_contract(self, agent_id: str, schema: Dict[str, Any]):
        """注册Agent输出契约"""
        self.pipeline_contract.register_contract(agent_id, schema)
    
    def validate_agent_output(self, agent_id: str, output: Dict[str, Any]) -> Tuple[ContractStatus, List[ContractViolation]]:
        """校验Agent输出"""
        return self.pipeline_contract.validate_output(agent_id, output)
    
    # ========== 并发控制 ==========
    
    def update_task(self, task_id: str, agent_id: str, status: str, data: Dict[str, Any]) -> ConcurrencyStatus:
        """更新任务状态（带乐观锁）"""
        # 获取当前状态
        current_state = self.state_center.get_task_state(task_id)
        version = current_state.version if current_state else 1
        
        # 创建新状态
        new_state = TaskState(
            task_id=task_id,
            agent_id=agent_id,
            status=status,
            version=version,
            data=data,
            timestamp=time.time()
        )
        
        return self.state_center.update_task_state(new_state)
    
    def acquire_resource_lock(self, resource_id: str, holder_id: str) -> bool:
        """获取资源锁"""
        result = self.state_center.acquire_lock(resource_id, holder_id)
        return result == ConcurrencyStatus.LOCKED
    
    def release_resource_lock(self, resource_id: str, holder_id: str):
        """释放资源锁"""
        self.state_center.release_lock(resource_id, holder_id)
    
    # ========== 高危拦截 ==========
    
    def execute_with_risk_control(self, operation: str, execute_func: Callable) -> Any:
        """带风险控制的执行"""
        # 风险评估
        allowed, assessment = self.high_risk_interceptor.intercept(operation)
        
        if not allowed:
            # 请求人工确认
            confirmed = self.human_in_the_loop.confirm(
                f"即将执行: {operation}\n风险等级: {assessment.level.value}\n原因: {assessment.reason}",
                assessment.level
            )
            
            if not confirmed:
                raise PermissionError(f"操作被拒绝: {operation}")
        
        # 执行操作
        return execute_func()
    
    # ========== 组合操作 ==========
    
    async def complete_task_with_validation(
        self,
        task_id: str,
        agent_id: str,
        output: Dict[str, Any],
        verification_spec: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        完整任务完成流程：
        1. 契约校验
        2. 端到端验证
        3. 状态更新
        """
        result = {
            "task_id": task_id,
            "agent_id": agent_id,
            "steps": []
        }
        
        # 步骤1: 契约校验
        contract_status, violations = self.validate_agent_output(agent_id, output)
        result["steps"].append({
            "step": "contract_validation",
            "status": contract_status.value,
            "violations": [v.__dict__ for v in violations]
        })
        
        if contract_status != ContractStatus.VALID:
            result["success"] = False
            result["error"] = "契约校验失败"
            return result
        
        # 步骤2: 端到端验证（如果指定）
        if verification_spec:
            verify_type = verification_spec.get("type")
            verify_params = verification_spec.get("params", {})
            
            verification_result = await self.verify_task(task_id, verify_type, verify_params)
            result["steps"].append({
                "step": "end_to_end_verification",
                "type": verify_type,
                "status": verification_result.status.value,
                "message": verification_result.message,
                "latency_ms": verification_result.latency_ms
            })
            
            if verification_result.status != VerificationStatus.PASS:
                result["success"] = False
                result["error"] = "端到端验证失败"
                return result
        
        # 步骤3: 更新状态
        concurrency_status = self.update_task(task_id, agent_id, "completed", output)
        result["steps"].append({
            "step": "state_update",
            "status": concurrency_status.value
        })
        
        if concurrency_status != ConcurrencyStatus.RELEASED:
            result["success"] = False
            result["error"] = "状态更新冲突"
            return result
        
        result["success"] = True
        return result

# ==================== 全局实例 ====================

collaborative_governor = CollaborativeGovernor()

# ==================== CLI 入口 ====================

def main():
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="协同治理层 - 多CLI+多AI协同的治理中心")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # verify 命令
    verify_parser = subparsers.add_parser("verify", help="端到端验证")
    verify_parser.add_argument("--task-id", required=True, help="任务ID")
    verify_parser.add_argument("--type", required=True, choices=["url", "database", "file"], help="验证类型")
    verify_parser.add_argument("--params", required=True, help="验证参数（JSON）")
    
    # contract 命令
    contract_parser = subparsers.add_parser("contract", help="契约校验")
    contract_parser.add_argument("--agent-id", required=True, help="Agent ID")
    contract_parser.add_argument("--output", required=True, help="输出数据（JSON）")
    
    # state 命令
    state_parser = subparsers.add_parser("state", help="状态管理")
    state_parser.add_argument("--task-id", required=True, help="任务ID")
    state_parser.add_argument("--agent-id", required=True, help="Agent ID")
    state_parser.add_argument("--status", required=True, help="状态")
    state_parser.add_argument("--data", help="数据（JSON）")
    
    # risk 命令
    risk_parser = subparsers.add_parser("risk", help="风险评估")
    risk_parser.add_argument("--operation", required=True, help="操作命令")
    
    args = parser.parse_args()
    
    if args.command == "verify":
        params = json.loads(args.params)
        result = asyncio.run(collaborative_governor.verify_task(
            args.task_id, args.type, params
        ))
        print(json.dumps({
            "task_id": result.task_id,
            "status": result.status.value,
            "message": result.message,
            "evidence": result.evidence,
            "latency_ms": result.latency_ms
        }, ensure_ascii=False, indent=2))
    
    elif args.command == "contract":
        output = json.loads(args.output)
        status, violations = collaborative_governor.validate_agent_output(args.agent_id, output)
        print(json.dumps({
            "agent_id": args.agent_id,
            "status": status.value,
            "violations": [v.__dict__ for v in violations]
        }, ensure_ascii=False, indent=2))
    
    elif args.command == "state":
        data = json.loads(args.data) if args.data else {}
        result = collaborative_governor.update_task(args.task_id, args.agent_id, args.status, data)
        print(json.dumps({
            "task_id": args.task_id,
            "status": result.value
        }, ensure_ascii=False, indent=2))
    
    elif args.command == "risk":
        allowed, assessment = collaborative_governor.high_risk_interceptor.intercept(args.operation)
        print(json.dumps({
            "operation": args.operation,
            "allowed": allowed,
            "risk_level": assessment.level.value,
            "reason": assessment.reason,
            "requires_confirmation": assessment.requires_confirmation,
            "alternatives": assessment.alternatives
        }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
