from ac.qa.pipeline.quality_filter import is_quality_text


def test_quality_filter_passthrough_on_no_model():
    ok, ppl = is_quality_text("any text")
    assert ok is True
    if ppl is not None:
        assert isinstance(ppl, float)


def test_quality_filter_empty_string():
    ok, ppl = is_quality_text("")
    assert ok is True
    if ppl is not None:
        assert isinstance(ppl, float)


def test_quality_filter_meaningful_text():
    ok, ppl = is_quality_text(
        "机器学习是人工智能的一个子领域，它使计算机能够从数据中学习和改进。"
    )
    assert ok is True
    if ppl is not None:
        assert isinstance(ppl, float)
        assert ppl < 500
