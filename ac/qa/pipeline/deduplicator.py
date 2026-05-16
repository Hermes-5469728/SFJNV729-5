import hashlib
import struct
from typing import List, Set
from ac.qa.config import QA_CONFIG


def _sha256_int(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)


def _hash_bytes(text: str, seed: int) -> int:
    h = hashlib.sha256((str(seed) + text).encode("utf-8"))
    return int(h.hexdigest()[:16], 16)


def _shingle(text: str, k: int = 3) -> Set[str]:
    text = text.lower().strip()
    if len(text) < k:
        return {text}
    return {text[i : i + k] for i in range(len(text) - k + 1)}


def _tokenize_shingle(text: str) -> Set[str]:
    return _shingle(text, k=3)


class MinHash:
    def __init__(self, num_perm: int | None = None):
        cfg = QA_CONFIG["pipeline"]["deduplicator"]
        self.num_perm = num_perm or cfg["minhash_num_perm"]
        self.seeds = list(range(self.num_perm))
        self.signature: List[int] | None = None

    def compute(self, text: str):
        shingles = _tokenize_shingle(text)
        sig = []
        for seed in self.seeds:
            sig.append(min(_hash_bytes(s, seed) for s in shingles))
        self.signature = sig
        return sig

    def jaccard(self, other: "MinHash") -> float:
        if self.signature is None or other.signature is None:
            return 0.0
        match = sum(1 for a, b in zip(self.signature, other.signature) if a == b)
        return match / len(self.signature)


class SimHash:
    def __init__(self, bits: int | None = None):
        cfg = QA_CONFIG["pipeline"]["deduplicator"]
        self.bits = bits or cfg["simhash_fingerprint_bits"]
        self.fingerprint: int | None = None

    def compute(self, text: str) -> int:
        tokens = text.lower().split()
        v = [0] * self.bits
        for t in tokens:
            h = _sha256_int(t)
            for i in range(self.bits):
                bit = (h >> i) & 1
                v[i] += 1 if bit else -1
        fp = 0
        for i in range(self.bits):
            if v[i] > 0:
                fp |= 1 << i
        self.fingerprint = fp
        return fp

    def hamming_distance(self, other: "SimHash") -> int:
        if self.fingerprint is None or other.fingerprint is None:
            return self.bits
        return bin(self.fingerprint ^ other.fingerprint).count("1")

    def is_duplicate(self, other: "SimHash") -> bool:
        cfg = QA_CONFIG["pipeline"]["deduplicator"]
        return self.hamming_distance(other) <= cfg["simhash_hamming_threshold"]


def deduplicate_docs(docs: List[str]) -> List[str]:
    cfg = QA_CONFIG["pipeline"]["deduplicator"]
    threshold = cfg["minhash_threshold"]
    result = []
    seen_sigs: List[List[int]] = []
    for doc in docs:
        mh = MinHash()
        sig = mh.compute(doc)
        dup = False
        for seen_sig in seen_sigs:
            match = sum(1 for a, b in zip(sig, seen_sig) if a == b)
            j = match / len(sig)
            if j >= threshold:
                dup = True
                break
        if not dup:
            seen_sigs.append(sig)
            result.append(doc)
    return result
