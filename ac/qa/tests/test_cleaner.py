from ac.qa.pipeline.cleaner import (
    strip_html,
    normalize_unicode,
    collapse_whitespace,
    clean,
    is_valid_length,
    strip_ad_tracking,
)
from ac.qa.tests.fixtures import SAMPLE_DIRTY_HTML, PIPELINE_EXPECTATIONS


def test_strip_html():
    result = strip_html(PIPELINE_EXPECTATIONS["strip_html"]["input"])
    expected = PIPELINE_EXPECTATIONS["strip_html"]["expected"]
    assert result == expected, f"Expected {expected!r}, got {result!r}"


def test_strip_html_entities():
    result = strip_html("a &amp; b &lt; c")
    assert "&amp;" not in result
    assert "&lt;" not in result


def test_normalize_unicode():
    result = normalize_unicode(PIPELINE_EXPECTATIONS["normalize_unicode"]["input"])
    expected = PIPELINE_EXPECTATIONS["normalize_unicode"]["expected"]
    assert result == expected, f"Expected {expected!r}, got {result!r}"


def test_collapse_whitespace():
    result = collapse_whitespace(PIPELINE_EXPECTATIONS["collapse_whitespace"]["input"])
    expected = PIPELINE_EXPECTATIONS["collapse_whitespace"]["expected"]
    assert result == expected, f"Expected {expected!r}, got {result!r}"


def test_strip_ad_tracking():
    samples = [
        "本文来自微信公众号，了解更多请联系微信 abc",
        "广告推广请联系电话 13800138000",
        "点击阅读原文查看详情",
        "这是一篇正常文章。",
    ]
    results = [strip_ad_tracking(s) for s in samples]
    assert all(len(r) <= len(s) for r, s in zip(results, samples))


def test_clean_integration():
    result = clean(SAMPLE_DIRTY_HTML)
    assert "script" not in result
    assert "<" not in result or ">" not in result
    assert len(result) > 0


def test_clean_empty():
    assert clean("") == ""
    assert clean("   ") == ""


def test_is_valid_length():
    assert is_valid_length("正常长度的文本内容适合测试") is True
    assert is_valid_length("x" * 10) is True
    assert is_valid_length("") is False
    assert is_valid_length("短") is False
    long_text = "x" * 20000
    assert is_valid_length(long_text) is False


def test_clean_preserves_content():
    text = "这是一段<p>正常</p>的文本。"
    result = clean(text)
    assert "正常" in result
    assert "文本" in result
