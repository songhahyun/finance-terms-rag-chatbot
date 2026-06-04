from __future__ import annotations

from pathlib import Path

from src.generation.query_intent import (
    ClassifierMethod,
    FinanceTermDictionary,
    QueryIntent,
    QueryIntentResult,
    normalize_term,
)


def test_query_intent_result_metadata() -> None:
    result = QueryIntentResult(
        intent=QueryIntent.NEEDS_RAG,
        confidence=1.0,
        reason="matched_finance_terms",
        matched_terms=["가산금리"],
        classifier_method=ClassifierMethod.RULE,
    )

    assert result.routing_metadata() == {
        "intent": "needs_rag",
        "routing_reason": "matched_finance_terms",
        "matched_terms": ["가산금리"],
        "classifier": {"method": "rule", "confidence": 1.0},
    }


def test_normalize_term_ignores_spacing_and_separators() -> None:
    assert normalize_term("가 산-금 리") == "가산금리"
    assert normalize_term("E T-F") == "etf"


def test_finance_dictionary_loads_terms_once_from_path(tmp_path: Path) -> None:
    path = tmp_path / "kiwi_user_dict.tsv"
    path.write_text("가산금리\tNNP\nETF\tNNP\n가산금리\tNNP\n", encoding="utf-8")

    dictionary = FinanceTermDictionary.load(path)

    assert dictionary.terms == ("가산금리", "ETF")
    assert dictionary.normalized_to_terms["가산금리"] == ("가산금리",)
    assert dictionary.normalized_to_terms["etf"] == ("ETF",)


def test_finance_dictionary_matches_spacing_insensitive_korean_term(tmp_path: Path) -> None:
    path = tmp_path / "kiwi_user_dict.tsv"
    path.write_text("가산금리\tNNP\n", encoding="utf-8")
    dictionary = FinanceTermDictionary.load(path)

    assert dictionary.find_matches("가 산 금 리란 무엇인가요?") == ["가산금리"]


def test_finance_dictionary_matches_abbreviation(tmp_path: Path) -> None:
    path = tmp_path / "kiwi_user_dict.tsv"
    path.write_text("ETF\tNNP\n", encoding="utf-8")
    dictionary = FinanceTermDictionary.load(path)

    assert dictionary.find_matches("etf 뜻 알려줘") == ["ETF"]
