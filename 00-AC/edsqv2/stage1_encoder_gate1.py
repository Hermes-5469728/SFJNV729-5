"""
E/D/S/Q Architecture v2.0 - Stage 1: Enhanced E Layer + Gate1
"""

import json
import hashlib
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass


# --- 1. 输入分类与结构 ---

class InputCategory(Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"
    MEDICAL = "medical"
    CHAT = "chat"
    INVALID = "invalid"
    DUPLICATE = "duplicate"


@dataclass
class StructuredInput:
    original_text: str
    category: InputCategory
    confidence: float
    keywords: List[str]
    structured: Optional[Dict[str, Any]] = None
    cached: bool = False
    cache_id: Optional[str] = None


class InputClassifier:
    """输入分类器 - 阶段 1 核心组件"""
    
    def __init__(self):
        self.medical_keywords = ["症状", "诊断", "治疗", "药物", "患者", "医生", "医学", "医院", "处方", "健康"]
        self.simple_keywords = ["查询", "搜索", "查找", "获取", "查看", "列表"]
        self.complex_keywords = ["分步", "步骤", "规划", "设计", "构建", "创建", "开发", "实现"]
        self.invalid_keywords = ["违法", "违规", "攻击", "破解", "病毒", "黑客", "犯罪", "诈骗"]
    
    def _compute_text_hash(self, text: str) -> str:
        """计算文本哈希 - 用于去重"""
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]
    
    def classify(self, text: str) -> StructuredInput:
        """分类输入并结构化"""
        text = text.strip()
        
        # 1. 检查无效输入（乱码、无意义字符串）
        if len(text) < 2 or self._is_invalid(text):
            return StructuredInput(
                original_text=text,
                category=InputCategory.INVALID,
                confidence=1.0,
                keywords=[],
                structured={"reason": "invalid_input"}
            )
        
        # 2. 提取关键词
        keywords = self._extract_keywords(text)
        
        # 3. 判断医疗类
        medical_score = sum(1 for kw in self.medical_keywords if kw in text.lower())
        if medical_score > 0:
            return StructuredInput(
                original_text=text,
                category=InputCategory.MEDICAL,
                confidence=min(1.0, medical_score / 2),
                keywords=keywords,
                structured={
                    "type": "medical_query",
                    "score": medical_score
                }
            )
        
        # 4. 判断复杂类
        complex_score = sum(1 for kw in self.complex_keywords if kw in text.lower())
        if complex_score > 0 or self._has_step_like(text):
            return StructuredInput(
                original_text=text,
                category=InputCategory.COMPLEX,
                confidence=min(1.0, (complex_score + 1) / 3),
                keywords=keywords,
                structured={
                    "type": "complex_query",
                    "score": complex_score,
                    "requires_sequencing": True
                }
            )
        
        # 5. 判断简单类
        simple_score = sum(1 for kw in self.simple_keywords if kw in text.lower())
        if simple_score > 0 or len(text.split()) < 20:
            return StructuredInput(
                original_text=text,
                category=InputCategory.SIMPLE,
                confidence=0.7,
                keywords=keywords,
                structured={
                    "type": "simple_query",
                    "score": simple_score
                }
            )
        
        # 6. 默认闲聊
        return StructuredInput(
            original_text=text,
            category=InputCategory.CHAT,
            confidence=0.5,
            keywords=keywords,
            structured={
                "type": "chat_query"
            }
        )
    
    def _is_invalid(self, text: str) -> bool:
        """检查是否为无效输入"""
        text_lower = text.lower()
        if any(kw in text_lower for kw in self.invalid_keywords):
            return True
        if re.match(r'^[\W\d_]+$', text):
            return True
        return False
    
    def _extract_keywords(self, text: str) -> List[str]:
        """简单关键词提取"""
        words = re.split(r'\W+', text.lower())
        stop_words = {"的", "是", "在", "有", "和", "了", "我", "你", "他", "这", "那", "个", "一", "上", "下"}
        return [w for w in words if w and w not in stop_words][:10]
    
    def _has_step_like(self, text: str) -> bool:
        """检查是否有步骤类关键词"""
        return any(pat in text for pat in [
            "1.", "2.", "3.", "第一步", "第二步", "第三步",
            "1)", "2)", "3)", "①", "②", "③"
        ])


# --- 2. 缓存层 ---

@dataclass
class CacheEntry:
    id: str
    text_hash: str
    input_text: str
    output_text: str
    created_at: str
    hits: int


class InputCache:
    """输入缓存层 - 去重 + 快速返回"""
    
    def __init__(self, ttl_minutes: int = 30):
        self.cache: Dict[str, CacheEntry] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def _compute_hash(self, text: str) -> str:
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]
    
    def get(self, text: str) -> Optional[CacheEntry]:
        """获取缓存"""
        text_hash = self._compute_hash(text)
        if text_hash not in self.cache:
            return None
        
        entry = self.cache[text_hash]
        
        # 检查 TTL
        created = datetime.fromisoformat(entry.created_at)
        if datetime.now() - created > self.ttl:
            del self.cache[text_hash]
            return None
        
        entry.hits += 1
        return entry
    
    def put(self, input_text: str, output_text: str) -> CacheEntry:
        """放入缓存"""
        text_hash = self._compute_hash(input_text)
        entry = CacheEntry(
            id=f"cache_{text_hash}",
            text_hash=text_hash,
            input_text=input_text,
            output_text=output_text,
            created_at=datetime.now().isoformat(),
            hits=0
        )
        self.cache[text_hash] = entry
        return entry
    
    def cleanup(self):
        """清理过期缓存"""
        now = datetime.now()
        to_delete = []
        for key, entry in self.cache.items():
            created = datetime.fromisoformat(entry.created_at)
            if now - created > self.ttl:
                to_delete.append(key)
        for key in to_delete:
            del self.cache[key]
        return len(to_delete)


# --- 3. Gate1: 输入筛选 ---

@dataclass
class CheckResult:
    passed: bool
    message: str
    check_name: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class Gate1Result:
    allowed: bool
    reason: str
    structured_input: StructuredInput
    cache_hit: bool
    checks: List[CheckResult]


class Gate1InputFilter:
    """Gate1 - 输入筛选网关"""
    
    def __init__(self):
        self.classifier = InputClassifier()
        self.cache = InputCache()
    
    def check(self, input_text: str) -> Gate1Result:
        """执行完整检查链"""
        checks: List[CheckResult] = []
        
        # 检查1: 基本验证（长度、乱码）
        check1 = self._check_basic(input_text)
        checks.append(check1)
        if not check1.passed:
            return Gate1Result(
                allowed=False,
                reason=check1.message,
                structured_input=self.classifier.classify(input_text),
                cache_hit=False,
                checks=checks
            )
        
        # 检查2: 缓存命中
        check2 = self._check_cache(input_text)
        checks.append(check2)
        if check2.passed:
            return Gate1Result(
                allowed=True,
                reason="cache_hit",
                structured_input=self.classifier.classify(input_text),
                cache_hit=True,
                checks=checks
            )
        
        # 检查3: 服务范围检查
        check3 = self._check_service_scope(input_text)
        checks.append(check3)
        
        # 分类输入
        structured = self.classifier.classify(input_text)
        
        return Gate1Result(
            allowed=structured.category != InputCategory.INVALID,
            reason="passed" if structured.category != InputCategory.INVALID else "invalid_input",
            structured_input=structured,
            cache_hit=False,
            checks=checks
        )
    
    def _check_basic(self, text: str) -> CheckResult:
        """基本验证检查"""
        if len(text.strip()) < 2:
            return CheckResult(passed=False, message="输入太短", check_name="basic_length")
        if re.match(r'^[\W\d_]+$', text):
            return CheckResult(passed=False, message="输入为无效字符", check_name="basic_characters")
        return CheckResult(passed=True, message="通过", check_name="basic")
    
    def _check_cache(self, text: str) -> CheckResult:
        """缓存检查"""
        entry = self.cache.get(text)
        if entry:
            return CheckResult(passed=True, message=f"缓存命中 (命中次数: {entry.hits})", 
                            check_name="cache", details={"cache_id": entry.id})
        return CheckResult(passed=False, message="未命中", check_name="cache")
    
    def _check_service_scope(self, text: str) -> CheckResult:
        """服务范围检查"""
        forbidden = ["违法", "违规", "攻击", "破解", "病毒", "黑客", "犯罪", "诈骗", "制作毒品"]
        text_lower = text.lower()
        for keyword in forbidden:
            if keyword.lower() in text_lower:
                return CheckResult(passed=False, message=f"检测到敏感词: {keyword}", 
                                check_name="service_scope")
        return CheckResult(passed=True, message="通过", check_name="service_scope")


# --- 4. 增强的 E 层编码器 ---

class EncoderLayer:
    """增强的 E 层 - 编码 + 分类 + 缓存"""
    
    def __init__(self):
        self.gate1 = Gate1InputFilter()
    
    def sanitize_text(self, text: str) -> str:
        """文本清理"""
        text = text.strip()
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'[\n\r]+', '\n', text)
        return text
    
    def encode(self, text: str) -> Tuple[Gate1Result, str]:
        """完整编码流程"""
        # 1. 清理文本
        sanitized = self.sanitize_text(text)
        
        # 2. Gate1 检查
        result = self.gate1.check(sanitized)
        
        # 3. 返回
        return result, sanitized
    
    def put_cache(self, input_text: str, output_text: str):
        """放入缓存"""
        self.gate1.cache.put(input_text, output_text)
    
    def get_cache(self, input_text: str) -> Optional[CacheEntry]:
        """获取缓存"""
        return self.gate1.cache.get(input_text)

