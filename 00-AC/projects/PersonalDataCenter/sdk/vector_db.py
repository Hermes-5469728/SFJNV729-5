"""
SDK Layer - Vector DB (向量数据库颗粒)
OpenCode Hook: /sdk vector-search <table> <query_vector> <top_k>
"""

import lancedb
import os
import numpy as np
from loguru import logger
from typing import List, Dict, Any, Optional

class VectorDB:
    """
    LanceDB向量数据库封装
    颗粒化模块：独立的向量存储与检索接口
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), '../data/lancedb')
        self.db = None
        self.tables = {}
        self._init_db()
    
    def _init_db(self):
        """初始化向量数据库连接"""
        try:
            os.makedirs(self.db_path, exist_ok=True)
            self.db = lancedb.connect(self.db_path)
            logger.info(f"LanceDB initialized at: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize LanceDB: {e}")
            raise
    
    def create_table(self, table_name: str, schema: Optional[Dict] = None):
        """创建向量表"""
        try:
            if table_name in self.tables:
                logger.warning(f"Table {table_name} already exists")
                return
            
            default_schema = {
                "vector": "fixed_size_list[float32, 1536]",
                "text": "string",
                "metadata": "map[string, string]"
            }
            
            table_schema = schema or default_schema
            self.db.create_table(table_name, schema=table_schema)
            self.tables[table_name] = self.db.open_table(table_name)
            logger.info(f"Created table: {table_name}")
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            raise
    
    def open_table(self, table_name: str):
        """打开已存在的表"""
        try:
            if table_name not in self.tables:
                self.tables[table_name] = self.db.open_table(table_name)
            return self.tables[table_name]
        except Exception as e:
            logger.error(f"Failed to open table {table_name}: {e}")
            raise
    
    def insert(self, table_name: str, data: List[Dict]):
        """插入数据"""
        try:
            table = self.open_table(table_name)
            table.add(data)
            logger.info(f"Inserted {len(data)} records into {table_name}")
        except Exception as e:
            logger.error(f"Failed to insert data: {e}")
            raise
    
    def search(self, table_name: str, query_vector: np.ndarray, top_k: int = 5) -> List[Dict]:
        """
        向量检索
        OpenCode Hook: /sdk vector-search <table> <query_vector> <top_k>
        """
        try:
            table = self.open_table(table_name)
            results = table.search(query_vector).limit(top_k).to_list()
            logger.debug(f"Search completed: {len(results)} results found")
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def query(self, table_name: str, filter_condition: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """SQL查询"""
        try:
            table = self.open_table(table_name)
            if filter_condition:
                results = table.query().where(filter_condition).limit(limit).to_list()
            else:
                results = table.query().limit(limit).to_list()
            return results
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
    
    def delete(self, table_name: str, row_id: str):
        """删除记录"""
        try:
            table = self.open_table(table_name)
            table.delete(row_id)
            logger.info(f"Deleted record: {row_id}")
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态（OpenCode监控接口）"""
        return {
            "initialized": self.db is not None,
            "tables": list(self.tables.keys()),
            "db_path": self.db_path
        }