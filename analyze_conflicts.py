"""
冲突分析报告生成器
"""

import json
from datetime import datetime


def analyze_conflicts():
    # 加载检测报告
    with open('conflict_detection_report.json', 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    # 加载锚点数据库
    with open('00-DataCenter/anchor_db.json', 'r', encoding='utf-8') as f:
        anchors = json.load(f)
    
    conflicts = report['conflicts']
    stats = report['stats']
    
    # 分析冲突模式
    conflict_sources = {}
    topic_conflicts = {}
    
    for conflict in conflicts:
        source1 = conflict['anchor1_source']
        source2 = conflict['anchor2_source']
        key = tuple(sorted([source1, source2]))
        
        if key not in conflict_sources:
            conflict_sources[key] = 0
        conflict_sources[key] += 1
        
        topic1 = conflict['anchor1_topic']
        topic2 = conflict['anchor2_topic']
        if topic1 not in topic_conflicts:
            topic_conflicts[topic1] = []
        if topic2 not in topic_conflicts:
            topic_conflicts[topic2] = []
        topic_conflicts[topic1].append(topic2)
        topic_conflicts[topic2].append(topic1)
    
    # 生成报告
    report_text = f"""
# 🧠 回溯冲突检测完整报告

## 一、检测概览

| 指标 | 值 |
|------|------|
| 锚点总数 | {stats['total_anchors']} |
| 检测配对数 | {stats['checked_pairs']} |
| 发现冲突数 | {stats['total_conflicts']} |
| 冲突率 | {stats['conflict_rate']:.2%} |
| 检测时间 | {stats['timestamp']} |

## 二、冲突来源分析

| 来源组合 | 冲突数量 |
|----------|----------|
"""
    
    for (source1, source2), count in conflict_sources.items():
        report_text += f"| {source1} vs {source2} | {count} |\n"
    
    report_text += """
## 三、高频冲突主题

| 主题 | 冲突次数 |
|------|----------|
"""
    
    for topic, others in topic_conflicts.items():
        report_text += f"| {topic[:30]}... | {len(set(others))} |\n"
    
    report_text += """
## 四、详细冲突列表

---

"""
    
    for i, conflict in enumerate(conflicts, 1):
        # 查找锚点内容
        anchor1_content = ""
        anchor2_content = ""
        
        for anchor in anchors:
            if anchor['topic'] == conflict['anchor1_topic']:
                anchor1_content = anchor['verified_truth']
            if anchor['topic'] == conflict['anchor2_topic']:
                anchor2_content = anchor['verified_truth']
        
        report_text += f"""### 冲突 #{i}

**冲突类型**: {conflict['conflict_type']}

**锚点1**: {conflict['anchor1_topic']}
- 来源: {conflict['anchor1_source']}
- 内容预览: {anchor1_content[:150]}...

**锚点2**: {conflict['anchor2_topic']}
- 来源: {conflict['anchor2_source']}
- 内容预览: {anchor2_content[:150]}...

---

"""
    
    report_text += f"""
## 五、分析结论

### 🔍 初步判断

**冲突率 {stats['conflict_rate']:.2%}** 表明：

1. **假阳性可能性**: 当前检测算法基于关键词匹配和否定词检测，可能存在误报
2. **真冲突可能性**: 不同来源的分析可能存在真实观点差异
3. **需要人工复核**: 建议对检测到的冲突进行人工审查确认

### 📋 建议行动

1. ✅ 人工审查所有11个冲突
2. ✅ 确认哪些是真冲突，哪些是假阳性
3. ✅ 更新冲突检测算法以降低误报率
4. ✅ 对真冲突进行内容修正或标记

---

*报告生成时间: {datetime.now().isoformat()}*
"""
    
    return report_text


if __name__ == "__main__":
    report = analyze_conflicts()
    
    # 保存报告
    with open('conflict_analysis_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("📄 冲突分析报告已保存到: conflict_analysis_report.md")
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("    冲突检测摘要")
    print("=" * 60)
    with open('conflict_detection_report.json', 'r', encoding='utf-8') as f:
        stats = json.load(f)['stats']
    print(f"锚点总数: {stats['total_anchors']}")
    print(f"检测配对: {stats['checked_pairs']}")
    print(f"冲突数量: {stats['total_conflicts']}")
    print(f"冲突率: {stats['conflict_rate']:.2%}")
    print("=" * 60)
    print("\n详细报告已生成，请查看 conflict_analysis_report.md")