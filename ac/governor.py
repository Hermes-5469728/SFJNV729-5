#!/usr/bin/env python3
"""
治理层（Governance Layer）模块

职责：审查 Opencode 生成的输出，确保符合 AC 架构规范

核心功能：
1. L0 层 · 编码探针：UTF-8 严格校验、非法字节检测
2. L1 层 · 格式校验：JSON/代码语法检查
3. L2 层 · 规范校验：AC 架构目录结构和命名规范检查
4. L3 层 · 自动修正：小错误自动修复
5. 报告生成：明确的错误报告供 Opencode 重试

定位：作为 Opencode 输出后的中间件运行

架构层次：
L0 (Pre-Validation) → L1 (Format) → L2 (Spec) → L3 (AutoFix)
"""

import json
import ast
import os
import re
import chardet
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

class ValidationStatus(Enum):
    """校验状态"""
    PASS = "pass"
    FIXED = "fixed"
    ERROR = "error"
    WARNING = "warning"

@dataclass
class ValidationResult:
    """校验结果"""
    status: ValidationStatus
    category: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    fixed_content: Optional[str] = None

class EncodingError(Exception):
    """编码错误异常 - L0 层抛出"""
    def __init__(self, message: str, invalid_bytes: Optional[bytes] = None, 
                 position: Optional[int] = None, suggestion: Optional[str] = None):
        super().__init__(message)
        self.invalid_bytes = invalid_bytes
        self.position = position
        self.suggestion = suggestion

class EncodingProbe:
    """
    L0 层 · 编码探针（Encoding Probe）
    
    职责：
    1. 拦截原始 Payload：在任何 JSON 解析之前，先获取原始字节流
    2. 严格 UTF-8 校验：检查所有字符串字段是否包含非法 UTF-8 字节序列
    3. 检测替换字符：检查是否包含  (U+FFFD)，意味着上游已发生转码错误
    4. 自动清洗或阻断：
       - 发现非法字节 → 尝试用 utf-8-sig 或 chardet 重新解码
       - 无法修复 → 抛出 EncodingError，拒绝进入 L2 层
    
    核心原则：
    - 防污染：在 L0 层阻断编码错误，防止污染后续逻辑
    - 零容忍：非法 UTF-8 字节序列直接拒绝
    - 自动修复：尝试多种解码策略
    """
    
    # UTF-8 替换字符
    REPLACEMENT_CHAR = '\ufffd'  # 
    
    # 常见编码类型
    COMMON_ENCODINGS = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin-1', 'cp1252']
    
    @staticmethod
    def to_bytes(content: Union[str, bytes]) -> bytes:
        """
        将内容转换为字节流
        
        :param content: 字符串或字节流
        :return: 字节流
        """
        if isinstance(content, bytes):
            return content
        elif isinstance(content, str):
            # 尝试按 UTF-8 编码
            try:
                return content.encode('utf-8')
            except UnicodeEncodeError:
                # 如果包含无法编码的字符，使用 errors='replace'
                return content.encode('utf-8', errors='replace')
        else:
            return str(content).encode('utf-8')
    
    @staticmethod
    def detect_encoding(data: bytes) -> Tuple[str, float]:
        """
        检测字节流的编码类型
        
        :param data: 字节流
        :return: (编码类型，置信度)
        """
        result = chardet.detect(data)
        return result['encoding'] or 'utf-8', result['confidence']
    
    @staticmethod
    def has_replacement_char(content: str) -> bool:
        """
        检查是否包含替换字符 
        
        :param content: 内容
        :return: 是否包含替换字符
        """
        return EncodingProbe.REPLACEMENT_CHAR in content
    
    @staticmethod
    def find_invalid_utf8_bytes(data: bytes) -> List[Tuple[int, bytes]]:
        """
        找出所有非法 UTF-8 字节序列的位置
        
        :param data: 字节流
        :return: [(位置，非法字节), ...]
        """
        invalid_positions = []
        i = 0
        
        while i < len(data):
            byte = data[i]
            
            # 单字节 ASCII
            if byte < 0x80:
                i += 1
                continue
            
            # 多字节 UTF-8
            try:
                # 尝试解码 1-4 字节
                for length in [1, 2, 3, 4]:
                    if i + length > len(data):
                        continue
                    
                    chunk = data[i:i+length]
                    try:
                        chunk.decode('utf-8', errors='strict')
                        i += length
                        break
                    except UnicodeDecodeError:
                        if length == 4:
                            # 4 字节都无法解码，记录非法字节
                            invalid_positions.append((i, bytes([byte])))
                            i += 1
                        continue
            except Exception:
                invalid_positions.append((i, bytes([byte])))
                i += 1
        
        return invalid_positions
    
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
            error_msg = f"非法 UTF-8 字节序列：位置 {e.start}-{e.end}, 字节 {e.object[e.start:e.end].hex()}"
            return False, error_msg
    
    @staticmethod
    def try_redecode(data: bytes, original_content: str) -> Tuple[Optional[str], str]:
        """
        尝试用其他编码重新解码
        
        :param data: 原始字节流
        :param original_content: 原始字符串（可能已损坏）
        :return: (修复后的字符串，使用的编码)
        """
        # 尝试常见编码
        for encoding in EncodingProbe.COMMON_ENCODINGS:
            try:
                decoded = data.decode(encoding, errors='strict')
                # 检查是否还有替换字符
                if not EncodingProbe.has_replacement_char(decoded):
                    return decoded, encoding
            except (UnicodeDecodeError, LookupError):
                continue
        
        # 使用 chardet 检测
        detected_encoding, confidence = EncodingProbe.detect_encoding(data)
        if confidence > 0.7:
            try:
                decoded = data.decode(detected_encoding, errors='replace')
                return decoded, f"{detected_encoding}(detected)"
            except:
                pass
        
        # 最后尝试 utf-8-sig
        try:
            decoded = data.decode('utf-8-sig', errors='replace')
            return decoded, 'utf-8-sig'
        except:
            pass
        
        return None, 'unknown'
    
    @staticmethod
    def probe(content: Union[str, bytes], content_type: str = "auto") -> ValidationResult:
        """
        L0 层编码探针 - 预校验入口
        
        :param content: 待校验内容
        :param content_type: 内容类型
        :return: 校验结果
        """
        # 转换为字节流
        data = EncodingProbe.to_bytes(content)
        original_str = content if isinstance(content, str) else None
        
        # 1. 检查替换字符
        if original_str and EncodingProbe.has_replacement_char(original_str):
            # 上游已经发生转码错误
            return ValidationResult(
                status=ValidationStatus.ERROR,
                category="encoding_l0",
                message="检测到替换字符 ，上游已发生转码错误",
                details={
                    "error_type": "replacement_char_detected",
                    "position": original_str.find(EncodingProbe.REPLACEMENT_CHAR),
                    "suggestion": "请检查上游数据源编码设置"
                }
            )
        
        # 2. 严格 UTF-8 校验
        is_valid, error_msg = EncodingProbe.strict_utf8_validate(data)
        
        if not is_valid:
            # 发现非法 UTF-8 字节
            invalid_bytes = EncodingProbe.find_invalid_utf8_bytes(data)
            
            # 尝试重新解码
            fixed_content, used_encoding = EncodingProbe.try_redecode(data, original_str or "")
            
            if fixed_content:
                # 修复成功
                return ValidationResult(
                    status=ValidationStatus.FIXED,
                    category="encoding_l0",
                    message=f"编码错误已修复：使用 {used_encoding} 重新解码",
                    details={
                        "error_type": "invalid_utf8_bytes",
                        "original_error": error_msg,
                        "invalid_bytes_count": len(invalid_bytes),
                        "used_encoding": used_encoding
                    },
                    fixed_content=fixed_content
                )
            else:
                # 无法修复，抛出错误
                return ValidationResult(
                    status=ValidationStatus.ERROR,
                    category="encoding_l0",
                    message=f"编码错误无法修复：{error_msg}",
                    details={
                        "error_type": "unfixable_encoding_error",
                        "original_error": error_msg,
                        "invalid_bytes": [
                            {"position": pos, "hex": b.hex()}
                            for pos, b in invalid_bytes[:10]  # 限制数量
                        ],
                        "suggestion": "请检查数据源编码或使用正确的编码重新发送"
                    }
                )
        
        # 通过校验
        return ValidationResult(
            status=ValidationStatus.PASS,
            category="encoding_l0",
            message="UTF-8 编码校验通过",
            details={"bytes_length": len(data)}
        )

class FormatValidator:
    """L1 层 · 格式校验器"""
    
    @staticmethod
    def validate_json(content: str) -> ValidationResult:
        """校验 JSON 格式"""
        try:
            json.loads(content)
            return ValidationResult(
                status=ValidationStatus.PASS,
                category="json_format",
                message="JSON 格式正确"
            )
        except json.JSONDecodeError as e:
            # 尝试自动修复常见问题
            fixed, success = FormatValidator._fix_json(content)
            if success:
                return ValidationResult(
                    status=ValidationStatus.FIXED,
                    category="json_format",
                    message=f"JSON 格式错误已修复：{str(e)}",
                    details={"original_error": str(e)},
                    fixed_content=fixed
                )
            return ValidationResult(
                status=ValidationStatus.ERROR,
                category="json_format",
                message=f"JSON 格式错误：{str(e)}",
                details={"original_error": str(e)}
            )
    
    @staticmethod
    def _fix_json(content: str) -> Tuple[str, bool]:
        """尝试修复 JSON 格式错误"""
        fixed = content
        
        # 修复末尾缺少逗号
        fixed = re.sub(r'(\{|\[)\s*(\".*?\":)', r'\1\n\2', fixed)
        
        # 修复字符串未闭合
        lines = fixed.split('\n')
        in_string = False
        for i, line in enumerate(lines):
            quote_count = line.count('"')
            if quote_count % 2 != 0:
                # 尝试在末尾添加引号
                lines[i] = line.rstrip() + '"'
        
        fixed = '\n'.join(lines)
        
        # 验证修复是否成功
        try:
            json.loads(fixed)
            return fixed, True
        except:
            return content, False
    
    @staticmethod
    def validate_python(content: str) -> ValidationResult:
        """校验 Python 代码语法"""
        try:
            ast.parse(content)
            return ValidationResult(
                status=ValidationStatus.PASS,
                category="python_syntax",
                message="Python 语法正确"
            )
        except SyntaxError as e:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                category="python_syntax",
                message=f"Python 语法错误：{str(e)}",
                details={
                    "line": e.lineno,
                    "offset": e.offset,
                    "text": e.text.strip() if e.text else ""
                }
            )
    
    @staticmethod
    def validate_format(content: str, content_type: str = "auto") -> ValidationResult:
        """根据类型校验格式"""
        if content_type == "json" or (content_type == "auto" and content.strip().startswith('{')):
            return FormatValidator.validate_json(content)
        elif content_type == "python" or (content_type == "auto" and content.strip().startswith(('def ', 'class ', 'import '))):
            return FormatValidator.validate_python(content)
        else:
            return ValidationResult(
                status=ValidationStatus.WARNING,
                category="unknown_format",
                message="无法确定内容格式，跳过格式校验"
            )

class SpecValidator:
    """L2 层 · 规范校验器 - 基于 AC 架构规范"""
    
    # AC 架构目录结构规范
    REQUIRED_DIRS = [
        "src/core",
        "src/modules",
        "ac",
        "data",
        "docs"
    ]
    
    # 命名规范模式
    MODULE_NAME_PATTERN = r'^[a-z_]+$'
    CLASS_NAME_PATTERN = r'^[A-Z][a-zA-Z0-9]*$'
    FUNCTION_NAME_PATTERN = r'^[a-z_][a-z0-9_]*$'
    
    @staticmethod
    def validate_directory_structure(base_path: str) -> List[ValidationResult]:
        """校验目录结构是否符合 AC 架构"""
        results = []
        
        for required_dir in SpecValidator.REQUIRED_DIRS:
            full_path = os.path.join(base_path, required_dir)
            if not os.path.exists(full_path):
                results.append(ValidationResult(
                    status=ValidationStatus.WARNING,
                    category="directory_structure",
                    message=f"缺少必需目录：{required_dir}",
                    details={"expected_path": full_path}
                ))
        
        return results
    
    @staticmethod
    def validate_naming_conventions(content: str) -> List[ValidationResult]:
        """校验命名规范"""
        results = []
        
        # 检查类名
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            if not re.match(SpecValidator.CLASS_NAME_PATTERN, class_name):
                results.append(ValidationResult(
                    status=ValidationStatus.WARNING,
                    category="naming_convention",
                    message=f"类名不符合规范：{class_name}（应为大驼峰）",
                    details={"name": class_name, "type": "class"}
                ))
        
        # 检查函数名
        func_pattern = r'def\s+(\w+)\('
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            if not re.match(SpecValidator.FUNCTION_NAME_PATTERN, func_name):
                results.append(ValidationResult(
                    status=ValidationStatus.WARNING,
                    category="naming_convention",
                    message=f"函数名不符合规范：{func_name}（应为蛇形命名）",
                    details={"name": func_name, "type": "function"}
                ))
        
        return results
    
    @staticmethod
    def validate_ac_architecture(content: str) -> List[ValidationResult]:
        """校验是否符合 AC 架构定义"""
        results = []
        
        # 检查是否包含 AC 架构关键字
        required_keywords = ["AC", "Expert", "Governance", "L5", "SourceTracker"]
        for keyword in required_keywords:
            if keyword not in content:
                results.append(ValidationResult(
                    status=ValidationStatus.WARNING,
                    category="ac_architecture",
                    message=f"缺少 AC 架构关键字：{keyword}",
                    details={"keyword": keyword}
                ))
        
        return results

class AutoFixer:
    """L3 层 · 自动修复器"""
    
    @staticmethod
    def fix_naming_conventions(content: str) -> Tuple[str, List[str]]:
        """修复命名规范问题"""
        fixed = content
        fixes = []
        
        # 修复类名（转为大驼峰）
        def fix_class_name(match):
            name = match.group(1)
            fixed_name = ''.join(word.capitalize() for word in name.replace('_', ' ').split())
            fixes.append(f"类名：{name} → {fixed_name}")
            return f'class {fixed_name}'
        
        fixed = re.sub(r'class\s+(\w+)', fix_class_name, fixed)
        
        # 修复函数名（转为蛇形）
        def fix_func_name(match):
            name = match.group(1)
            # 转换为蛇形命名
            fixed_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
            fixes.append(f"函数名：{name} → {fixed_name}")
            return f'def {fixed_name}('
        
        fixed = re.sub(r'def\s+(\w+)\(', fix_func_name, fixed)
        
        return fixed, fixes
    
    @staticmethod
    def fix_import_order(content: str) -> Tuple[str, List[str]]:
        """修复 import 顺序"""
        lines = content.split('\n')
        import_lines = []
        other_lines = []
        fixes = []
        
        for line in lines:
            if line.startswith('import ') or line.startswith('from '):
                import_lines.append(line)
            else:
                other_lines.append(line)
        
        # 排序 import
        import_lines.sort()
        fixed = '\n'.join(import_lines + [''] + other_lines)
        
        if import_lines:
            fixes.append("已重新排序 import 语句")
        
        return fixed, fixes

class GovernanceReport:
    """治理报告"""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.fixed_content: Optional[str] = None
        self.l0_blocked = False  # L0 层是否阻断
    
    def add_result(self, result: ValidationResult):
        """添加校验结果"""
        self.results.append(result)
        
        # 如果 L0 层错误，标记为阻断
        if result.category == "encoding_l0" and result.status == ValidationStatus.ERROR:
            self.l0_blocked = True
    
    def has_errors(self) -> bool:
        """是否存在错误"""
        return any(r.status == ValidationStatus.ERROR for r in self.results)
    
    def has_fixes(self) -> bool:
        """是否有自动修复"""
        return any(r.status == ValidationStatus.FIXED for r in self.results)
    
    def is_l0_blocked(self) -> bool:
        """L0 层是否阻断"""
        return self.l0_blocked
    
    def get_summary(self) -> Dict[str, Any]:
        """获取报告摘要"""
        summary = {
            "total_checks": len(self.results),
            "passed": sum(1 for r in self.results if r.status == ValidationStatus.PASS),
            "fixed": sum(1 for r in self.results if r.status == ValidationStatus.FIXED),
            "errors": sum(1 for r in self.results if r.status == ValidationStatus.ERROR),
            "warnings": sum(1 for r in self.results if r.status == ValidationStatus.WARNING),
            "has_errors": self.has_errors(),
            "has_fixes": self.has_fixes(),
            "l0_blocked": self.is_l0_blocked()
        }
        return summary
    
    def to_json(self) -> str:
        """转换为 JSON"""
        report = {
            "summary": self.get_summary(),
            "results": [
                {
                    "status": r.status.value,
                    "category": r.category,
                    "message": r.message,
                    "details": r.details,
                    "fixed_content": r.fixed_content
                } for r in self.results
            ]
        }
        return json.dumps(report, ensure_ascii=False, indent=2)

class Governor:
    """治理者核心类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.encoding_probe = EncodingProbe()
        self.format_validator = FormatValidator()
        self.spec_validator = SpecValidator()
        self.auto_fixer = AutoFixer()
    
    def inspect(self, content: Union[str, bytes], content_type: str = "auto", 
                base_path: Optional[str] = None) -> GovernanceReport:
        """
        审查内容 - 作为中间件的核心接口
        
        校验流程：
        L0 (编码探针) → L1 (格式) → L2 (规范) → L3 (自动修复)
        
        :param content: 待审查的内容（可以是字符串或字节流）
        :param content_type: 内容类型 (json/python/auto)
        :param base_path: 项目基础路径（用于目录结构校验）
        :return: 治理报告
        """
        report = GovernanceReport()
        
        # L0 层：编码探针（预校验）
        l0_result = self.encoding_probe.probe(content, content_type)
        report.add_result(l0_result)
        
        # 如果 L0 层阻断，直接返回
        if l0_result.status == ValidationStatus.ERROR:
            return report
        
        # 使用 L0 层修复后的内容（如果有）
        current_content = l0_result.fixed_content or content
        if isinstance(current_content, bytes):
            current_content = current_content.decode('utf-8', errors='replace')
        
        # L1 层：格式校验
        format_result = self.format_validator.validate_format(current_content, content_type)
        report.add_result(format_result)
        
        # 如果 L1 层错误，停止后续校验
        if format_result.status == ValidationStatus.ERROR:
            return report
        
        # 使用 L1 层修复后的内容（如果有）
        if format_result.fixed_content:
            current_content = format_result.fixed_content
        
        # L2 层：规范校验
        naming_results = self.spec_validator.validate_naming_conventions(current_content)
        for r in naming_results:
            report.add_result(r)
        
        ac_results = self.spec_validator.validate_ac_architecture(current_content)
        for r in ac_results:
            report.add_result(r)
        
        # 目录结构校验（如果提供了路径）
        if base_path:
            dir_results = self.spec_validator.validate_directory_structure(base_path)
            for r in dir_results:
                report.add_result(r)
        
        # L3 层：自动修复
        if report.has_fixes():
            fixed_content, fixes = self._auto_fix(current_content)
            if fixes:
                report.fixed_content = fixed_content
        
        return report
    
    def _auto_fix(self, content: str) -> Tuple[str, List[str]]:
        """执行自动修复"""
        content, fixes1 = self.auto_fixer.fix_naming_conventions(content)
        content, fixes2 = self.auto_fixer.fix_import_order(content)
        return content, fixes1 + fixes2
    
    def middleware(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        中间件接口 - 供 Opencode 调用
        
        :param input_data: {"content": "...", "type": "json/python/auto", "path": "..."}
        :return: {"status": "pass/fixed/error/blocked", "content": "...", "report": {...}}
        """
        content = input_data.get("content", "")
        content_type = input_data.get("type", "auto")
        base_path = input_data.get("path", None)
        
        report = self.inspect(content, content_type, base_path)
        summary = report.get_summary()
        
        # 将字节流转换为字符串（用于返回）
        content_to_return = content
        if isinstance(content, bytes):
            content_to_return = content.decode('utf-8', errors='replace')
        if isinstance(report.fixed_content, bytes):
            report.fixed_content = report.fixed_content.decode('utf-8', errors='replace')
        
        # L0 层阻断
        if summary["l0_blocked"]:
            return {
                "status": "blocked",
                "content": content_to_return,
                "report": json.loads(report.to_json()),
                "message": "L0 层编码错误，拒绝进入后续校验"
            }
        # 其他错误
        elif summary["has_errors"]:
            return {
                "status": "error",
                "content": content_to_return,
                "report": json.loads(report.to_json())
            }
        # 已修复
        elif summary["has_fixes"]:
            return {
                "status": "fixed",
                "content": report.fixed_content or content_to_return,
                "report": json.loads(report.to_json())
            }
        # 通过
        else:
            return {
                "status": "pass",
                "content": content_to_return,
                "report": json.loads(report.to_json())
            }

# 全局治理者实例
governor = Governor()

# CLI 入口
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Governance Layer - AC 架构治理者")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # inspect 命令
    inspect_parser = subparsers.add_parser("inspect", help="审查内容")
    inspect_parser.add_argument("--file", "-f", help="文件路径")
    inspect_parser.add_argument("--content", "-c", help="直接内容")
    inspect_parser.add_argument("--type", "-t", default="auto", help="内容类型")
    inspect_parser.add_argument("--path", "-p", help="项目基础路径")
    inspect_parser.add_argument("--bytes", "-b", action="store_true", help="以字节流模式读取")
    
    # middleware 命令（模拟 Opencode 调用）
    middleware_parser = subparsers.add_parser("middleware", help="中间件模式")
    middleware_parser.add_argument("--input", "-i", required=True, help="JSON 输入")
    
    args = parser.parse_args()
    
    if args.command == "inspect":
        content = ""
        if args.file:
            if args.bytes:
                # 字节流模式
                with open(args.file, 'rb') as f:
                    content = f.read()
            else:
                with open(args.file, 'r', encoding='utf-8') as f:
                    content = f.read()
        elif args.content:
            content = args.content
        
        report = governor.inspect(content, args.type, args.path)
        print(report.to_json())
    
    elif args.command == "middleware":
        try:
            input_data = json.loads(args.input)
            result = governor.middleware(input_data)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except json.JSONDecodeError as e:
            print(json.dumps({
                "status": "error",
                "error": f"Invalid input JSON: {str(e)}"
            }))

if __name__ == "__main__":
    main()
