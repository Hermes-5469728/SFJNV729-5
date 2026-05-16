"""数据初始化脚本 · 容器启动时自动执行 · 造测试数据"""
import os
import sys
import json
from datetime import datetime, date

# ─── 此脚本由 docker-entrypoint-initdb.d 自动调用 ───
# 仅当 postgres 容器首次启动时执行一次

SQL = [
    # ──────── 核心表 ────────
    """
    CREATE TABLE IF NOT EXISTS core_users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(64) UNIQUE NOT NULL,
        password_hash VARCHAR(128) NOT NULL,
        role VARCHAR(32) NOT NULL DEFAULT 'resident',
        created_at TIMESTAMP DEFAULT NOW()
    )
    """,
    # ──────── 医疗模块表 (med_ 前缀) ────────
    """
    CREATE TABLE IF NOT EXISTS med_drugs (
        id SERIAL PRIMARY KEY,
        name VARCHAR(128) NOT NULL,
        class_name VARCHAR(64),
        aliases TEXT,
        guideline TEXT,
        verified_date DATE,
        created_at TIMESTAMP DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS med_interactions (
        id SERIAL PRIMARY KEY,
        drug_a VARCHAR(128) NOT NULL,
        drug_b VARCHAR(128) NOT NULL,
        severity VARCHAR(32) NOT NULL,
        mechanism TEXT,
        recommendation TEXT,
        source VARCHAR(256),
        verified_date DATE,
        created_at TIMESTAMP DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS med_guidelines (
        id SERIAL PRIMARY KEY,
        condition_name VARCHAR(256) NOT NULL,
        source VARCHAR(256),
        key_point TEXT NOT NULL,
        evidence_level VARCHAR(8),
        guideline_date DATE,
        created_at TIMESTAMP DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS med_clinical_notes (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES core_users(id),
        note_type VARCHAR(32),
        content TEXT,
        entities JSONB,
        created_at TIMESTAMP DEFAULT NOW()
    )
    """,
    # ──────── 内容模块表 (cnt_ 前缀) ────────
    """
    CREATE TABLE IF NOT EXISTS cnt_creative_assets (
        id SERIAL PRIMARY KEY,
        title VARCHAR(256) NOT NULL,
        category VARCHAR(64) NOT NULL,
        tags VARCHAR(512),
        content TEXT NOT NULL,
        language VARCHAR(16) DEFAULT 'zh',
        notes TEXT,
        metadata JSONB,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cnt_references (
        id SERIAL PRIMARY KEY,
        title VARCHAR(256) NOT NULL,
        ref_type VARCHAR(64) NOT NULL,
        tags VARCHAR(512),
        content TEXT NOT NULL,
        source VARCHAR(256),
        language VARCHAR(16) DEFAULT 'zh',
        notes TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """,
]

SEED_DATA = [
    # core_users
    """
    INSERT INTO core_users (username, password_hash, role) VALUES
    ('admin', 'sha256$placeholder', 'attending'),
    ('student', 'sha256$placeholder', 'student'),
    ('resident', 'sha256$placeholder', 'resident'),
    ('attending', 'sha256$placeholder', 'attending')
    ON CONFLICT (username) DO NOTHING
    """,
    # med_drugs
    """
    INSERT INTO med_drugs (name, class_name, aliases, guideline, verified_date) VALUES
    ('warfarin', 'anticoagulant', 'coumadin,jantoven', 'ACC/AHA 2019', '2025-01-15'),
    ('aspirin', 'antiplatelet', 'asa,acetylsalicylic acid', 'AHA/ASA 2021', '2025-01-15'),
    ('metformin', 'biguanide', 'glucophage', 'ADA 2023', '2025-01-15'),
    ('lisinopril', 'ACE inhibitor', 'prinivil,zestril', 'ACC/AHA 2017', '2025-01-15'),
    ('clopidogrel', 'antiplatelet', 'plavix', 'ACC/AHA 2016', '2025-01-15'),
    ('fluconazole', 'antifungal', 'diflucan', 'IDSA 2016', '2025-01-15'),
    ('atorvastatin', 'statin', 'lipitor', 'ACC/AHA 2018', '2025-01-15')
    ON CONFLICT DO NOTHING
    """,
    # cnt_references: 广告文案配方
    """
    INSERT INTO cnt_references (title, ref_type, tags, content, source, language, notes) VALUES
    ('高级广告文案配方', '广告文案配方', '广告,文案,创意,方法论,模板,power,hallucination,desire',
     $$一条高级的广告画面，必须从你这辈子都没见过的风景开始。
卖什么不重要，但得制造一种人们想要的生活幻觉。
接着需要一个看似拥有一切的男人，记住他绝不能直视镜头，不能笑，因为讨好观众显得太廉价。
他必须像在思考人类文明的存亡一样盯着空气发呆。
这个时候如果觉得太单调，我们可以牵入一匹野马。
如果你的马儿不够听话，就用升格慢一些，再慢一些。
它跟我们要卖的东西没有任何关系，但它能强行暗示你这个品牌充满了野性与不可驾驭的权力。
气氛都到这里了，让男主莫名其妙地开始狂奔，让他试图逃离一场根本不存在的顶流晚宴。
这时候再露出你想卖的产品，可以是打火机，也可以是一辆豪华汽车。
其实卖什么根本不重要，哪怕它根本不存在。
最后让男主对着镜头说一句不明所以的话：
我从来到这个世界开始就没想过活着回去。
期待你的产品。
Looking forward to your product.$$,
     'self', 'zh',
     '配方拆解: 陌生风景→幻觉制造→不笑不直视的男人→野马慢镜头→无关联想+权力暗示→莫名其妙狂奔→露产品→不明所以金句收尾。可用于训练生成高级广告文案。')
    ON CONFLICT DO NOTHING
    """,
    # cnt_references: mattpocock/skills
    """
    INSERT INTO cnt_references (title, ref_type, tags, content, source, language, notes) VALUES
    ('mattpocock/skills · 16个TypeScript工程Skill包', '工具/技能包', 'TypeScript,React,skill,engineering,ClaudeCode,Codex,Cursor,npx',
     $$GitHub: https://github.com/mattpocock/skills (6万+星)
安装: npx skills@latest add mattpocock/skills
支持: Claude Code / Codex / Cursor
执行后交互式勾选需要的 16 个 Skill
国内备用: 镜像/打包待补充$$,
     'mattpocock', 'zh',
     '16个高质量 TypeScript/React 工程 skill，社区验证。我不具备此能力，入库用于训练和参考。')
    ON CONFLICT DO NOTHING
    """,

    # med_guidelines
    """
    INSERT INTO med_guidelines (condition_name, source, key_point, evidence_level, guideline_date) VALUES
    ('Atrial Fibrillation', 'ACC/AHA/HRS 2019', 'CHA2DS2-VASc ≥2 → anticoagulation (Class I)', 'A', '2019-03-01'),
    ('Hypertension', 'ACC/AHA 2017', 'BP target <130/80 mmHg; first-line: ACEi/ARB, CCB, thiazide', 'A', '2017-11-01'),
    ('Type 2 Diabetes', 'ADA 2023', 'First-line: metformin + lifestyle; HbA1c <7% for most adults', 'A', '2023-01-01'),
    ('Community-Acquired Pneumonia', 'IDSA/ATS 2019', 'Empiric: beta-lactam + macrolide or fluoroquinolone monotherapy', 'A', '2019-10-01')
    ON CONFLICT DO NOTHING
    """,
]


def run():
    import psycopg2
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="ac_admin",
        password="ac_platform_2026",
        dbname="ac_platform",
    )
    cur = conn.cursor()
    for stmt in SQL:
        print(f"[DDL] {stmt.strip()[:60]}...")
        cur.execute(stmt)
    for stmt in SEED_DATA:
        print(f"[SEED] {stmt.strip()[:60]}...")
        cur.execute(stmt)
    conn.commit()
    cur.close()
    conn.close()
    print("[SEED] Initialization complete.")


if __name__ == "__main__":
    run()
