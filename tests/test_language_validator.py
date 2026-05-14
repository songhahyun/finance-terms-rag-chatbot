# Run from the project root: python -m pytest tests/test_language_validator.py

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.generation.language_validator import needs_regeneration, validate_answer_language


def test_korean_only_answer_passes() -> None:
    result = validate_answer_language("기준금리는 중앙은행이 금융기관과 거래할 때 기준이 되는 금리입니다.")

    assert result["is_valid"] is True
    assert result["detected_issues"] == []


def test_korean_answer_with_allowed_financial_abbreviations_passes() -> None:
    text = "ETF는 여러 자산을 묶어 거래소에서 주식처럼 거래할 수 있는 금융상품이며 CD, CP, GDP도 공식 약어입니다."

    result = validate_answer_language(text)

    assert result["is_valid"] is True


def test_answer_with_japanese_hiragana_or_katakana_fails() -> None:
    result = validate_answer_language("これは日本語の文章です。")

    assert result["is_valid"] is False
    assert needs_regeneration("これは日本語の文章です。") is True
    assert "contains_japanese_hiragana" in result["detected_issues"]


def test_answer_with_long_chinese_text_fails() -> None:
    result = validate_answer_language("基準利率是中央銀行設定的政策利率。")

    assert result["is_valid"] is False
    assert "contains_long_cjk_ideograph_sequence" in result["detected_issues"]


def test_answer_with_japanese_kanji_and_hiragana_fails() -> None:
    result = validate_answer_language("基準金利とは、中央銀行が金融政策のために設定する金利です。")

    assert result["is_valid"] is False
    assert "contains_japanese_hiragana" in result["detected_issues"]


def test_single_isolated_hanja_does_not_automatically_fail() -> None:
    result = validate_answer_language("금(金)은 화폐나 안전자산을 설명할 때 쓰이는 표현입니다.")

    assert result["is_valid"] is True


def test_empty_answer_fails() -> None:
    result = validate_answer_language("   ")

    assert result["is_valid"] is False
    assert result["detected_issues"] == ["empty_answer"]
