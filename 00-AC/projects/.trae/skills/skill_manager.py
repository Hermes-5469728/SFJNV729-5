import os
import sqlite3
import shutil

SKILLS_DIR = '.trae/skills'
DORMANT_DIR = '.trae/skills_dormant'
DB_PATH = '.trae/skills/skills.db'

def scan_skills(base_dir):
    skills = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for file in files:
            if file == 'SKILL.md':
                skill_path = os.path.join(root, file)
                skills.append(skill_path)
            elif file.endswith('.md') and 'skill' in file.lower():
                skill_path = os.path.join(root, file)
                skills.append(skill_path)
    return skills

def extract_metadata(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        metadata = {'file_path': filepath}
        
        if content.startswith('---'):
            end = content.find('---', 3)
            if end != -1:
                yaml_content = content[3:end].strip()
                for line in yaml_content.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        if key in ['name', 'description', 'triggers', 'commands']:
                            metadata[key] = value
        
        if 'name' not in metadata:
            metadata['name'] = os.path.basename(os.path.dirname(filepath))
        
        metadata['content_length'] = len(content)
        return metadata
    except Exception as e:
        print(f'Error reading {filepath}: {e}')
        return None

def init_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS skills (
            name TEXT PRIMARY KEY,
            description TEXT,
            triggers TEXT,
            commands TEXT,
            metadata TEXT,
            file_path TEXT,
            enabled INTEGER DEFAULT 1,
            source_dir TEXT,
            dormant INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def save_to_database(metadata):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO skills 
        (name, description, triggers, commands, file_path, enabled, dormant) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        metadata.get('name', 'Unknown'),
        metadata.get('description', ''),
        metadata.get('triggers', ''),
        metadata.get('commands', ''),
        metadata.get('file_path', ''),
        1,
        0
    ))
    conn.commit()
    conn.close()

def move_to_dormant(skill_path):
    rel_path = os.path.relpath(skill_path, SKILLS_DIR)
    dest_path = os.path.join(DORMANT_DIR, rel_path)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    shutil.move(skill_path, dest_path)
    return dest_path

def main():
    os.makedirs(DORMANT_DIR, exist_ok=True)
    
    high_frequency_keywords = ['diagnose', 'tdd', 'prototype', 'grill', 'refactor', 'skill', 'qa', 'improve', 'write', 'create', 'build', 'generate']
    low_frequency_keywords = ['out-of-scope', 'deprecated', 'legacy', 'old', 'example', 'test_', '_test', 'sample']
    
    all_skills = scan_skills(SKILLS_DIR)
    print('【扫描结果】共发现 {} 个技能文件'.format(len(all_skills)))
    
    skill_metadata = []
    for skill in all_skills:
        meta = extract_metadata(skill)
        if meta:
            skill_metadata.append(meta)
    
    init_database()
    
    active_skills = []
    dormant_skills = []
    
    for meta in skill_metadata:
        name = meta.get('name', '').lower()
        desc = meta.get('description', '').lower()
        
        is_high_freq = any(kw in name or kw in desc for kw in high_frequency_keywords)
        is_low_freq = any(kw in name or kw in desc for kw in low_frequency_keywords)
        
        if is_low_freq and not is_high_freq:
            dormant_skills.append(meta)
        else:
            active_skills.append(meta)
            save_to_database(meta)
    
    print('\n【高频实用技能】{} 个，已入库'.format(len(active_skills)))
    for i, meta in enumerate(active_skills[:5], 1):
        print('  {}. {}'.format(i, meta.get('name')))
    if len(active_skills) > 5:
        print('  ... 还有 {} 个'.format(len(active_skills) - 5))
    
    print('\n【闲置技能】{} 个，准备移入休眠库'.format(len(dormant_skills)))
    for meta in dormant_skills:
        print('  • {}'.format(meta.get('name')))
        move_to_dormant(meta['file_path'])
    
    print('\n✅ 自动化管理流程完成！')
    print('━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    print('扫描总数: {}'.format(len(all_skills)))
    print('成功入库: {}'.format(len(active_skills)))
    print('移入休眠库: {}'.format(len(dormant_skills)))

if __name__ == '__main__':
    main()
