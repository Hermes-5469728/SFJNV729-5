#!/usr/bin/env python
"""
Obsidian Bridge — opencode ↔ Obsidian Vault 语义搜索桥
======================================================
让 opencode 能检索你的 Obsidian 笔记，作为推理上下文。

用法:
    python obsidian_bridge.py rebuild          # 重建索引
    python obsidian_bridge.py search "查询"     # JSON 结果
    python obsidian_bridge.py context "查询"    # 格式化上下文（给 opencode 注入用）
    python obsidian_bridge.py status            # 索引状态

技术栈:
    TF-IDF (scikit-learn) → 零下载, 即时, 离线可用
    未来: 切换 Smart Connections 向量索引 API
"""

import argparse
import json
import os
import pickle
import re
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ── 配置 ──────────────────────────────────────────
VAULT_PATH = r"{USER_VAULT}"
INDEX_DIR = Path(__file__).resolve().parent / ".obsidian_index"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K = 8
EXCLUDE_DIRS = {".obsidian", ".git", ".trash", "node_modules", "__pycache__"}


def get_md_files() -> list[Path]:
    vault = Path(VAULT_PATH)
    if not vault.exists():
        print(f"[ERROR] Vault 不存在: {VAULT_PATH}", file=sys.stderr)
        return []
    files = []
    for f in vault.rglob("*.md"):
        parts = set(f.relative_to(vault).parts)
        if parts & EXCLUDE_DIRS:
            continue
        files.append(f)
    return sorted(files)


def chunk_markdown(content: str, filepath: Path) -> list[dict]:
    chunks = []
    lines = content.split("\n")
    current_title = filepath.stem
    current_text: list[str] = []

    for line in lines:
        heading_match = re.match(r"^(#{1,4})\s+(.+)", line)
        if heading_match:
            if current_text:
                text = "\n".join(current_text).strip()
                if len(text) > 50:
                    chunks.append({"title": current_title, "text": text, "source": str(filepath)})
            current_title = heading_match.group(2).strip()
            current_text = [line]
        else:
            current_text.append(line)

    if current_text:
        text = "\n".join(current_text).strip()
        if len(text) > 50:
            chunks.append({"title": current_title, "text": text, "source": str(filepath)})

    final_chunks = []
    for ch in chunks:
        if len(ch["text"]) <= CHUNK_SIZE:
            final_chunks.append(ch)
        else:
            start = 0
            while start < len(ch["text"]):
                end = start + CHUNK_SIZE
                sub = ch["text"][start:end]
                final_chunks.append({"title": ch["title"], "text": sub.strip(), "source": ch["source"]})
                start += CHUNK_SIZE - CHUNK_OVERLAP
                if start >= len(ch["text"]):
                    break
    return final_chunks


def build_index():
    t0 = time.time()
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[索引] 扫描 {VAULT_PATH}...", file=sys.stderr)
    files = get_md_files()
    if not files:
        print("[ERROR] 没有找到 .md 文件", file=sys.stderr)
        return

    all_chunks = []
    for fp in files:
        try:
            content = fp.read_text(encoding="utf-8")
        except Exception:
            continue
        chunks = chunk_markdown(content, fp)
        all_chunks.extend(chunks)

    texts = [c["text"] for c in all_chunks]
    metadatas = [{"title": c["title"], "source": c["source"]} for c in all_chunks]

    print(f"[索引] {len(files)} 个文件 → {len(all_chunks)} 个块, 构建 TF-IDF...", file=sys.stderr)

    vectorizer = TfidfVectorizer(
        max_features=10000,
        ngram_range=(1, 2),
        analyzer="char_wb",
        lowercase=True,
    )
    tfidf_matrix = vectorizer.fit_transform(texts)

    with open(INDEX_DIR / "vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
    with open(INDEX_DIR / "tfidf_matrix.pkl", "wb") as f:
        pickle.dump(tfidf_matrix, f)
    with open(INDEX_DIR / "metadatas.pkl", "wb") as f:
        pickle.dump(metadatas, f)
    with open(INDEX_DIR / "texts.pkl", "wb") as f:
        pickle.dump(texts, f)

    elapsed = time.time() - t0
    print(f"[索引] 完成! {len(all_chunks)} 块, {tfidf_matrix.shape[1]} 特征, 耗时 {elapsed:.1f}s", file=sys.stderr)


def _load_index():
    with open(INDEX_DIR / "vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)
    with open(INDEX_DIR / "tfidf_matrix.pkl", "rb") as f:
        matrix = pickle.load(f)
    with open(INDEX_DIR / "metadatas.pkl", "rb") as f:
        metadatas = pickle.load(f)
    with open(INDEX_DIR / "texts.pkl", "rb") as f:
        texts = pickle.load(f)
    return vectorizer, matrix, metadatas, texts


def search(query: str, top_k: int = TOP_K) -> list[dict]:
    if not (INDEX_DIR / "vectorizer.pkl").exists():
        print("[ERROR] 索引不存在，请先运行 rebuild", file=sys.stderr)
        return []

    vectorizer, matrix, metadatas, texts = _load_index()
    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, matrix).flatten()
    top_indices = np.argsort(scores)[::-1][:top_k]

    output = []
    for idx in top_indices:
        if scores[idx] > 0:
            output.append({
                "source": metadatas[idx]["source"],
                "title": metadatas[idx]["title"],
                "text": texts[idx],
                "score": round(float(scores[idx]), 4),
            })
    return output


def context(query: str, top_k: int = TOP_K) -> str:
    results = search(query, top_k)
    if not results:
        return "(未在笔记中找到相关内容)"

    lines = ["[Obsidian 笔记检索结果]", f"查询: {query}", f"匹配: {len(results)} 条", "=" * 50]
    for i, r in enumerate(results, 1):
        source_name = Path(r["source"]).stem if r["source"] else "未知"
        lines.append(f"\n## {i}. {r['title']} ({source_name})  [相关度: {r['score']}]")
        lines.append(f"来源: {r['source']}")
        lines.append(r["text"][:600])
        if len(r["text"]) > 600:
            lines.append("...(截断)")
        lines.append("-" * 40)
    return "\n".join(lines)


def show_status():
    if not (INDEX_DIR / "vectorizer.pkl").exists():
        print("索引未创建。运行: python obsidian_bridge.py rebuild")
        return
    _, matrix, metadatas, _ = _load_index()
    sources = sorted(set(m["source"] for m in metadatas))
    print(f"索引状态: 活跃")
    print(f"块总数: {matrix.shape[0]}")
    print(f"特征维度: {matrix.shape[1]}")
    print(f"覆盖文件: {len(sources)} 个")
    print(f"Vault: {VAULT_PATH}")
    for s in sources[:10]:
        print(f"  - {Path(s).name}")
    if len(sources) > 10:
        print(f"  ... 共 {len(sources)} 个文件")


def main():
    parser = argparse.ArgumentParser(description="Obsidian Bridge")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("rebuild", help="重建 TF-IDF 索引")
    p_search = sub.add_parser("search", help="语义搜索")
    p_search.add_argument("query", help="搜索查询")
    p_search.add_argument("-k", type=int, default=TOP_K, help="返回条数")
    p_ctx = sub.add_parser("context", help="生成上下文文本")
    p_ctx.add_argument("query", help="搜索查询")
    p_ctx.add_argument("-k", type=int, default=TOP_K, help="返回条数")
    sub.add_parser("status", help="索引状态")

    args = parser.parse_args()
    if args.command == "rebuild":
        build_index()
    elif args.command == "search":
        results = search(args.query, args.k)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.command == "context":
        text = context(args.query, args.k)
        print(text)
    elif args.command == "status":
        show_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
