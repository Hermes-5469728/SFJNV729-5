from ac.qa.pipeline.deduplicator import MinHash, SimHash, deduplicate_docs
from ac.qa.tests.fixtures import SAMPLE_DUPLICATES, SAMPLE_NON_DUPLICATES


def test_minhash_same_docs_high_similarity():
    text = "这是一段测试文本。"
    mh1 = MinHash(num_perm=64)
    mh2 = MinHash(num_perm=64)
    mh1.compute(text)
    mh2.compute(text)
    assert mh1.jaccard(mh2) == 1.0


def test_minhash_different_docs_low_similarity():
    mh1 = MinHash(num_perm=64)
    mh2 = MinHash(num_perm=64)
    mh1.compute("今天天气真好。")
    mh2.compute("量子计算是前沿科技。")
    j = mh1.jaccard(mh2)
    assert j < 0.5


def test_minhash_empty_signature():
    mh = MinHash()
    assert mh.jaccard(MinHash()) == 0.0


def test_simhash_same_text():
    sh1 = SimHash(bits=64)
    sh2 = SimHash(bits=64)
    sh1.compute("测试文本")
    sh2.compute("测试文本")
    assert sh1.hamming_distance(sh2) == 0


def test_simhash_near_duplicate():
    sh1 = SimHash(bits=64)
    sh2 = SimHash(bits=64)
    sh1.compute("今天天气真好，适合出去散步。")
    sh2.compute("今日天气不错，宜外出散步。")
    dist = sh1.hamming_distance(sh2)
    assert isinstance(dist, int)
    assert dist >= 0


def test_simhash_is_duplicate_threshold():
    sh = SimHash(bits=64)
    sh.compute("test")
    assert sh.is_duplicate(sh) is True


def test_deduplicate_docs_exact():
    result = deduplicate_docs(SAMPLE_DUPLICATES)
    assert len(result) < len(SAMPLE_DUPLICATES)


def test_deduplicate_docs_no_dup():
    result = deduplicate_docs(SAMPLE_NON_DUPLICATES)
    assert len(result) == len(SAMPLE_NON_DUPLICATES)


def test_deduplicate_empty():
    assert deduplicate_docs([]) == []


def test_deduplicate_single():
    assert deduplicate_docs(["唯一文档"]) == ["唯一文档"]


def test_simhash_empty_string():
    sh = SimHash()
    fp = sh.compute("")
    assert isinstance(fp, int)
