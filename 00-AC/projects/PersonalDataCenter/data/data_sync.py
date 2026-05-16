"""
DADS Data Synchronization Tool - 数据同步工具

功能：
1. 从TXT文件导入数据到SQLite数据库
2. 从SQLite数据库导出数据到TXT文件
3. 数据完整性校验
4. 版本控制与回滚

OpenCode Hooks:
  /data sync-txt-to-db    # 同步TXT到数据库
  /data sync-db-to-txt    # 同步数据库到TXT
  /data validate          # 数据完整性校验
  /data backup            # 备份数据
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any
from loguru import logger

class DataSync:
    """数据同步管理器"""
    
    def __init__(self, db_path: str = None, data_dir: str = None):
        # 数据库路径：放在data目录下
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), 'dads_db.sqlite')
        # 数据文件路径：从opencode根目录读取data/dads_db
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        default_data_dir = os.path.join(root_dir, 'data', 'dads_db')
        self.data_dir = data_dir or default_data_dir
        self._init_database()
    
    def _init_database(self):
        """初始化SQLite数据库表结构"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建药物表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drugs (
                generic_name TEXT PRIMARY KEY,
                class TEXT,
                aliases TEXT,
                primary_guideline_source TEXT,
                last_verified TEXT
            )
        ''')
        
        # 创建药物相互作用表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                drug_a TEXT,
                drug_b TEXT,
                severity TEXT,
                mechanism TEXT,
                recommendation TEXT,
                source TEXT,
                last_verified TEXT,
                PRIMARY KEY (drug_a, drug_b)
            )
        ''')
        
        # 创建临床指南表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS guidelines (
                condition TEXT,
                guideline_source_year TEXT,
                key_point TEXT,
                evidence_level TEXT,
                last_verified TEXT,
                PRIMARY KEY (condition, guideline_source_year)
            )
        ''')
        
        # 创建安全信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS safety (
                drug TEXT PRIMARY KEY,
                pregnancy_category TEXT,
                lactation TEXT,
                hepatic_impairment TEXT,
                renal_impairment TEXT,
                source TEXT
            )
        ''')
        
        # 创建版本记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS version_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT,
                operation TEXT,
                timestamp TEXT,
                version TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")
    
    def _parse_txt_file(self, file_path: str, delimiter: str = '|') -> List[List[str]]:
        """解析TXT文件（返回列表列表，不含表头）"""
        records = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过注释行
                if line.startswith('#'):
                    continue
                # 空行
                if not line:
                    continue
                
                parts = [p.strip() for p in line.split(delimiter)]
                records.append(parts)
        
        return records
    
    def sync_txt_to_db(self) -> Dict[str, int]:
        """将TXT文件同步到数据库"""
        result = {
            'drugs': {'imported': 0, 'updated': 0, 'errors': 0},
            'interactions': {'imported': 0, 'updated': 0, 'errors': 0},
            'guidelines': {'imported': 0, 'updated': 0, 'errors': 0},
            'safety': {'imported': 0, 'updated': 0, 'errors': 0}
        }
        
        # 同步药物数据
        drugs_file = os.path.join(self.data_dir, 'drugs.txt')
        if os.path.exists(drugs_file):
            records = self._parse_txt_file(drugs_file)
            result['drugs'] = self._import_drugs(records)
        
        # 同步药物相互作用数据
        interactions_file = os.path.join(self.data_dir, 'interactions.txt')
        if os.path.exists(interactions_file):
            records = self._parse_txt_file(interactions_file)
            result['interactions'] = self._import_interactions(records)
        
        # 同步临床指南数据
        guidelines_file = os.path.join(self.data_dir, 'guidelines.txt')
        if os.path.exists(guidelines_file):
            records = self._parse_txt_file(guidelines_file)
            result['guidelines'] = self._import_guidelines(records)
        
        # 同步安全信息数据
        safety_file = os.path.join(self.data_dir, 'safety.txt')
        if os.path.exists(safety_file):
            records = self._parse_txt_file(safety_file)
            result['safety'] = self._import_safety(records)
        
        # 记录版本历史
        self._record_version('all', 'sync_txt_to_db')
        
        logger.info(f"Data sync completed: {result}")
        return result
    
    def _import_drugs(self, records: List[List[str]]) -> Dict[str, int]:
        """导入药物数据"""
        imported = 0
        updated = 0
        errors = 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for record in records:
            try:
                if len(record) < 5:
                    continue  # 跳过不完整的记录
                generic_name, drug_class, aliases, guideline_source, last_verified = record[:5]
                
                cursor.execute('SELECT 1 FROM drugs WHERE generic_name = ?', (generic_name,))
                exists = cursor.fetchone()
                
                if exists:
                    cursor.execute('''
                        UPDATE drugs SET class=?, aliases=?, primary_guideline_source=?, last_verified=?
                        WHERE generic_name=?
                    ''', (drug_class, aliases, guideline_source, last_verified, generic_name))
                    updated += 1
                else:
                    cursor.execute('''
                        INSERT INTO drugs (generic_name, class, aliases, primary_guideline_source, last_verified)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (generic_name, drug_class, aliases, guideline_source, last_verified))
                    imported += 1
            except Exception as e:
                logger.error(f"Error importing drug {record[0] if record else 'unknown'}: {e}")
                errors += 1
        
        conn.commit()
        conn.close()
        
        return {'imported': imported, 'updated': updated, 'errors': errors}
    
    def _import_interactions(self, records: List[List[str]]) -> Dict[str, int]:
        """导入药物相互作用数据"""
        imported = 0
        updated = 0
        errors = 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for record in records:
            try:
                if len(record) < 7:
                    continue
                drug_a, drug_b, severity, mechanism, recommendation, source, last_verified = record[:7]
                
                cursor.execute('SELECT 1 FROM interactions WHERE drug_a = ? AND drug_b = ?', (drug_a, drug_b))
                exists = cursor.fetchone()
                
                if exists:
                    cursor.execute('''
                        UPDATE interactions SET severity=?, mechanism=?, recommendation=?, source=?, last_verified=?
                        WHERE drug_a=? AND drug_b=?
                    ''', (severity, mechanism, recommendation, source, last_verified, drug_a, drug_b))
                    updated += 1
                else:
                    cursor.execute('''
                        INSERT INTO interactions (drug_a, drug_b, severity, mechanism, recommendation, source, last_verified)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (drug_a, drug_b, severity, mechanism, recommendation, source, last_verified))
                    imported += 1
            except Exception as e:
                logger.error(f"Error importing interaction {record[0]}-{record[1] if len(record)>1 else 'unknown'}: {e}")
                errors += 1
        
        conn.commit()
        conn.close()
        
        return {'imported': imported, 'updated': updated, 'errors': errors}
    
    def _import_guidelines(self, records: List[List[str]]) -> Dict[str, int]:
        """导入临床指南数据"""
        imported = 0
        updated = 0
        errors = 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for record in records:
            try:
                if len(record) < 5:
                    continue
                condition, guideline_source_year, key_point, evidence_level, last_verified = record[:5]
                
                cursor.execute('SELECT 1 FROM guidelines WHERE condition = ? AND guideline_source_year = ?', (condition, guideline_source_year))
                exists = cursor.fetchone()
                
                if exists:
                    cursor.execute('''
                        UPDATE guidelines SET key_point=?, evidence_level=?, last_verified=?
                        WHERE condition=? AND guideline_source_year=?
                    ''', (key_point, evidence_level, last_verified, condition, guideline_source_year))
                    updated += 1
                else:
                    cursor.execute('''
                        INSERT INTO guidelines (condition, guideline_source_year, key_point, evidence_level, last_verified)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (condition, guideline_source_year, key_point, evidence_level, last_verified))
                    imported += 1
            except Exception as e:
                logger.error(f"Error importing guideline {record[0] if record else 'unknown'}: {e}")
                errors += 1
        
        conn.commit()
        conn.close()
        
        return {'imported': imported, 'updated': updated, 'errors': errors}
    
    def _import_safety(self, records: List[List[str]]) -> Dict[str, int]:
        """导入安全信息数据"""
        imported = 0
        updated = 0
        errors = 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for record in records:
            try:
                if len(record) < 6:
                    continue
                drug, pregnancy_category, lactation, hepatic_impairment, renal_impairment, source = record[:6]
                
                cursor.execute('SELECT 1 FROM safety WHERE drug = ?', (drug,))
                exists = cursor.fetchone()
                
                if exists:
                    cursor.execute('''
                        UPDATE safety SET pregnancy_category=?, lactation=?, hepatic_impairment=?, renal_impairment=?, source=?
                        WHERE drug=?
                    ''', (pregnancy_category, lactation, hepatic_impairment, renal_impairment, source, drug))
                    updated += 1
                else:
                    cursor.execute('''
                        INSERT INTO safety (drug, pregnancy_category, lactation, hepatic_impairment, renal_impairment, source)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (drug, pregnancy_category, lactation, hepatic_impairment, renal_impairment, source))
                    imported += 1
            except Exception as e:
                logger.error(f"Error importing safety {record[0] if record else 'unknown'}: {e}")
                errors += 1
        
        conn.commit()
        conn.close()
        
        return {'imported': imported, 'updated': updated, 'errors': errors}
    
    def sync_db_to_txt(self) -> Dict[str, int]:
        """将数据库同步到TXT文件"""
        result = {}
        
        # 导出药物数据
        result['drugs'] = self._export_drugs()
        
        # 导出药物相互作用数据
        result['interactions'] = self._export_interactions()
        
        # 导出临床指南数据
        result['guidelines'] = self._export_guidelines()
        
        # 导出安全信息数据
        result['safety'] = self._export_safety()
        
        # 记录版本历史
        self._record_version('all', 'sync_db_to_txt')
        
        logger.info(f"Database export completed: {result}")
        return result
    
    def _export_drugs(self) -> int:
        """导出药物数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM drugs')
        rows = cursor.fetchall()
        conn.close()
        
        file_path = os.path.join(self.data_dir, 'drugs.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('# DADS Drug Database · National Expert Verified\n')
            f.write('# Format: generic_name | class | aliases(comma) | primary_guideline_source | last_verified\n')
            f.write('# Version: 1.1 · Last updated: {}\n'.format(datetime.now().strftime('%Y-%m-%d')))
            f.write('\n')
            for row in rows:
                f.write(' | '.join(str(r) for r in row) + '\n')
        
        return len(rows)
    
    def _export_interactions(self) -> int:
        """导出药物相互作用数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM interactions')
        rows = cursor.fetchall()
        conn.close()
        
        file_path = os.path.join(self.data_dir, 'interactions.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('# DADS Drug Interaction Database · National Expert Verified\n')
            f.write('# Format: drug_a | drug_b | severity | mechanism | recommendation | source | last_verified\n')
            f.write('# Version: 1.1 · Last updated: {}\n'.format(datetime.now().strftime('%Y-%m-%d')))
            f.write('\n')
            for row in rows:
                f.write(' | '.join(str(r) for r in row) + '\n')
        
        return len(rows)
    
    def _export_guidelines(self) -> int:
        """导出临床指南数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM guidelines')
        rows = cursor.fetchall()
        conn.close()
        
        file_path = os.path.join(self.data_dir, 'guidelines.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('# DADS Clinical Guidelines · National Expert Verified\n')
            f.write('# Format: condition | guideline_source_year | key_point | evidence_level | last_verified\n')
            f.write('# Version: 1.1 · Last updated: {}\n'.format(datetime.now().strftime('%Y-%m-%d')))
            f.write('\n')
            for row in rows:
                f.write(' | '.join(str(r) for r in row) + '\n')
        
        return len(rows)
    
    def _export_safety(self) -> int:
        """导出安全信息数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM safety')
        rows = cursor.fetchall()
        conn.close()
        
        file_path = os.path.join(self.data_dir, 'safety.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('# DADS Drug Safety Database · Pregnancy/Lactation/Hepatic/Renal\n')
            f.write('# Format: drug | pregnancy_category | lactation | hepatic_impairment | renal_impairment | source\n')
            f.write('# Version: 1.1 · Last updated: {}\n'.format(datetime.now().strftime('%Y-%m-%d')))
            f.write('\n')
            for row in rows:
                f.write(' | '.join(str(r) for r in row) + '\n')
        
        return len(rows)
    
    def validate_data(self) -> Dict[str, Any]:
        """数据完整性校验"""
        result = {
            'valid': True,
            'tables': {},
            'errors': []
        }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查药物表
        cursor.execute('SELECT COUNT(*) FROM drugs')
        drug_count = cursor.fetchone()[0]
        result['tables']['drugs'] = {'count': drug_count, 'valid': drug_count > 0}
        
        # 检查相互作用表
        cursor.execute('SELECT COUNT(*) FROM interactions')
        interaction_count = cursor.fetchone()[0]
        result['tables']['interactions'] = {'count': interaction_count, 'valid': interaction_count > 0}
        
        # 检查指南表
        cursor.execute('SELECT COUNT(*) FROM guidelines')
        guideline_count = cursor.fetchone()[0]
        result['tables']['guidelines'] = {'count': guideline_count, 'valid': guideline_count > 0}
        
        # 检查安全表
        cursor.execute('SELECT COUNT(*) FROM safety')
        safety_count = cursor.fetchone()[0]
        result['tables']['safety'] = {'count': safety_count, 'valid': safety_count > 0}
        
        # 检查药物引用完整性
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE drug_a NOT IN (SELECT generic_name FROM drugs)')
        invalid_drug_a = cursor.fetchone()[0]
        if invalid_drug_a > 0:
            result['valid'] = False
            result['errors'].append(f"Found {invalid_drug_a} interactions with invalid drug_a references")
        
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE drug_b NOT IN (SELECT generic_name FROM drugs)')
        invalid_drug_b = cursor.fetchone()[0]
        if invalid_drug_b > 0:
            result['valid'] = False
            result['errors'].append(f"Found {invalid_drug_b} interactions with invalid drug_b references")
        
        cursor.execute('SELECT COUNT(*) FROM safety WHERE drug NOT IN (SELECT generic_name FROM drugs)')
        invalid_safety_drug = cursor.fetchone()[0]
        if invalid_safety_drug > 0:
            result['valid'] = False
            result['errors'].append(f"Found {invalid_safety_drug} safety records with invalid drug references")
        
        conn.close()
        
        return result
    
    def _record_version(self, table_name: str, operation: str):
        """记录版本历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO version_history (table_name, operation, timestamp, version)
            VALUES (?, ?, ?, ?)
        ''', (table_name, operation, datetime.now().isoformat(), '1.1'))
        conn.commit()
        conn.close()
    
    def get_status(self) -> Dict[str, Any]:
        """获取数据同步状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM drugs')
        drug_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions')
        interaction_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM guidelines')
        guideline_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM safety')
        safety_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT timestamp FROM version_history ORDER BY id DESC LIMIT 1')
        last_sync = cursor.fetchone()
        last_sync = last_sync[0] if last_sync else None
        
        conn.close()
        
        return {
            'database_path': self.db_path,
            'data_dir': self.data_dir,
            'record_counts': {
                'drugs': drug_count,
                'interactions': interaction_count,
                'guidelines': guideline_count,
                'safety': safety_count
            },
            'last_sync': last_sync,
            'version': '1.1'
        }

# 测试同步
if __name__ == "__main__":
    sync = DataSync()
    
    # 同步TXT到数据库
    print("同步TXT到数据库...")
    result = sync.sync_txt_to_db()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 校验数据
    print("\n校验数据完整性...")
    validation = sync.validate_data()
    print(json.dumps(validation, indent=2, ensure_ascii=False))
    
    # 获取状态
    print("\n数据状态...")
    status = sync.get_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))