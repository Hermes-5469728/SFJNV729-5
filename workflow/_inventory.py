import os, sys
sys.stdout.reconfigure(encoding='utf-8')

root = r'{PROJECT_ROOT}'
exts = {'.py','.md','.txt','.json','.toml','.yaml','.yml','.db','.html','.css','.js','.exe','.png','.zip'}
skip = {'.git','.obsidian','__pycache__','.trae','.pytest_cache'}

results = {}
max_depth = 15

for dirpath, dirnames, filenames in os.walk(root):
    depth = dirpath.replace(root, '').count(os.sep)
    if depth > max_depth:
        dirnames[:] = []
        continue
    dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith('_dc_') and d != '.RecoveryCenter']
    
    rel_dir = os.path.relpath(dirpath, root)
    for f in filenames:
        fp = os.path.join(dirpath, f)
        ext = os.path.splitext(f)[1].lower()
        if ext not in exts and f not in ('AGENTS.md','anchor_db.json'):
            continue
        try:
            sz = os.path.getsize(fp)
        except:
            continue
        rel = os.path.join(rel_dir, f) if rel_dir != '.' else f
        src = 'root'
        if '00-AC' + os.sep + 'docs' + os.sep + 'references' in rel:
            src = 'docs_references'
        elif '00-AC' + os.sep + 'docs' in rel:
            src = 'docs'
        elif '00-AC' + os.sep + 'DataCenter' in rel:
            src = 'DataCenter'
        elif '00-AC' + os.sep + 'projects' in rel:
            src = 'projects'
        elif '00-AC' in rel:
            src = '00-AC'
        elif 'workflow' in rel:
            src = 'workflow'
        elif 'governance' in rel:
            src = 'governance'
        elif 'schemas' in rel:
            src = 'schemas'
        elif 'qa' in rel:
            src = 'qa'
        results.setdefault(src, []).append((rel, sz, ext))

# site/
sr = r'{USER_HOME}\.AgentHub\site'
if os.path.exists(sr):
    for dirpath, dirnames, filenames in os.walk(sr):
        dirnames[:] = [d for d in dirnames if d != '.git']
        for f in filenames:
            fp = os.path.join(dirpath, f)
            ext = os.path.splitext(f)[1].lower()
            if ext not in exts:
                continue
            sz = os.path.getsize(fp)
            rel = os.path.relpath(fp, sr)
            results.setdefault('site', []).append((rel, sz, ext))

# desktop/hermes
h = r'{USER_HOME}\Desktop\hermes'
if os.path.exists(h):
    for dirpath, dirnames, filenames in os.walk(h):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            ext = os.path.splitext(f)[1].lower()
            if ext not in exts and ext not in ('.exe','.zip','.png','.html'):
                continue
            sz = os.path.getsize(fp)
            rel = os.path.relpath(fp, h)
            results.setdefault('desktop_hermes_v19.4', []).append((rel, sz, ext))

# 新建文件夹
n = r'{USER_HOME}\Desktop\新建文件夹'
if os.path.exists(n):
    for f in os.listdir(n):
        fp = os.path.join(n, f)
        if os.path.isfile(fp):
            ext = os.path.splitext(f)[1].lower()
            if ext not in exts:
                continue
            sz = os.path.getsize(fp)
            results.setdefault('desktop_v19.0', []).append((f, sz, ext))

for s in sorted(results):
    files = sorted(results[s], key=lambda x: x[0])
    total = sum(f[1] for f in files)
    print(f'=== {s} ({len(files)} files, {total:,} bytes) ===')
    for f in files:
        if f[1] > 1024*1024:
            sz = f'{f[1]/1024/1024:.1f}MB'
        elif f[1] > 1024:
            sz = f'{f[1]/1024:.1f}KB'
        else:
            sz = f'{f[1]}B'
        print(f'  {f[0]:70s} {sz:>8s}')
    print()

# summary
print('='*80)
print(f'{"SOURCE":30s} {"COUNT":>6s} {"SIZE":>10s}')
print('-'*46)
grand_total_files = 0
grand_total_bytes = 0
for s in sorted(results):
    files = results[s]
    total = sum(f[1] for f in files)
    grand_total_files += len(files)
    grand_total_bytes += total
    print(f'{s:30s} {len(files):6d} {total:>10,}')
print('-'*46)
print(f'{"TOTAL":30s} {grand_total_files:6d} {grand_total_bytes:>10,}')
print(f'{"(excl. .trae/.git/pycache/dc_)":30s}')
