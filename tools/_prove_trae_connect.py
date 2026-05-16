import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 读 Trae prompt
fp = r'{PROJECT_ROOT}\00-AC\projects\.trae\skills\chinese-prompts\字节跳动（ByteDance）\Trae.ai\Builder Prompt.txt'
content = open(fp, encoding='utf-8').read()[:2000]

# 1. 调度匹配
sys.path.insert(0, r'{USER_HOME}')
from ac.core import dispatch
result = dispatch('Trae AI编程助手系统提示词处理')
print('1. AC dispatch 匹配结果:')
print('   status: ' + str(result.get('status')))
for m in result.get('matched', []):
    print('   - ' + m.get('name', '?') + ' (P' + str(m.get('priority', '?')) + ')')
print()

# 2. L5 标注
from ac.core import annotate
labeled = annotate(content[:200], source_chain=['Trae prompt', 'AC dispatch'])
print('2. AC L5 标注:')
lines = labeled.split(chr(10))
for line in lines[:4]:
    print('   ' + line)
print()

# 3. governance pipeline 检查
from ac.governance import pipeline
gov_result = pipeline(content[:500], {'command': 'annotate'})
print('3. AC Governance: passed=' + str(gov_result.get('passed')))
for c in gov_result.get('checks', [])[:3]:
    print('   [' + c.get('checker', '?') + '] passed=' + str(c.get('passed', '?')))
print()
print('证明: Trae prompt -> AC dispatch -> AC governance 链路已通')
