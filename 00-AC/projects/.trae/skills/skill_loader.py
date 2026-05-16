"""
Enhanced Skill Loader - 增强版技能加载器
支持从多个目录扫描技能，自动提取真值并存储到数据库
"""

import os
import re
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger

@dataclass
class Skill:
    """技能数据结构"""
    name: str
    description: str
    triggers: List[str]
    commands: List[str]
    metadata: Dict[str, Any]
    file_path: str
    enabled: bool = True

class EnhancedSkillLoader:
    """增强版技能加载器"""
    
    def __init__(self, skills_dirs: List[str] = None):
        self.skills_dirs = skills_dirs or [".trae/skills"]
        self.skills: Dict[str, Skill] = {}
        self.db_path = ".trae/skills/skills.db"
        self._init_database()
        self.load_all_skills()
    
    def _init_database(self):
        """初始化技能数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skills (
                name TEXT PRIMARY KEY,
                description TEXT,
                triggers TEXT,
                commands TEXT,
                metadata TEXT,
                file_path TEXT,
                enabled INTEGER DEFAULT 1,
                source_dir TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_truths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT,
                key TEXT,
                value TEXT,
                value_type TEXT,
                FOREIGN KEY (skill_name) REFERENCES skills(name)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_execution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT,
                command TEXT,
                timestamp TEXT,
                success INTEGER,
                error_message TEXT,
                FOREIGN KEY (skill_name) REFERENCES skills(name)
            )
        ''')
        
        cursor.execute("PRAGMA table_info(skills)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'source_dir' not in columns:
            cursor.execute('ALTER TABLE skills ADD COLUMN source_dir TEXT')
        
        conn.commit()
        conn.close()
        logger.info(f"技能数据库初始化完成: {self.db_path}")
    
    def _parse_yaml_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """解析 YAML Frontmatter"""
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return None
        
        frontmatter = match.group(1)
        result = {}
        
        lines = frontmatter.strip().split('\n')
        current_key = None
        current_list = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('- '):
                if current_key:
                    current_list.append(line[2:].strip())
                continue
            
            if ':' in line:
                if current_key and current_list:
                    result[current_key] = current_list
                    current_list = []
                
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if value.startswith('[') and value.endswith(']'):
                    result[key] = [item.strip() for item in value[1:-1].split(',')]
                elif value.lower() == 'true':
                    result[key] = True
                elif value.lower() == 'false':
                    result[key] = False
                elif value.replace('.', '').isdigit():
                    if '.' in value:
                        result[key] = float(value)
                    else:
                        result[key] = int(value)
                else:
                    result[key] = value
                current_key = key
        
        if current_key and current_list:
            result[current_key] = current_list
        
        return result
    
    def _extract_commands(self, content: str) -> List[str]:
        """从文档中提取 / 开头的命令"""
        commands = re.findall(r'(/\w+(?:\s+\w+)*(?:\s+<\w+>)*)', content)
        return list(set(commands))
    
    def _extract_truths(self, content: str) -> List[Dict[str, Any]]:
        """从文档中提取真值数据"""
        truths = []
        
        table_pattern = r'\|(.+)\|\n\|[-|]+\|\n((?:\|.+\|\n?)+)'
        for match in re.finditer(table_pattern, content):
            headers = [h.strip() for h in match.group(1).split('|') if h.strip()]
            rows = match.group(2).strip().split('\n')
            for row in rows:
                values = [v.strip() for v in row.split('|') if v.strip()]
                if len(values) == len(headers):
                    truth = dict(zip(headers, values))
                    truths.append(truth)
        
        code_pattern = r'```(\w+)?\n(.+?)```'
        for match in re.finditer(code_pattern, content, re.DOTALL):
            lang = match.group(1) or ''
            code = match.group(2)
            if lang.lower() in ('json', 'yaml', 'yml'):
                try:
                    data = json.loads(code) if lang.lower() == 'json' else self._parse_yaml_frontmatter(f'---\n{code}\n---')
                    if data:
                        truths.append(data)
                except:
                    pass
        
        return truths
    
    def _parse_skill_file(self, file_path: str, source_dir: str) -> Optional[Skill]:
        """解析单个技能文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            frontmatter = self._parse_yaml_frontmatter(content)
            if not frontmatter:
                frontmatter = {}
            
            name = frontmatter.get('name', Path(file_path).parent.name)
            description = frontmatter.get('description', frontmatter.get('description_zh', ''))
            triggers = frontmatter.get('triggers', [])
            metadata = frontmatter.get('metadata', {})
            
            commands = self._extract_commands(content)
            
            skill = Skill(
                name=name,
                description=description,
                triggers=triggers,
                commands=commands,
                metadata=metadata,
                file_path=file_path,
                enabled=True
            )
            
            self._save_truths_to_database(skill.name, content)
            
            return skill
        
        except Exception as e:
            logger.error(f"解析技能文件失败 {file_path}: {e}")
            return None
    
    def _save_truths_to_database(self, skill_name: str, content: str):
        """提取并保存真值到数据库"""
        truths = self._extract_truths(content)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for truth in truths:
            for key, value in truth.items():
                value_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                value_type = type(value).__name__
                
                cursor.execute('''
                    INSERT OR REPLACE INTO skill_truths 
                    (skill_name, key, value, value_type)
                    VALUES (?, ?, ?, ?)
                ''', (skill_name, key, value_str, value_type))
        
        conn.commit()
        conn.close()
    
    def _skill_exists(self, skill_name: str) -> bool:
        """检查技能是否已存在于数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM skills WHERE name = ?', (skill_name,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    
    def _save_to_database(self, skill: Skill, source_dir: str):
        """保存技能到数据库（如果不存在则插入）"""
        if self._skill_exists(skill.name):
            logger.debug(f"技能已存在，跳过: {skill.name}")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO skills 
            (name, description, triggers, commands, metadata, file_path, enabled, source_dir)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            skill.name,
            skill.description,
            json.dumps(skill.triggers),
            json.dumps(skill.commands),
            json.dumps(skill.metadata),
            skill.file_path,
            1 if skill.enabled else 0,
            source_dir
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"已插入新技能: {skill.name}")
    
    def load_all_skills(self):
        """加载所有技能文件"""
        self.skills.clear()
        
        for skills_dir in self.skills_dirs:
            if not os.path.exists(skills_dir):
                continue
            
            for item in os.listdir(skills_dir):
                item_path = os.path.join(skills_dir, item)
                
                if os.path.isdir(item_path):
                    skill_file = os.path.join(item_path, "SKILL.md")
                    if os.path.exists(skill_file):
                        skill = self._parse_skill_file(skill_file, skills_dir)
                        if skill:
                            self.skills[skill.name] = skill
                            self._save_to_database(skill, skills_dir)
                
                elif item.endswith('.md') and item != '00-SKILL-SPEC.md':
                    skill_name = item.replace('.md', '')
                    skill = self._parse_skill_file(item_path, skills_dir)
                    if skill:
                        self.skills[skill.name] = skill
                        self._save_to_database(skill, skills_dir)
        
        logger.info(f"共加载 {len(self.skills)} 个技能")
    
    def get_skill_by_command(self, command: str) -> Optional[Skill]:
        """根据命令查找技能"""
        for skill in self.skills.values():
            for cmd in skill.commands:
                cmd_pattern = cmd.split()[0]
                if command.startswith(cmd_pattern):
                    return skill
        return None
    
    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        """根据名称查找技能"""
        return self.skills.get(name)
    
    def list_skills(self) -> List[Skill]:
        """获取所有技能列表"""
        return list(self.skills.values())
    
    def get_truths(self, skill_name: str = None) -> List[Dict[str, Any]]:
        """获取真值数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if skill_name:
            cursor.execute('SELECT * FROM skill_truths WHERE skill_name = ?', (skill_name,))
        else:
            cursor.execute('SELECT * FROM skill_truths')
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            _, s_name, key, value, value_type = row
            try:
                value = json.loads(value)
            except:
                pass
            results.append({
                'skill_name': s_name,
                'key': key,
                'value': value,
                'value_type': value_type
            })
        
        return results
    
    def get_commands(self) -> List[str]:
        """获取所有可用命令"""
        commands = []
        for skill in self.skills.values():
            commands.extend(skill.commands)
        return sorted(list(set(commands)))


# 全局技能加载器实例
skill_loader = None

def init_enhanced_skill_loader(skills_dirs: List[str] = None):
    """初始化全局技能加载器"""
    global skill_loader
    
    default_dirs = [
        ".trae/skills",
        os.path.expanduser("~/.agenthub-fork/skills"),
        os.path.expanduser("~/.local/share/opencode/worktree/global/calm-river/skills"),
    ]
    
    if skills_dirs:
        dirs_to_scan = skills_dirs
    else:
        dirs_to_scan = [d for d in default_dirs if os.path.exists(d)]
    
    skill_loader = EnhancedSkillLoader(dirs_to_scan)
    return skill_loader

def get_skill_loader() -> EnhancedSkillLoader:
    """获取全局技能加载器"""
    global skill_loader
    if skill_loader is None:
        skill_loader = EnhancedSkillLoader()
    return skill_loader

def process_command(command: str) -> Dict[str, Any]:
    """处理用户命令"""
    loader = get_skill_loader()
    
    if command.startswith('/skills'):
        parts = command.split()
        if len(parts) == 1:
            return {"success": True, "skills": [s.name for s in loader.list_skills()]}
        elif parts[1] == 'list':
            return {"success": True, "skills": [
                {"name": s.name, "description": s.description, "commands": s.commands}
                for s in loader.list_skills()
            ]}
        elif parts[1] == 'reload':
            loader.load_all_skills()
            return {"success": True, "message": f"已重新加载 {len(loader.list_skills())} 个技能"}
        elif parts[1] == 'info' and len(parts) > 2:
            skill = loader.get_skill_by_name(parts[2])
            if skill:
                return {"success": True, "skill": {
                    "name": skill.name,
                    "description": skill.description,
                    "triggers": skill.triggers,
                    "commands": skill.commands,
                    "metadata": skill.metadata
                }}
            return {"success": False, "error": "技能不存在"}
        elif parts[1] == 'truths':
            skill_name = parts[2] if len(parts) > 2 else None
            return {"success": True, "truths": loader.get_truths(skill_name)}
    
    skill = loader.get_skill_by_command(command)
    if skill:
        return {
            "success": True,
            "skill_name": skill.name,
            "command": command,
            "message": f"已识别技能命令: {skill.name}"
        }
    
    return {"success": False, "error": "未找到匹配的技能"}


if __name__ == "__main__":
    loader = init_enhanced_skill_loader()
    print(f"已加载 {len(loader.list_skills())} 个技能")
    print(f"已提取 {len(loader.get_truths())} 条真值")
    print("\n可用命令:")
    for cmd in loader.get_commands()[:20]:
        print(f"  {cmd}")
    print(f"... 还有 {len(loader.get_commands()) - 20} 个命令")