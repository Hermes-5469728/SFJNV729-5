"""AC Medical Vector Store - 零依赖向量存储
迁移自: core/dads_vector.py
纯Python实现 · 无faiss依赖"""
import os, json, hashlib, math
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

class VectorStore:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent.parent / "data" / "dads_db" / "vector_store.json"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.vectors: Dict[str, dict] = self._load()

    def _load(self) -> dict:
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save(self):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self.vectors, f, ensure_ascii=False, indent=2)

    def _tokenize(self, text: str) -> List[str]:
        import re
        text = text.lower()
        chars = []
        for i, c in enumerate(text):
            if '\u4e00' <= c <= '\u9fff':
                chars.append(c)
                if i+1 < len(text): chars.append(text[i:i+2])
                if i+2 < len(text): chars.append(text[i:i+3])
        words = re.findall(r'[a-z0-9]{2,}', text)
        result = chars + words
        return list(set(result))

    def _compute_vector(self, tokens: List[str]) -> dict:
        vec = {}
        for t in tokens:
            vec[t] = vec.get(t, 0) + 1
        norm = math.sqrt(sum(v*v for v in vec.values())) or 1
        return {k: v/norm for k, v in vec.items()}

    def _cosine(self, a: dict, b: dict) -> float:
        if not a or not b: return 0.0
        dot = sum(a.get(k, 0) * b.get(k, 0) for k in set(a) | set(b))
        norm_a = math.sqrt(sum(v*v for v in a.values())) or 1
        norm_b = math.sqrt(sum(v*v for v in b.values())) or 1
        return dot / (norm_a * norm_b)

    def add(self, doc_id: str, text: str, metadata: Optional[dict] = None):
        tokens = self._tokenize(text)
        vec = self._compute_vector(tokens)
        self.vectors[doc_id] = {"vector": vec, "text": text[:500], "meta": metadata or {}}
        self._save()

    def search(self, query: str, top_k: int = 5, threshold: float = 0.1) -> List[Tuple[str, float, dict]]:
        tokens = self._tokenize(query)
        query_vec = self._compute_vector(tokens)
        scores = []
        for doc_id, entry in self.vectors.items():
            score = self._cosine(query_vec, entry["vector"])
            if score >= threshold:
                scores.append((doc_id, score, entry.get("meta", {})))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def delete(self, doc_id: str):
        if doc_id in self.vectors:
            del self.vectors[doc_id]
            self._save()

    def count(self) -> int:
        return len(self.vectors)

    def stats(self) -> dict:
        return {"total_docs": len(self.vectors), "db_path": str(self.db_path)}

def init_vector_store(data_dir: str = None) -> VectorStore:
    if data_dir is None:
        data_dir = Path(__file__).parent.parent.parent.parent / "data" / "dads_db"
    store = VectorStore(str(Path(data_dir) / "vector_store.json"))

    drugs_file = Path(data_dir) / "drugs.txt"
    if drugs_file.exists() and store.count() == 0:
        with open(drugs_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if line:
                    store.add(f"drug_{i}", line)
    return store
