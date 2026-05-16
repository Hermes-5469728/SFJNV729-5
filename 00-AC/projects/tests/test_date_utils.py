"""Unit Tests for src/utils/date_utils.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.date_utils import extract_dates, extract_unique_dates


def test_iso_format():
    text = "2023-01-01"
    assert extract_dates(text) == ["2023-01-01"]


def test_slash_format():
    text = "2023/01/01"
    assert extract_dates(text) == ["2023/01/01"]


def test_cn_format():
    text = "2023年1月1日"
    assert extract_dates(text) == ["2023年1月1日"]


def test_mixed_formats():
    text = "2023-01-01 2023/01/01 2023年1月1日"
    result = extract_dates(text)
    assert len(result) == 3
    assert "2023-01-01" in result
    assert "2023/01/01" in result
    assert "2023年1月1日" in result


def test_unique_dates():
    text = "2023-01-01 2023-01-01"
    result = extract_unique_dates(text)
    assert len(result) == 1


if __name__ == "__main__":
    test_iso_format()
    test_slash_format()
    test_cn_format()
    test_mixed_formats()
    test_unique_dates()
    print("All tests passed!")
