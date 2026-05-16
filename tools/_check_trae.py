import os, sys, io
from datetime import datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

d = r'{PROJECT_ROOT}\00-AC\projects\.trae\skills\chinese-prompts\字节跳动（ByteDance）\Trae.ai'
for f in sorted(os.listdir(d)):
    fp = os.path.join(d, f)
    t = os.path.getmtime(fp)
    sz = os.path.getsize(fp)
    dt = datetime.fromtimestamp(t)
    print(f'{dt.strftime("%m-%d %H:%M")} {sz:>8}B  {f}')
