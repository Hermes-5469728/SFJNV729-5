import json

with open('00-DataCenter/anchor_db.json', 'r', encoding='utf-8') as f:
    anchors = json.load(f)

print('可用锚点主题:')
for i, anchor in enumerate(anchors[:10], 1):
    print(f'{i}. {anchor["topic"]}')
print(f'... 共 {len(anchors)} 条锚点')

# 查找图灵测试和AGI相关锚点
print('\n查找AGI相关锚点:')
for anchor in anchors:
    if 'AGI' in anchor['topic']:
        print(f"主题: {anchor['topic']}")
        print(f"真值: {anchor['verified_truth'][:100]}...")
        print()