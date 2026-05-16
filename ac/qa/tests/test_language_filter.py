from ac.qa.pipeline.language_filter import detect_language, is_target_language
from ac.qa.tests.fixtures import SAMPLE_MIXED_LANG


def test_detect_zh():
    lang, conf = detect_language("今天天气真好，适合出去散步。")
    assert lang == "zh"
    assert conf > 0.5


def test_detect_en():
    lang, conf = detect_language("The weather is nice today.")
    assert lang == "en"
    assert conf > 0.3


def test_detect_empty():
    lang, conf = detect_language("")
    assert lang == "unknown"
    assert conf == 0.0


def test_is_target_zh_accepts_zh():
    ok, conf = is_target_language("这是一段中文。", target="zh")
    assert ok is True
    assert conf > 0


def test_is_target_zh_rejects_en():
    ok, _ = is_target_language("This is English.", target="zh")
    assert ok is False


def test_detect_ja():
    lang, conf = detect_language("これはテストです。")
    assert lang == "ja" or lang == "zh"


def test_mixed_lang_detection():
    results = [detect_language(t)[0] for t in SAMPLE_MIXED_LANG]
    assert any(r == "zh" for r in results)
    assert any(r == "en" for r in results)
