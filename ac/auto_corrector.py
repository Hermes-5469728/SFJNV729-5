"""自动修正器 - 处理 ValidationError 并尝试自动修复"""

from pydantic import ValidationError
from typing import Dict, Any, Optional
import json

class AutoCorrector:
    """自动修正器"""
    
    DEFAULT_VALUES = {
        "max_workers": 2,
        "timeout": 300,
        "max_retries": 3,
        "agents": [],
        "data": {},
        "params": {},
        "output": {}
    }
    
    TYPE_CONVERTERS = {
        "int": int,
        "integer": int,
        "float": float,
        "str": str,
        "string": str,
        "bool": bool,
        "boolean": bool,
        "list": list,
        "dict": dict,
        "object": dict,
    }
    
    def __init__(self):
        self.correction_history = []
    
    async def correct(self, error: ValidationError, original_input: Dict) -> Optional[Dict]:
        """尝试修正输入"""
        try:
            errors = error.errors()
            corrected = original_input.copy()
            
            for err in errors:
                loc = err['loc']
                err_type = err['type']
                msg = err['msg']
                
                # 获取字段名（处理嵌套）
                field_name = loc[-1] if isinstance(loc, tuple) else loc
                
                if err_type.startswith('missing'):
                    corrected = self._handle_missing_field(corrected, field_name)
                elif err_type.startswith('type_error'):
                    corrected = self._handle_type_error(corrected, field_name, err)
                elif err_type.startswith('value_error'):
                    corrected = self._handle_value_error(corrected, field_name, err)
                elif err_type.startswith('constrained'):
                    corrected = self._handle_constrained_error(corrected, field_name, err)
            
            # 记录修正历史
            self.correction_history.append({
                "original": original_input,
                "corrected": corrected,
                "errors": errors
            })
            
            return corrected
        
        except Exception as e:
            print(f"⚠️ 自动修正失败: {e}")
            return None
    
    def _handle_missing_field(self, data: Dict, field: str) -> Dict:
        """处理缺失字段"""
        if field in self.DEFAULT_VALUES:
            data[field] = self.DEFAULT_VALUES[field]
            print(f"🔧 自动填充缺失字段 '{field}' = {data[field]}")
        return data
    
    def _handle_type_error(self, data: Dict, field: str, err: Dict) -> Dict:
        """处理类型错误"""
        if field not in data:
            return data
        
        try:
            # 提取期望类型
            expected_type = err.get('ctx', {}).get('expected', 'str')
            expected_type = str(expected_type).lower()
            
            # 尝试转换
            converter = self.TYPE_CONVERTERS.get(expected_type)
            if converter:
                data[field] = converter(data[field])
                print(f"🔧 自动转换类型 '{field}': {type(data[field]).__name__} -> {expected_type}")
        except Exception:
            pass
        
        return data
    
    def _handle_value_error(self, data: Dict, field: str, err: Dict) -> Dict:
        """处理值错误"""
        # 尝试使用默认值
        if field in self.DEFAULT_VALUES:
            data[field] = self.DEFAULT_VALUES[field]
            print(f"🔧 自动修正值错误 '{field}' -> {data[field]}")
        return data
    
    def _handle_constrained_error(self, data: Dict, field: str, err: Dict) -> Dict:
        """处理约束错误（如 min/max）"""
        if field in data:
            # 尝试调整到合法范围
            if field == 'max_workers':
                data[field] = max(1, min(10, data.get(field, 2)))
                print(f"🔧 自动修正约束 '{field}' -> {data[field]}")
        return data

async def auto_correct_validation_error(error: ValidationError, input_data: Dict = {}) -> Optional[Dict]:
    """修正验证错误的快捷函数"""
    corrector = AutoCorrector()
    return await corrector.correct(error, input_data)