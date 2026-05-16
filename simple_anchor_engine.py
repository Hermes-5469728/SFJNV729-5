"""
简化版锚点引擎 - 基于35条绝对真值构建
功能：冲突检测、一致性验证、回溯分析
"""

import json
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class SimpleAnchor:
    """简化的锚点数据结构"""
    def __init__(self, topic: str, verified_truth: str, source: str, tags: List[str]):
        self.topic = topic
        self.verified_truth = verified_truth
        self.source = source
        self.tags = tags
    
    def to_dict(self):
        return {
            "topic": self.topic,
            "verified_truth": self.verified_truth,
            "source": self.source,
            "tags": self.tags
        }


class ConflictDetector:
    """冲突检测器 - 检测锚点之间的冲突"""
    
    def __init__(self, anchors: List[SimpleAnchor]):
        self.anchors = anchors
    
    def _extract_key_concepts(self, text: str) -> List[str]:
        """提取文本中的关键概念"""
        # 提取中文词语和英文单词
        chinese_pattern = r'[\u4e00-\u9fa5]{2,}'
        english_pattern = r'[a-zA-Z]{2,}'
        
        chinese_concepts = re.findall(chinese_pattern, text)
        english_concepts = re.findall(english_pattern, text)
        
        return list(set(chinese_concepts + english_concepts))
    
    def _extract_numeric_claims(self, text: str) -> List[Tuple[str, str]]:
        """提取文本中的数字断言"""
        patterns = [
            r'(\d+(\.\d+)?)\s*%',  # 百分比
            r'(\d+(\.\d+)?)\s*年',  # 年份
            r'(\d+(\.\d+)?)\s*亿',  # 亿
            r'(\d+(\.\d+)?)\s*万',  # 万
            r'(\d+(\.\d+)?)\s*美元', # 美元
            r'(\d+)\s*%',           # 另一种百分比格式
        ]
        
        claims = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                claims.append((match[0], pattern))
        
        return claims
    
    def detect_conflict_between(self, anchor1: SimpleAnchor, anchor2: SimpleAnchor) -> Optional[str]:
        """检测两个锚点之间是否存在冲突"""
        # 如果主题完全相同但内容不同，可能存在冲突
        if anchor1.topic == anchor2.topic and anchor1.verified_truth != anchor2.verified_truth:
            return f"主题相同但内容不同: {anchor1.topic}"
        
        # 提取关键概念
        concepts1 = set(self._extract_key_concepts(anchor1.verified_truth))
        concepts2 = set(self._extract_key_concepts(anchor2.verified_truth))
        
        # 检查否定关系
        negation_words = {'不', '不是', '非', '没有', '从未', '错误', '不正确', '不能', '不会'}
        
        text1 = anchor1.verified_truth
        text2 = anchor2.verified_truth
        
        has_negation1 = any(word in text1 for word in negation_words)
        has_negation2 = any(word in text2 for word in negation_words)
        
        # 如果两个锚点有重叠概念但一个包含否定词，可能存在冲突
        common_concepts = concepts1 & concepts2
        if common_concepts and (has_negation1 or has_negation2):
            # 检查是否有直接矛盾
            for concept in common_concepts:
                # 检查是否一个说存在，一个说不存在
                concept_in_text1 = concept in text1
                concept_in_text2 = concept in text2
                
                if has_negation1 and concept_in_text1:
                    # 锚点1否定了这个概念
                    if has_negation2 and concept_in_text2:
                        # 两个都否定，不算冲突
                        continue
                    elif concept_in_text2 and not has_negation2:
                        # 锚点2肯定了这个概念，冲突！
                        return f"概念冲突: '{concept}' - 锚点1否定，锚点2肯定"
        
        # 检查数字断言冲突
        numeric1 = self._extract_numeric_claims(anchor1.verified_truth)
        numeric2 = self._extract_numeric_claims(anchor2.verified_truth)
        
        # 如果两个锚点都有数字断言且主题相关，检查是否矛盾
        if numeric1 and numeric2:
            # 检查是否针对同一主题有不同数字
            if self._topics_related(anchor1.topic, anchor2.topic):
                # 比较数字
                nums1 = [float(n[0]) for n in numeric1]
                nums2 = [float(n[0]) for n in numeric2]
                
                if nums1 and nums2:
                    # 检查是否有明显矛盾的数字（相差超过50%）
                    for n1 in nums1:
                        for n2 in nums2:
                            if abs(n1 - n2) / max(n1, n2) > 0.5:
                                return f"数字冲突: {anchor1.topic} vs {anchor2.topic} - {n1} vs {n2}"
        
        return None
    
    def _topics_related(self, topic1: str, topic2: str) -> bool:
        """判断两个主题是否相关"""
        keywords1 = set(self._extract_key_concepts(topic1))
        keywords2 = set(self._extract_key_concepts(topic2))
        
        # 如果有共同关键词，则认为相关
        return len(keywords1 & keywords2) > 0
    
    def find_all_conflicts(self) -> List[Dict]:
        """查找所有锚点之间的冲突"""
        conflicts = []
        n = len(self.anchors)
        
        for i in range(n):
            for j in range(i + 1, n):
                anchor1 = self.anchors[i]
                anchor2 = self.anchors[j]
                
                conflict = self.detect_conflict_between(anchor1, anchor2)
                if conflict:
                    conflicts.append({
                        "anchor1_topic": anchor1.topic,
                        "anchor2_topic": anchor2.topic,
                        "conflict_type": conflict,
                        "anchor1_source": anchor1.source,
                        "anchor2_source": anchor2.source
                    })
        
        return conflicts


class AnchorEngine:
    """简化版锚点引擎"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.anchors = self._load_anchors()
        self.detector = ConflictDetector(self.anchors)
    
    def _load_anchors(self) -> List[SimpleAnchor]:
        """加载锚点数据库"""
        anchors = []
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for item in data:
                    anchor = SimpleAnchor(
                        topic=item.get('topic', ''),
                        verified_truth=item.get('verified_truth', ''),
                        source=item.get('source', ''),
                        tags=item.get('tags', [])
                    )
                    anchors.append(anchor)
            
            print(f"✅ 成功加载 {len(anchors)} 条锚点")
        except Exception as e:
            print(f"⚠️ 加载锚点失败: {e}")
        
        return anchors
    
    def run_backward_conflict_detection(self) -> Dict:
        """执行回溯冲突检测"""
        print("\n🔍 开始回溯冲突检测...")
        
        # 查找所有冲突
        conflicts = self.detector.find_all_conflicts()
        
        # 统计信息
        stats = {
            "total_anchors": len(self.anchors),
            "total_conflicts": len(conflicts),
            "conflict_rate": len(conflicts) / max(1, len(self.anchors)),
            "checked_pairs": len(self.anchors) * (len(self.anchors) - 1) // 2,
            "timestamp": datetime.now().isoformat()
        }
        
        # 输出报告
        print("\n" + "=" * 60)
        print("    🧠 回溯冲突检测报告")
        print("=" * 60)
        print(f"锚点总数: {stats['total_anchors']}")
        print(f"检测配对: {stats['checked_pairs']}")
        print(f"冲突数量: {stats['total_conflicts']}")
        print(f"冲突率: {stats['conflict_rate']:.2%}")
        print("=" * 60)
        
        if conflicts:
            print("\n⚠️ 发现冲突:")
            for i, conflict in enumerate(conflicts, 1):
                print(f"\n{i}. 冲突类型: {conflict['conflict_type']}")
                print(f"   锚点1: {conflict['anchor1_topic']} (来源: {conflict['anchor1_source']})")
                print(f"   锚点2: {conflict['anchor2_topic']} (来源: {conflict['anchor2_source']})")
        else:
            print("\n✅ 未发现冲突 - 所有锚点一致性良好")
        
        return {
            "stats": stats,
            "conflicts": conflicts
        }
    
    def search_by_topic(self, query: str) -> List[SimpleAnchor]:
        """按主题搜索锚点"""
        results = []
        query_lower = query.lower()
        
        for anchor in self.anchors:
            if query_lower in anchor.topic.lower():
                results.append(anchor)
        
        return results
    
    def validate_text(self, text: str) -> Dict:
        """验证文本与锚点的一致性"""
        conflicts = []
        
        for anchor in self.anchors:
            # 创建临时锚点进行比对
            temp_anchor = SimpleAnchor(
                topic="待验证文本",
                verified_truth=text,
                source="user_input",
                tags=["待验证"]
            )
            
            conflict = self.detector.detect_conflict_between(anchor, temp_anchor)
            if conflict:
                conflicts.append({
                    "anchor_topic": anchor.topic,
                    "conflict_type": conflict,
                    "anchor_truth": anchor.verified_truth[:50] + "..." if len(anchor.verified_truth) > 50 else anchor.verified_truth
                })
        
        return {
            "valid": len(conflicts) == 0,
            "conflicts": conflicts,
            "checked_anchors": len(self.anchors)
        }


# 执行回溯检测
if __name__ == "__main__":
    engine = AnchorEngine("00-DataCenter/anchor_db.json")
    result = engine.run_backward_conflict_detection()
    
    # 保存检测结果
    with open("conflict_detection_report.json", 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("\n📄 报告已保存到: conflict_detection_report.json")