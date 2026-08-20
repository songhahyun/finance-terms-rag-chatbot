from __future__ import annotations

from pathlib import Path

import pytest

import src.query_intent as intent_package
from src.generation.query_intent import (
    CAPABILITY_ANSWER,
    ClassifierMethod,
    DEFAULT_CLARIFICATION_ANSWER,
    FinanceTermDictionary,
    GREETING_ANSWER,
    NEEDS_WEB_FALLBACK_ANSWER,
    OpenAILLMIntentClassifier,
    QueryIntentClassifier,
    QueryIntent,
    QueryIntentResult,
    RuleBasedQueryClassifier,
    UNSUPPORTED_DOMAIN_ANSWER,
    normalize_term,
)


def test_query_intent_facade_exports_same_objects_as_intent_package() -> None:
    assert CAPABILITY_ANSWER is intent_package.CAPABILITY_ANSWER
    assert ClassifierMethod is intent_package.ClassifierMethod
    assert DEFAULT_CLARIFICATION_ANSWER is intent_package.DEFAULT_CLARIFICATION_ANSWER
    assert FinanceTermDictionary is intent_package.FinanceTermDictionary
    assert GREETING_ANSWER is intent_package.GREETING_ANSWER
    assert NEEDS_WEB_FALLBACK_ANSWER is intent_package.NEEDS_WEB_FALLBACK_ANSWER
    assert OpenAILLMIntentClassifier is intent_package.OpenAILLMIntentClassifier
    assert QueryIntent is intent_package.QueryIntent
    assert QueryIntentClassifier is intent_package.QueryIntentClassifier
    assert QueryIntentResult is intent_package.QueryIntentResult
    assert RuleBasedQueryClassifier is intent_package.RuleBasedQueryClassifier
    assert UNSUPPORTED_DOMAIN_ANSWER is intent_package.UNSUPPORTED_DOMAIN_ANSWER
    assert normalize_term is intent_package.normalize_term


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


def test_finance_dictionary_loads_json_canonical_terms(tmp_path: Path) -> None:
    path = tmp_path / "finance_intent_terms.json"
    path.write_text(
        '[{"term":"가산금리","aliases":[]},{"term":"상장지수펀드(ETF)","aliases":["ETF"]}]',
        encoding="utf-8",
    )

    dictionary = FinanceTermDictionary.load(path)

    assert dictionary.terms == ("가산금리", "상장지수펀드(ETF)")
    assert dictionary.normalized_to_terms["가산금리"] == ("가산금리",)
    assert dictionary.normalized_to_terms["etf"] == ("상장지수펀드(ETF)",)


def test_finance_dictionary_json_alias_matches_return_canonical_terms(tmp_path: Path) -> None:
    path = tmp_path / "finance_intent_terms.json"
    path.write_text(
        '[{"term":"상장지수펀드(ETF)","aliases":["ETF","상장지수펀드"]}]',
        encoding="utf-8",
    )
    dictionary = FinanceTermDictionary.load(path)

    assert dictionary.find_matches("ETF 뜻 알려줘") == ["상장지수펀드(ETF)"]
    assert dictionary.find_token_matches(["상장지수펀드"]) == ["상장지수펀드(ETF)"]


def test_finance_dictionary_json_deduplicates_terms_and_aliases(tmp_path: Path) -> None:
    path = tmp_path / "finance_intent_terms.json"
    path.write_text(
        (
            "["
            '{"term":"상장지수펀드(ETF)","aliases":["ETF","ETF","상장지수펀드"]},'
            '{"term":"상장지수펀드(ETF)","aliases":["ignored"]}'
            "]"
        ),
        encoding="utf-8",
    )

    dictionary = FinanceTermDictionary.load(path)

    assert dictionary.terms == ("상장지수펀드(ETF)",)
    assert dictionary.find_matches("ETF와 상장지수펀드 차이") == ["상장지수펀드(ETF)"]


def test_finance_dictionary_json_rejects_invalid_records(tmp_path: Path) -> None:
    path = tmp_path / "finance_intent_terms.json"
    path.write_text('[{"term":"가산금리","aliases":"가산 금리"}]', encoding="utf-8")

    with pytest.raises(ValueError, match="aliases must be a list"):
        FinanceTermDictionary.load(path)


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


def test_rule_classifier_routes_finance_term_to_rag(tmp_path: Path) -> None:
    path = tmp_path / "kiwi_user_dict.tsv"
    path.write_text("가산금리\tNNP\n", encoding="utf-8")
    classifier = RuleBasedQueryClassifier(path)

    result = classifier.classify("가산금리란 무엇인가요?")

    assert result.intent == QueryIntent.NEEDS_RAG
    assert result.reason == "matched_finance_terms"
    assert result.matched_terms == ["가산금리"]


def test_rule_classifier_routes_current_finance_query_to_web(tmp_path: Path) -> None:
    path = tmp_path / "kiwi_user_dict.tsv"
    path.write_text("기준금리\tNNP\n", encoding="utf-8")
    classifier = RuleBasedQueryClassifier(path)

    result = classifier.classify("기준금리 오늘 얼마야?")

    assert result.intent == QueryIntent.NEEDS_WEB
    assert result.reason == "matched_current_information_signal"
    assert result.matched_terms == ["기준금리"]
    assert result.fixed_answer is not None


def test_rule_classifier_routes_greeting_to_simple(tmp_path: Path) -> None:
    path = tmp_path / "kiwi_user_dict.tsv"
    path.write_text("가산금리\tNNP\n", encoding="utf-8")
    classifier = RuleBasedQueryClassifier(path)

    result = classifier.classify("안녕?")

    assert result.intent == QueryIntent.SIMPLE
    assert result.reason == "matched_greeting"
    assert result.fixed_answer is not None


def test_rule_classifier_routes_unsupported_domain_to_simple_fixed_answer(tmp_path: Path) -> None:
    path = tmp_path / "kiwi_user_dict.tsv"
    path.write_text("가산금리\tNNP\n", encoding="utf-8")
    classifier = RuleBasedQueryClassifier(path)

    result = classifier.classify("파이썬 리스트 컴프리헨션 알려줘")

    assert result.intent == QueryIntent.SIMPLE
    assert result.reason == "unsupported_domain_fixed_answer"
    assert result.fixed_answer is not None


def test_rule_classifier_filters_longest_finance_term_matches(tmp_path: Path) -> None:
    path = tmp_path / "kiwi_user_dict.tsv"
    path.write_text(
        "\n".join(
            [
                "레이션\tNNG",
                "스태\tNNG",
                "스태그플레이션\tNNG",
                "인플\tNNG",
                "인플레\tNNG",
                "인플레이션\tNNG",
                "차이\tNNG",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    classifier = RuleBasedQueryClassifier(path)

    result = classifier.classify("인플레이션과 스태그플레이션의 차이점은 무엇인가요?")

    assert result.intent == QueryIntent.NEEDS_RAG
    assert set(result.matched_terms) == {"스태그플레이션", "인플레이션"}


def test_rule_classifier_programming_query_has_no_finance_false_positive(tmp_path: Path) -> None:
    path = tmp_path / "kiwi_user_dict.tsv"
    path.write_text("리스\tNNG\n리스트\tNNG\n", encoding="utf-8")
    classifier = RuleBasedQueryClassifier(path)

    result = classifier.classify("파이썬 리스트 컴프리헨션 알려줘")

    assert result.intent == QueryIntent.SIMPLE
    assert result.reason == "unsupported_domain_fixed_answer"
    assert result.matched_terms == []


def test_rule_classifier_conceptual_market_word_query_uses_rag(tmp_path: Path) -> None:
    path = tmp_path / "kiwi_user_dict.tsv"
    path.write_text("금리\tNNG\n주가\tNNG\n", encoding="utf-8")
    classifier = RuleBasedQueryClassifier(path)

    result = classifier.classify("금리와 주가의 관계는?")

    assert result.intent == QueryIntent.NEEDS_RAG
    assert set(result.matched_terms) == {"금리", "주가"}


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls = 0
        self.last_kwargs = None

    def create(self, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        return _FakeResponse(self.content)


class _FakeChat:
    def __init__(self, content: str) -> None:
        self.completions = _FakeCompletions(content)


class _FakeClient:
    def __init__(self, content: str) -> None:
        self.chat = _FakeChat(content)


def test_llm_classifier_returns_structured_result() -> None:
    client = _FakeClient('{"intent":"needs_web","confidence":0.91,"reason":"latest_news"}')
    classifier = OpenAILLMIntentClassifier(api_key="", client=client)

    result = classifier.classify("최근 환율 뉴스 알려줘")

    assert result.intent == QueryIntent.NEEDS_WEB
    assert result.confidence == 0.91
    assert result.reason == "latest_news"
    assert result.classifier_method == ClassifierMethod.LLM
    assert client.chat.completions.calls == 1
    assert client.chat.completions.last_kwargs["temperature"] == 0
    assert client.chat.completions.last_kwargs["max_tokens"] == 80


def test_llm_classifier_json_parse_failure_routes_to_clarify() -> None:
    classifier = OpenAILLMIntentClassifier(api_key="", client=_FakeClient("not json"))

    result = classifier.classify("애매한 질문")

    assert result.intent == QueryIntent.CLARIFY
    assert result.confidence == 0.0
    assert result.reason == "llm_classifier_failed"


def test_llm_classifier_low_confidence_routes_to_clarify() -> None:
    classifier = OpenAILLMIntentClassifier(
        api_key="",
        client=_FakeClient('{"intent":"simple","confidence":0.2,"reason":"weak"}'),
        confidence_threshold=0.7,
    )

    result = classifier.classify("간단한 질문?")

    assert result.intent == QueryIntent.CLARIFY
    assert result.confidence == 0.2
    assert result.reason == "llm_classifier_low_confidence"


def test_llm_classifier_disallows_rag_label() -> None:
    classifier = OpenAILLMIntentClassifier(
        api_key="",
        client=_FakeClient('{"intent":"needs_rag","confidence":0.99,"reason":"bad_label"}'),
    )

    result = classifier.classify("가산금리 알려줘")

    assert result.intent == QueryIntent.CLARIFY
    assert result.reason == "llm_classifier_failed"


class _FakeLLMClassifier:
    def __init__(self, result: QueryIntentResult) -> None:
        self.result = result
        self.calls = 0

    def classify(self, query: str) -> QueryIntentResult:
        self.calls += 1
        return self.result


class _FakeRuleClassifier:
    def __init__(self, result: QueryIntentResult) -> None:
        self.result = result
        self.calls = 0

    def classify(self, query: str) -> QueryIntentResult:
        self.calls += 1
        return self.result


def test_final_classifier_keeps_rule_rag_result_and_skips_llm(tmp_path: Path) -> None:
    path = tmp_path / "kiwi_user_dict.tsv"
    path.write_text("기준금리\tNNP\n", encoding="utf-8")
    llm = _FakeLLMClassifier(
        QueryIntentResult(intent=QueryIntent.CLARIFY, confidence=1.0, reason="unused")
    )
    classifier = QueryIntentClassifier(rule_classifier=RuleBasedQueryClassifier(path), llm_classifier=llm)

    result = classifier.classify("기준금리란 무엇인가요?")

    assert result.intent == QueryIntent.NEEDS_RAG
    assert result.matched_terms == ["기준금리"]
    assert llm.calls == 0


def test_final_classifier_prioritizes_web_over_finance_term(tmp_path: Path) -> None:
    path = tmp_path / "kiwi_user_dict.tsv"
    path.write_text("기준금리\tNNP\n", encoding="utf-8")
    classifier = QueryIntentClassifier(rule_classifier=RuleBasedQueryClassifier(path))

    result = classifier.classify("기준금리 오늘 얼마야?")

    assert result.intent == QueryIntent.NEEDS_WEB
    assert result.matched_terms == ["기준금리"]


def test_final_classifier_uses_llm_for_rule_no_match(tmp_path: Path) -> None:
    path = tmp_path / "kiwi_user_dict.tsv"
    path.write_text("기준금리\tNNP\n", encoding="utf-8")
    llm = _FakeLLMClassifier(
        QueryIntentResult(
            intent=QueryIntent.CLARIFY,
            confidence=0.8,
            reason="ambiguous",
            classifier_method=ClassifierMethod.LLM,
        )
    )
    classifier = QueryIntentClassifier(rule_classifier=RuleBasedQueryClassifier(path), llm_classifier=llm)

    result = classifier.classify("이거 알려줘")

    assert result.intent == QueryIntent.CLARIFY
    assert result.reason == "ambiguous"
    assert llm.calls == 1


def test_final_classifier_caches_repeated_queries() -> None:
    rule = _FakeRuleClassifier(
        QueryIntentResult(
            intent=QueryIntent.SIMPLE,
            confidence=1.0,
            reason="matched_greeting",
            classifier_method=ClassifierMethod.RULE,
            fixed_answer="안녕하세요.",
        )
    )
    classifier = QueryIntentClassifier(rule_classifier=rule)

    first = classifier.classify("안녕?")
    second = classifier.classify("안녕?")

    assert first is second
    assert rule.calls == 1
