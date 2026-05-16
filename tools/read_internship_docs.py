import zipfile, xml.etree.ElementTree as ET, sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

folder = r'{USER_HOME}\Desktop\备份\26年实习学生用表'
files = [f for f in os.listdir(folder) if f.endswith('.docx')]
files.sort()

for fname in files:
    path = os.path.join(folder, fname)
    z = zipfile.ZipFile(path)
    xml_content = z.read('word/document.xml')
    root = ET.fromstring(xml_content)
    texts = []
    for t in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
        if t.text:
            texts.append(t.text)
    full = '\n'.join(texts)
    print(f'=== {fname} ({len(full)} chars) ===')
    print(full[:500])
    print('...')
    print()
