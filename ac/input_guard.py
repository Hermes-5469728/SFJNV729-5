#!/usr/bin/env python3
"""
L0 层 · 输入守卫（Input Guard）

职责：
1. 强制 UTF-8 编码检测 - 确保所有输入都是合法的 UTF-8
2. 路径标准化 - 兼容 Windows/Linux/macOS
3. 环境变量类型安全加载 - 防止类型错误污染后续逻辑

核心原则：
- 防御性编程：在进入 L2 层之前过滤所有潜在问题
- 零信任：不信任任何外部输入
- 早期失败：在入口处发现问题，而不是在深层逻辑中

架构位置：
```
外部输入 ──→ [InputGuard L0] ──→ [Governor L1-L3] ──→ 业务逻辑
```
"""

import os
import sys
import re
import chardet
from pathlib import Path, PurePath, PureWindowsPath, PurePosixPath
from typing import Dict, Any, Optional, Union, List, Tuple
from dataclasses import dataclass
from enum import Enum

class GuardStatus(Enum):
    """守卫状态"""
    PASS = "pass"
    FIXED = "fixed"
    BLOCKED = "blocked"
    WARNING = "warning"

@dataclass
class GuardResult:
    """守卫校验结果"""
    status: GuardStatus
    category: str
    message: str
    details: Dict[str, Any] = None
    fixed_value: Optional[Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

class EncodingDetector:
    """
    编码检测器
    
    功能：
    1. 强制 UTF-8 校验
    2. 自动检测并修复编码问题
    3. 识别 BOM 头
    """
    
    # 常见编码（按优先级排序）
    COMMON_ENCODINGS = [
        'utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'big5',
        'latin-1', 'cp1252', 'iso-8859-1', 'shift_jis'
    ]
    
    @staticmethod
    def detect(data: bytes) -> Tuple[str, float]:
        """
        检测编码类型
        
        :param data: 字节流
        :return: (编码类型，置信度)
        """
        result = chardet.detect(data)
        return result['encoding'] or 'utf-8', result['confidence']
    
    @staticmethod
    def has_bom(data: bytes) -> bool:
        """
        检查是否有 BOM 头
        
        :param data: 字节流
        :return: 是否有 BOM
        """
        return data.startswith(b'\xef\xbb\xbf')
    
    @staticmethod
    def remove_bom(data: bytes) -> bytes:
        """
        移除 BOM 头
        
        :param data: 字节流
        :return: 移除 BOM 后的字节流
        """
        if EncodingDetector.has_bom(data):
            return data[3:]
        return data
    
    @staticmethod
    def strict_utf8_validate(data: bytes) -> Tuple[bool, Optional[str]]:
        """
        严格 UTF-8 校验
        
        :param data: 字节流
        :return: (是否有效，错误信息)
        """
        try:
            data.decode('utf-8', errors='strict')
            return True, None
        except UnicodeDecodeError as e:
            error_msg = (
                f"非法 UTF-8 字节序列：位置 {e.start}-{e.end}, "
                f"字节 {e.object[e.start:e.end].hex()}"
            )
            return False, error_msg
    
    @staticmethod
    def try_decode(data: bytes) -> Tuple[str, str, bool]:
        """
        尝试解码为字符串
        
        :param data: 字节流
        :return: (解码后的字符串，使用的编码，是否成功)
        """
        # 先检查 BOM
        if EncodingDetector.has_bom(data):
            data = EncodingDetector.remove_bom(data)
            # 有 BOM 默认是 UTF-8-SIG
            try:
                return data.decode('utf-8-sig'), 'utf-8-sig', True
            except:
                pass
        
        # 尝试常见编码
        for encoding in EncodingDetector.COMMON_ENCODINGS:
            try:
                decoded = data.decode(encoding, errors='strict')
                return decoded, encoding, True
            except (UnicodeDecodeError, LookupError):
                continue
        
        # 使用 chardet 检测
        detected_encoding, confidence = EncodingDetector.detect(data)
        if confidence > 0.7:
            try:
                decoded = data.decode(detected_encoding, errors='replace')
                return decoded, f"{detected_encoding}(detected)", True
            except:
                pass
        
        # 最后尝试 UTF-8 with replacement
        try:
            decoded = data.decode('utf-8', errors='replace')
            return decoded, 'utf-8(replace)', True
        except:
            return '', 'unknown', False
    
    @staticmethod
    def guard(content: Union[str, bytes]) -> GuardResult:
        """
        编码守卫
        
        :param content: 输入内容
        :return: 校验结果
        """
        # 转换为字节流
        if isinstance(content, str):
            data = content.encode('utf-8')
        elif isinstance(content, bytes):
            data = content
        else:
            return GuardResult(
                status=GuardStatus.BLOCKED,
                category="encoding",
                message=f"不支持的输入类型：{type(content).__name__}",
                details={"type": type(content).__name__}
            )
        
        # 严格 UTF-8 校验
        is_valid, error_msg = EncodingDetector.strict_utf8_validate(data)
        
        if is_valid:
            return GuardResult(
                status=GuardStatus.PASS,
                category="encoding",
                message="UTF-8 编码校验通过",
                details={"bytes_length": len(data)}
            )
        
        # 尝试修复
        decoded, used_encoding, success = EncodingDetector.try_decode(data)
        
        if success:
            # 检查是否有替换字符
            if '' in decoded:
                return GuardResult(
                    status=GuardStatus.WARNING,
                    category="encoding",
                    message="编码已修复，但包含替换字符",
                    details={
                        "original_error": error_msg,
                        "used_encoding": used_encoding,
                        "has_replacement_char": True
                    },
                    fixed_value=decoded
                )
            else:
                return GuardResult(
                    status=GuardStatus.FIXED,
                    category="encoding",
                    message=f"编码错误已修复：使用 {used_encoding} 重新解码",
                    details={
                        "original_error": error_msg,
                        "used_encoding": used_encoding
                    },
                    fixed_value=decoded
                )
        else:
            return GuardResult(
                status=GuardStatus.BLOCKED,
                category="encoding",
                message=f"编码错误无法修复：{error_msg}",
                details={"original_error": error_msg}
            )

class PathNormalizer:
    """
    路径标准化器
    
    功能：
    1. Windows 路径兼容（处理 \\ 和 /）
    2. 绝对路径转换
    3. 路径存在性检查
    4. 路径注入防护
    """
    
    @staticmethod
    def is_windows_path(path: str) -> bool:
        """
        判断是否为 Windows 路径
        
        :param path: 路径字符串
        :return: 是否为 Windows 路径
        """
        # 检查是否有盘符（如 C:）
        if len(path) >= 2 and path[1] == ':':
            return True
        # 检查是否有反斜杠
        if '\\' in path:
            return True
        return False
    
    @staticmethod
    def has_path_traversal(path: str) -> bool:
        """
        检查是否有路径穿越（..）
        
        :param path: 路径字符串
        :return: 是否有路径穿越
        """
        normalized = path.replace('\\', '/')
        parts = normalized.split('/')
        return '..' in parts
    
    @staticmethod
    def normalize(path: Union[str, Path], base_dir: Optional[str] = None) -> str:
        """
        标准化路径
        
        :param path: 路径
        :param base_dir: 基础目录（用于相对路径）
        :return: 标准化后的绝对路径
        """
        if isinstance(path, Path):
            path = str(path)
        
        # 移除前后引号
        path = path.strip().strip('"').strip("'")
        
        # 处理 Windows 路径
        if PathNormalizer.is_windows_path(path):
            # 将反斜杠转换为正斜杠（统一格式）
            path = path.replace('\\', '/')
        
        # 转换为 Path 对象
        path_obj = Path(path)
        
        # 如果是相对路径，添加基础目录
        if base_dir and not path_obj.is_absolute():
            path_obj = Path(base_dir) / path_obj
        
        # 转换为绝对路径
        path_obj = path_obj.resolve()
        
        # 在 Windows 上保持盘符大写
        if sys.platform == 'win32':
            path_str = str(path_obj)
            if len(path_str) >= 2 and path_str[1] == ':':
                path_str = path_str[0].upper() + path_str[1:]
            return path_str
        
        return str(path_obj)
    
    @staticmethod
    def validate(path: str, must_exist: bool = False) -> GuardResult:
        """
        路径守卫
        
        :param path: 路径
        :param must_exist: 是否必须存在
        :return: 校验结果
        """
        # 检查路径穿越
        if PathNormalizer.has_path_traversal(path):
            return GuardResult(
                status=GuardStatus.BLOCKED,
                category="path",
                message="检测到路径穿越攻击",
                details={"path": path, "has_traversal": True}
            )
        
        # 标准化路径
        try:
            normalized = PathNormalizer.normalize(path)
        except Exception as e:
            return GuardResult(
                status=GuardStatus.BLOCKED,
                category="path",
                message=f"路径标准化失败：{str(e)}",
                details={"path": path, "error": str(e)}
            )
        
        # 检查存在性
        if must_exist and not os.path.exists(normalized):
            return GuardResult(
                status=GuardStatus.BLOCKED,
                category="path",
                message=f"路径不存在：{normalized}",
                details={"path": normalized}
            )
        
        # 返回标准化路径
        return GuardResult(
            status=GuardStatus.PASS,
            category="path",
            message="路径校验通过",
            details={
                "original": path,
                "normalized": normalized,
                "exists": os.path.exists(normalized),
                "is_absolute": os.path.isabs(normalized)
            },
            fixed_value=normalized
        )

class EnvLoader:
    """
    环境变量加载器
    
    功能：
    1. 类型安全加载（自动类型转换）
    2. 默认值支持
    3. 必需变量检查
    4. 敏感变量脱敏
    """
    
    # 类型映射
    TYPE_MAP = {
        'int': int,
        'float': float,
        'bool': lambda x: x.lower() in ('true', '1', 'yes', 'on'),
        'str': str,
        'list': lambda x: x.split(',') if x else [],
        'dict': lambda x: dict(item.split('=') for item in x.split(',')) if x else {}
    }
    
    # 敏感变量模式
    SENSITIVE_PATTERNS = [
        r'.*password.*',
        r'.*secret.*',
        r'.*token.*',
        r'.*key.*',
        r'.*credential.*'
    ]
    
    @staticmethod
    def is_sensitive(var_name: str) -> bool:
        """
        判断变量是否敏感
        
        :param var_name: 变量名
        :return: 是否敏感
        """
        var_lower = var_name.lower()
        for pattern in EnvLoader.SENSITIVE_PATTERNS:
            if re.match(pattern, var_lower):
                return True
        return False
    
    @staticmethod
    def load(
        var_name: str,
        var_type: str = 'str',
        default: Any = None,
        required: bool = False,
        allow_empty: bool = False
    ) -> GuardResult:
        """
        环境变量守卫
        
        :param var_name: 变量名
        :param var_type: 变量类型 (int/float/bool/str/list/dict)
        :param default: 默认值
        :param required: 是否必需
        :param allow_empty: 是否允许为空
        :return: 校验结果
        """
        # 获取环境变量
        value = os.environ.get(var_name)
        
        # 检查必需性
        if value is None:
            if required:
                return GuardResult(
                    status=GuardStatus.BLOCKED,
                    category="env",
                    message=f"必需的环境变量未设置：{var_name}",
                    details={"var_name": var_name, "required": True}
                )
            else:
                return GuardResult(
                    status=GuardStatus.PASS,
                    category="env",
                    message=f"环境变量未设置，使用默认值",
                    details={
                        "var_name": var_name,
                        "default": default,
                        "is_sensitive": EnvLoader.is_sensitive(var_name)
                    },
                    fixed_value=default
                )
        
        # 检查空值
        if not value and not allow_empty:
            if required:
                return GuardResult(
                    status=GuardStatus.BLOCKED,
                    category="env",
                    message=f"环境变量为空：{var_name}",
                    details={"var_name": var_name}
                )
            else:
                return GuardResult(
                    status=GuardStatus.PASS,
                    category="env",
                    message="环境变量为空，使用默认值",
                    details={"var_name": var_name, "default": default},
                    fixed_value=default
                )
        
        # 类型转换
        try:
            converter = EnvLoader.TYPE_MAP.get(var_type, str)
            converted_value = converter(value)
        except Exception as e:
            return GuardResult(
                status=GuardStatus.BLOCKED,
                category="env",
                message=f"环境变量类型转换失败：{var_name}",
                details={
                    "var_name": var_name,
                    "value": value,
                    "expected_type": var_type,
                    "error": str(e)
                }
            )
        
        # 返回结果
        return GuardResult(
            status=GuardStatus.PASS,
            category="env",
            message=f"环境变量加载成功：{var_name}",
            details={
                "var_name": var_name,
                "type": var_type,
                "is_sensitive": EnvLoader.is_sensitive(var_name)
            },
            fixed_value=converted_value
        )
    
    @staticmethod
    def load_batch(config: Dict[str, Dict[str, Any]]) -> Dict[str, GuardResult]:
        """
        批量加载环境变量
        
        :param config: 配置字典 {var_name: {type, default, required}}
        :return: 校验结果字典
        """
        results = {}
        
        for var_name, var_config in config.items():
            result = EnvLoader.load(
                var_name=var_name,
                var_type=var_config.get('type', 'str'),
                default=var_config.get('default'),
                required=var_config.get('required', False),
                allow_empty=var_config.get('allow_empty', False)
            )
            results[var_name] = result
        
        return results

class InputGuard:
    """
    输入守卫 - L0 层防御模块
    
    统一接口：
    1. 编码检测
    2. 路径标准化
    3. 环境变量加载
    """
    
    def __init__(self):
        self.encoding_detector = EncodingDetector()
        self.path_normalizer = PathNormalizer()
        self.env_loader = EnvLoader()
    
    def guard_content(self, content: Union[str, bytes]) -> GuardResult:
        """
        守卫内容（编码检测）
        
        :param content: 输入内容
        :return: 校验结果
        """
        return self.encoding_detector.guard(content)
    
    def guard_path(
        self, 
        path: Union[str, Path], 
        base_dir: Optional[str] = None,
        must_exist: bool = False
    ) -> GuardResult:
        """
        守卫路径
        
        :param path: 路径
        :param base_dir: 基础目录
        :param must_exist: 是否必须存在
        :return: 校验结果
        """
        return self.path_normalizer.validate(path, must_exist)
    
    def guard_env(
        self,
        var_name: str,
        var_type: str = 'str',
        default: Any = None,
        required: bool = False
    ) -> GuardResult:
        """
        守卫环境变量
        
        :param var_name: 变量名
        :param var_type: 变量类型
        :param default: 默认值
        :param required: 是否必需
        :return: 校验结果
        """
        return self.env_loader.load(var_name, var_type, default, required)
    
    def guard_all(
        self,
        content: Optional[Union[str, bytes]] = None,
        paths: Optional[List[Union[str, Path]]] = None,
        env_vars: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, GuardResult]:
        """
        全面守卫（批量校验）
        
        :param content: 内容
        :param paths: 路径列表
        :param env_vars: 环境变量配置
        :return: 校验结果字典
        """
        results = {}
        
        # 校验内容
        if content is not None:
            results['content'] = self.guard_content(content)
        
        # 校验路径
        if paths:
            for i, path in enumerate(paths):
                results[f'path_{i}'] = self.guard_path(path)
        
        # 校验环境变量
        if env_vars:
            env_results = self.env_loader.load_batch(env_vars)
            results.update(env_results)
        
        return results

# 全局守卫实例
input_guard = InputGuard()

# CLI 入口
def main():
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Input Guard - L0 层防御模块")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # content 命令
    content_parser = subparsers.add_parser("content", help="守卫内容")
    content_parser.add_argument("--content", "-c", required=True, help="输入内容")
    content_parser.add_argument("--bytes", "-b", action="store_true", help="以字节流模式读取")
    
    # path 命令
    path_parser = subparsers.add_parser("path", help="守卫路径")
    path_parser.add_argument("--path", "-p", required=True, help="路径")
    path_parser.add_argument("--base", "-b", help="基础目录")
    path_parser.add_argument("--must-exist", action="store_true", help="必须存在")
    
    # env 命令
    env_parser = subparsers.add_parser("env", help="守卫环境变量")
    env_parser.add_argument("--var", "-v", required=True, help="变量名")
    env_parser.add_argument("--type", "-t", default="str", help="变量类型")
    env_parser.add_argument("--default", "-d", help="默认值")
    env_parser.add_argument("--required", action="store_true", help="必需")
    
    args = parser.parse_args()
    
    if args.command == "content":
        content = args.content
        if args.bytes:
            content = content.encode('utf-8')
        result = input_guard.guard_content(content)
        print(json.dumps({
            "status": result.status.value,
            "category": result.category,
            "message": result.message,
            "details": result.details,
            "fixed_value": result.fixed_value
        }, ensure_ascii=False, indent=2))
    
    elif args.command == "path":
        result = input_guard.guard_path(args.path, args.base, args.must_exist)
        print(json.dumps({
            "status": result.status.value,
            "category": result.category,
            "message": result.message,
            "details": result.details,
            "fixed_value": result.fixed_value
        }, ensure_ascii=False, indent=2))
    
    elif args.command == "env":
        default = args.default
        if args.type == 'int' and default:
            default = int(default)
        elif args.type == 'float' and default:
            default = float(default)
        elif args.type == 'bool' and default:
            default = default.lower() in ('true', '1', 'yes')
        
        result = input_guard.guard_env(args.var, args.type, default, args.required)
        print(json.dumps({
            "status": result.status.value,
            "category": result.category,
            "message": result.message,
            "details": result.details,
            "fixed_value": result.fixed_value
        }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
