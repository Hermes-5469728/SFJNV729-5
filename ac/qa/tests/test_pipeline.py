from ac.qa.pipeline.cleaner import clean, is_valid_length
from ac.qa.pipeline.deduplicator import deduplicate_docs
from ac.qa.pipeline.language_filter import is_target_language
from ac.qa.tests.fixtures import SAMPLE_DIRTY_HTML, SAMPLE_DUPLICATES, SAMPLE_MIXED_LANG


def test_full_pipeline_clean_then_dedup():
    html_docs = [
        "<p>今天天气真好。</p>",
        "<div>今天天气真好。</div>",
        "<span>Python是一种编程语言。</span>",
    ]
    cleaned = [clean(d) for d in html_docs]
    assert all("<" not in c for c in cleaned)

    deduped = deduplicate_docs(cleaned)
    assert len(deduped) <= len(cleaned)


def test_full_pipeline_filter_zh_only():
    zh_docs = []
    for text in SAMPLE_MIXED_LANG:
        cleaned = clean(text)
        ok, _ = is_target_language(cleaned, target="zh")
        if ok:
            zh_docs.append(cleaned)

    assert len(zh_docs) > 0
    assert all(is_target_language(d, "zh")[0] for d in zh_docs)


def test_full_pipeline_dirty_to_clean():
    result = clean(SAMPLE_DIRTY_HTML)
    assert is_valid_length(result)
    assert "script" not in result
    assert "微信" not in result


def test_full_pipeline_dedup_then_length_check():
    valid = [d for d in SAMPLE_DUPLICATES if is_valid_length(clean(d))]
    deduped = deduplicate_docs([clean(d) for d in valid])
    assert len(deduped) <= len(valid)
