"""
LangGraph Workflow Engine - 多AI工作流引擎

核心功能：
1. 确定性状态机架构（任务编排）
2. 防御管道与闭环校验（免疫系统）
3. 多模型路由策略（精准分工）
4. 可观测性与日志链路（黑盒破局）
5. 循环迭代与反馈闭环（进化能力）

OpenCode Hooks:
  /workflow start <task_type> <input>    # 启动工作流
  /workflow status <task_id>             # 查询工作流状态
  /workflow stop <task_id>               # 停止工作流
  /workflow list                         # 列出所有工作流
  /workflow logs <task_id>               # 查看工作流日志
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, TypedDict
from enum import Enum
from loguru import logger
import sqlite3

try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint import SQLiteCheckpoint
    HAS_LANGGRAPH = True
except ImportError:
    logger.warning("LangGraph not installed, using mock implementation")
    HAS_LANGGRAPH = False

class TaskType(Enum):
    """任务类型枚举"""
    CODE_GENERATION = "code_generation"
    NOVEL_WRITING = "novel_writing"
    PPT_GENERATION = "ppt_generation"
    VIDEO_SCRIPT = "video_script"
    ARCHITECTURE_DESIGN = "architecture_design"
    REVIEW = "review"

class ModelType(Enum):
    """模型类型枚举"""
    DEEPSEEK = "deepseek"
    CLAUDE = "claude"
    QIANWEN = "qianwen"
    GEMINI = "gemini"
    GPT4O = "gpt4o"
    LIGHTWEIGHT = "lightweight"

class WorkflowState(TypedDict):
    """工作流状态定义"""
    task_id: str
    task_type: str
    input: str
    output: str
    current_node: str
    history: List[Dict[str, Any]]
    iteration_count: int
    max_iterations: int
    status: str
    errors: List[str]
    model_choices: Dict[str, str]

class ValidationResult(TypedDict):
    """校验结果"""
    passed: bool
    message: str
    corrections: List[str]

class WorkflowEngine:
    """多AI工作流引擎"""
    
    def __init__(self):
        self.workflows = {}  # task_id -> workflow_data
        self.db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'workflow.db'
        )
        self._init_database()
        logger.info("LangGraph工作流引擎初始化完成")
    
    def _init_database(self):
        """初始化工作流数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflows (
                task_id TEXT PRIMARY KEY,
                task_type TEXT,
                input TEXT,
                output TEXT,
                status TEXT,
                current_node TEXT,
                iteration_count INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                node_name TEXT,
                timestamp TEXT,
                input TEXT,
                output TEXT,
                model_used TEXT,
                duration_ms INTEGER,
                error TEXT,
                FOREIGN KEY (task_id) REFERENCES workflows(task_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _generate_task_id(self) -> str:
        """生成唯一任务ID"""
        return f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
    
    def _get_model_for_task(self, task_type: str) -> str:
        """根据任务类型选择最优模型"""
        model_mapping = {
            TaskType.CODE_GENERATION.value: ModelType.DEEPSEEK.value,
            TaskType.ARCHITECTURE_DESIGN.value: ModelType.DEEPSEEK.value,
            TaskType.REVIEW.value: ModelType.CLAUDE.value,
            TaskType.NOVEL_WRITING.value: ModelType.QIANWEN.value,
            TaskType.PPT_GENERATION.value: ModelType.LIGHTWEIGHT.value,
            TaskType.VIDEO_SCRIPT.value: ModelType.GEMINI.value,
        }
        return model_mapping.get(task_type, ModelType.GPT4O.value)
    
    # === 防御管道校验节点 ===
    
    def validate_input(self, state: WorkflowState) -> WorkflowState:
        """输入层校验：检查需求是否合规、是否有歧义"""
        logger.info(f"[校验节点] 输入校验 - 任务: {state['task_id']}")
        
        input_text = state['input']
        issues = []
        
        # 检查长度
        if len(input_text) < 10:
            issues.append("需求描述过短，请提供更详细的信息")
        
        # 检查是否包含敏感内容
        sensitive_words = ["违法", "违规", "攻击", "破解"]
        for word in sensitive_words:
            if word in input_text:
                issues.append(f"检测到敏感内容: {word}")
        
        # 检查是否超出范围
        if "写病毒" in input_text or "黑客攻击" in input_text:
            issues.append("请求内容超出服务范围")
        
        if issues:
            state['errors'].extend(issues)
            state['status'] = "failed"
            self._log_node(state['task_id'], "input_validation", input_text, 
                        f"校验失败: {', '.join(issues)}", "validation", 0, None)
        else:
            state['history'].append({
                "node": "input_validation",
                "status": "passed",
                "message": "输入校验通过"
            })
            self._log_node(state['task_id'], "input_validation", input_text, 
                        "校验通过", "validation", 0, None)
        
        return state
    
    def validate_output(self, state: WorkflowState) -> WorkflowState:
        """输出层校验：检查是否符合交付标准"""
        logger.info(f"[校验节点] 输出校验 - 任务: {state['task_id']}")
        
        output = state['output']
        issues = []
        
        # 检查输出是否为空
        if not output or len(output.strip()) < 10:
            issues.append("输出内容过短")
        
        # 检查格式
        if state['task_type'] == TaskType.CODE_GENERATION.value:
            if not (output.startswith('```') or 'def ' in output or 'class ' in output):
                issues.append("代码输出格式不正确")
        
        # 检查内容质量
        if len(output.split()) < 50:
            issues.append("输出内容不够详细")
        
        if issues:
            state['errors'].extend(issues)
            self._log_node(state['task_id'], "output_validation", output, 
                        f"校验失败: {', '.join(issues)}", "validation", 0, None)
            return self._decide_retry(state)
        else:
            state['history'].append({
                "node": "output_validation",
                "status": "passed",
                "message": "输出校验通过"
            })
            self._log_node(state['task_id'], "output_validation", output, 
                        "校验通过", "validation", 0, None)
            state['status'] = "completed"
        
        return state
    
    def validate_contract(self, state: WorkflowState) -> WorkflowState:
        """契约校验：检查是否符合架构规范/世界观设定"""
        logger.info(f"[校验节点] 契约校验 - 任务: {state['task_id']}")
        
        output = state['output']
        issues = []
        
        # 架构规范检查（代码任务）
        if state['task_type'] == TaskType.CODE_GENERATION.value:
            # 检查是否有注释
            if '"""' not in output and "'''" not in output and '#' not in output:
                issues.append("代码缺少注释")
            # 检查函数命名
            if 'def ' in output and not any(name.islower() for name in output.split('def ')[1:] if '(' in name):
                issues.append("函数命名不符合小写下划线规范")
        
        # 世界观一致性检查（小说任务）
        if state['task_type'] == TaskType.NOVEL_WRITING.value:
            if "魔法" in output and "科技" in output:
                issues.append("世界观存在矛盾：同时包含魔法和科技元素")
        
        if issues:
            state['errors'].extend(issues)
            self._log_node(state['task_id'], "contract_validation", output, 
                        f"校验失败: {', '.join(issues)}", "validation", 0, None)
            return self._decide_retry(state)
        else:
            state['history'].append({
                "node": "contract_validation",
                "status": "passed",
                "message": "契约校验通过"
            })
            self._log_node(state['task_id'], "contract_validation", output, 
                        "校验通过", "validation", 0, None)
            # 校验通过，重置重试标记
            state['needs_revision'] = False
        
        return state
    
    def _decide_retry(self, state: WorkflowState) -> WorkflowState:
        """决定是否重试"""
        if state['iteration_count'] < state['max_iterations']:
            state['iteration_count'] += 1
            state['status'] = "retrying"
            state['needs_revision'] = True
            logger.info(f"[重试] 任务 {state['task_id']} 第 {state['iteration_count']} 次重试")
        else:
            state['status'] = "failed"
            logger.error(f"[失败] 任务 {state['task_id']} 达到最大重试次数")
        
        return state
    
    # === AI生成节点 ===
    
    def generate_content(self, state: WorkflowState) -> WorkflowState:
        """AI内容生成节点"""
        task_type = state['task_type']
        model = self._get_model_for_task(task_type)
        
        logger.info(f"[生成节点] 任务: {state['task_id']}, 类型: {task_type}, 使用模型: {model}")
        
        # 模拟AI生成（实际应用中调用真实API）
        mock_outputs = {
            TaskType.CODE_GENERATION.value: self._mock_code_generation(state['input']),
            TaskType.NOVEL_WRITING.value: self._mock_novel_writing(state['input']),
            TaskType.PPT_GENERATION.value: self._mock_ppt_generation(state['input']),
            TaskType.VIDEO_SCRIPT.value: self._mock_video_script(state['input']),
            TaskType.ARCHITECTURE_DESIGN.value: self._mock_architecture_design(state['input']),
            TaskType.REVIEW.value: self._mock_review(state['input']),
        }
        
        output = mock_outputs.get(task_type, f"根据需求生成的{task_type}内容")
        
        state['output'] = output
        state['current_node'] = "contract_validation"
        state['model_choices']['generate'] = model
        
        self._log_node(state['task_id'], "generate", state['input'], output, model, 1500, None)
        
        return state
    
    def _mock_code_generation(self, input_text: str) -> str:
        """模拟代码生成"""
        return f'''"""
{input_text}
"""

def process_data(input_data: dict) -> dict:
    """
    处理数据函数
    :param input_data: 输入数据字典
    :return: 处理后的结果
    """
    result = {{}}
    # 核心处理逻辑
    for key, value in input_data.items():
        result[key] = value * 2
    return result

if __name__ == "__main__":
    test_input = {{"a": 1, "b": 2, "c": 3}}
    print(process_data(test_input))
'''
    
    def _mock_novel_writing(self, input_text: str) -> str:
        """模拟小说创作"""
        return f'''# {input_text}

在一个遥远的星系，人类已经掌握了星际旅行的奥秘。

## 第一章：启程

"船长，前方发现未知信号。"通讯官的声音打破了指挥舱的宁静。

李逸船长抬起头，目光透过舷窗望向深邃的星空。三十年的航行经验告诉他，这片星域并不应该有任何文明存在。

"分析信号来源。"他命令道，手指轻轻敲击着控制台。

## 第二章：发现

信号来自一颗隐藏在星云背后的行星。当飞船缓缓靠近时，所有人都屏住了呼吸——

这是一颗完美的蓝色星球，与地球惊人地相似。
'''
    
    def _mock_ppt_generation(self, input_text: str) -> str:
        """模拟PPT生成"""
        return f'''# {input_text}

## 目录
1. 项目背景
2. 核心目标
3. 技术方案
4. 实施计划
5. 预期成果

## 一、项目背景
- 行业现状分析
- 市场需求调研
- 痛点与挑战

## 二、核心目标
- 目标1：提升效率 50%
- 目标2：降低成本 30%
- 目标3：优化用户体验

## 三、技术方案
- 架构设计
- 技术选型
- 关键实现

## 四、实施计划
| 阶段 | 时间 | 任务 |
|------|------|------|
| 第一阶段 | 1-2月 | 需求分析 |
| 第二阶段 | 3-4月 | 系统开发 |
| 第三阶段 | 5月 | 测试上线 |

## 五、预期成果
- 交付物清单
- 验收标准
- 成功指标
'''
    
    def _mock_video_script(self, input_text: str) -> str:
        """模拟视频脚本生成"""
        return f'''# {input_text}

## 视频脚本

### 开场 (0:00-0:10)
[镜头] 全景星空，镜头缓缓推进
[旁白] 在浩瀚的宇宙中，每一颗星辰都有它的故事...

### 主体 (0:10-1:30)
[镜头] 飞船穿越虫洞的特效画面
[旁白] 人类从未停止探索的脚步...

### 高潮 (1:30-2:00)
[镜头] 发现新星球的震撼画面
[旁白] 当我们仰望星空，我们在寻找什么？

### 结尾 (2:00-2:15)
[镜头] 飞船飞向远方
[旁白] 探索永无止境...
'''
    
    def _mock_architecture_design(self, input_text: str) -> str:
        """模拟架构设计"""
        return f'''# {input_text}

## 系统架构设计

### 一、架构概述
采用微服务架构，基于云原生技术栈构建。

### 二、架构图
```
┌─────────────────────────────────────────────┐
│              API Gateway                    │
├─────────────────────────────────────────────┤
│  Service A  │  Service B  │  Service C    │
├─────────────────────────────────────────────┤
│              Message Queue                  │
├─────────────────────────────────────────────┤
│           Database Cluster                  │
└─────────────────────────────────────────────┘
```

### 三、关键组件
1. **网关层**：统一入口，负载均衡
2. **服务层**：业务逻辑处理
3. **消息队列**：异步解耦
4. **数据层**：高可用存储

### 四、技术选型
- 语言：Python 3.10+
- 框架：FastAPI
- 数据库：PostgreSQL + Redis
- 容器：Docker + Kubernetes
'''
    
    def _mock_review(self, input_text: str) -> str:
        """模拟评审"""
        return f'''# 评审报告

## 评审对象
{input_text[:50]}...

## 评审结果

### 优点 ✓
1. 架构设计合理
2. 代码结构清晰
3. 文档齐全

### 需要改进 ✗
1. 增加单元测试覆盖率
2. 优化性能瓶颈
3. 加强错误处理

## 综合评价
通过，建议在部署前完成上述改进项。

评审人：AI系统
评审时间：{datetime.now().isoformat()}
'''
    
    # === 可观测性 ===
    
    def _log_node(self, task_id: str, node_name: str, input_data: str, 
                 output_data: str, model_used: str, duration_ms: int, error: Optional[str]):
        """记录节点执行日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO workflow_logs 
            (task_id, node_name, timestamp, input, output, model_used, duration_ms, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (task_id, node_name, datetime.now().isoformat(), 
            input_data[:500], output_data[:500], model_used, duration_ms, error))
        conn.commit()
        conn.close()
    
    def get_workflow_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """获取工作流日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM workflow_logs WHERE task_id = ? ORDER BY timestamp', (task_id,))
        logs = []
        for row in cursor.fetchall():
            logs.append({
                'id': row[0],
                'task_id': row[1],
                'node_name': row[2],
                'timestamp': row[3],
                'input': row[4],
                'output': row[5],
                'model_used': row[6],
                'duration_ms': row[7],
                'error': row[8]
            })
        conn.close()
        return logs
    
    # === 工作流执行 ===
    
    def start_workflow(self, task_type: str, input_text: str, max_iterations: int = 3) -> str:
        """启动工作流"""
        task_id = self._generate_task_id()
        
        state: WorkflowState = {
            'task_id': task_id,
            'task_type': task_type,
            'input': input_text,
            'output': "",
            'current_node': "input_validation",
            'history': [],
            'iteration_count': 0,
            'max_iterations': max_iterations,
            'status': "running",
            'errors': [],
            'model_choices': {}
        }
        
        # 保存到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO workflows (task_id, task_type, input, output, status, 
                                current_node, iteration_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (task_id, task_type, input_text, "", "running", "input_validation", 
            0, datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        # 执行工作流
        self._execute_workflow(state)
        
        return task_id
    
    def _execute_workflow(self, state: WorkflowState):
        """执行工作流（状态机）"""
        logger.info(f"[工作流启动] 任务: {state['task_id']}, 类型: {state['task_type']}")
        
        while True:
            if state['status'] in ["completed", "failed"]:
                break
                
            if state['status'] == "retrying":
                state['status'] = "running"  # 重置状态
                state['current_node'] = "generate"
            
            if state['current_node'] == "input_validation":
                state = self.validate_input(state)
                if state['status'] != "failed":
                    state['current_node'] = "generate"
            
            elif state['current_node'] == "generate":
                state = self.generate_content(state)
                state['current_node'] = "contract_validation"
            
            elif state['current_node'] == "contract_validation":
                state = self.validate_contract(state)
                # 只有在运行状态且不需要修订时才进入下一步
                if state['status'] == "running" and state.get('needs_revision', False) == False:
                    state['current_node'] = "output_validation"
            
            elif state['current_node'] == "output_validation":
                state = self.validate_output(state)
            
            else:
                state['status'] = "completed"
                break
        
        # 更新数据库状态
        self._update_workflow_state(state)
        logger.info(f"[工作流结束] 任务: {state['task_id']}, 状态: {state['status']}")
    
    def _update_workflow_state(self, state: WorkflowState):
        """更新工作流状态到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE workflows SET output=?, status=?, current_node=?, 
                            iteration_count=?, updated_at=?
            WHERE task_id=?
        ''', (state['output'], state['status'], state['current_node'], 
            state['iteration_count'], datetime.now().isoformat(), state['task_id']))
        conn.commit()
        conn.close()
    
    def get_workflow_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM workflows WHERE task_id = ?', (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'task_id': row[0],
                'task_type': row[1],
                'input': row[2],
                'output': row[3],
                'status': row[4],
                'current_node': row[5],
                'iteration_count': row[6],
                'created_at': row[7],
                'updated_at': row[8]
            }
        return None
    
    def list_workflows(self, limit: int = 10) -> List[Dict[str, Any]]:
        """列出工作流列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM workflows ORDER BY created_at DESC LIMIT ?', (limit,))
        workflows = []
        for row in cursor.fetchall():
            workflows.append({
                'task_id': row[0],
                'task_type': row[1],
                'status': row[4],
                'created_at': row[7]
            })
        conn.close()
        return workflows
    
    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM workflows WHERE status = "running"')
        running_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM workflows WHERE status = "completed"')
        completed_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM workflows WHERE status = "failed"')
        failed_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM workflow_logs')
        log_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'running_workflows': running_count,
            'completed_workflows': completed_count,
            'failed_workflows': failed_count,
            'total_log_entries': log_count,
            'has_langgraph': HAS_LANGGRAPH
        }

# 创建全局引擎实例
_workflow_engine = None

def get_workflow_engine() -> WorkflowEngine:
    """获取工作流引擎单例"""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine

# 便捷函数
def start_workflow(task_type: str, input_text: str) -> str:
    """启动工作流的便捷函数"""
    engine = get_workflow_engine()
    return engine.start_workflow(task_type, input_text)

# 测试
if __name__ == "__main__":
    engine = get_workflow_engine()
    
    # 测试代码生成工作流
    task_id = engine.start_workflow("code_generation", "创建一个数据处理函数，输入字典，输出每个值翻倍后的字典")
    print(f"启动工作流: {task_id}")
    
    # 查看状态
    status = engine.get_workflow_status(task_id)
    print(f"\n工作流状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
    
    # 查看引擎状态
    engine_status = engine.get_status()
    print(f"\n引擎状态: {json.dumps(engine_status, indent=2, ensure_ascii=False)}")