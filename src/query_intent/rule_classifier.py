from __future__ import annotations

from pathlib import Path
from typing import Any

from src.query_intent.constants import (
    CAPABILITY_ANSWER,
    DEFAULT_CLARIFICATION_ANSWER,
    GREETING_ANSWER,
    NEEDS_WEB_FALLBACK_ANSWER,
    UNSUPPORTED_DOMAIN_ANSWER,
    _CAPABILITY_PATTERNS,
    _CONCEPTUAL_QUERY_PATTERNS,
    _CURRENT_INFO_PATTERNS,
    _GREETING_PATTERNS,
    _MARKET_INFO_PATTERNS,
    _UNSUPPORTED_PATTERNS,
)
from src.query_intent.dictionary import FinanceTermDictionary
from src.query_intent.normalization import _allows_short_substring_match, normalize_term
from src.query_intent.types import ClassifierMethod, QueryIntent, QueryIntentResult


# ---------------------------------------------------------------------------
# Rule-based intent classifier
# ---------------------------------------------------------------------------


class RuleBasedQueryClassifier:
    """Classify queries with deterministic finance-term and pattern matching."""

    def __init__(self, intent_dictionary_path: str | Path, kiwi_dictionary_path: str | Path | None = None) -> None:
        """Initialize dictionary lookup and the Kiwi tokenizer user dictionary."""

        intent_path = Path(intent_dictionary_path)
        tokenizer_dictionary_path = kiwi_dictionary_path
        if tokenizer_dictionary_path is None and intent_path.suffix.casefold() != ".json":
            tokenizer_dictionary_path = intent_path
        self.dictionary = FinanceTermDictionary.load(intent_dictionary_path)
        self._kiwi = self._build_kiwi(tokenizer_dictionary_path)

    @staticmethod
    def _build_kiwi(dictionary_path: str | Path | None) -> Any:
        """Build a Kiwi tokenizer and load the finance user dictionary if supported."""

        try:
            from kiwipiepy import Kiwi  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError("kiwipiepy is required for rule-based query classification.") from exc

        kiwi = Kiwi()
        load_user_dictionary = getattr(kiwi, "load_user_dictionary", None)
        if dictionary_path is not None and callable(load_user_dictionary):
            load_user_dictionary(str(dictionary_path))
        return kiwi

    def classify(self, query: str) -> QueryIntentResult:
        """Classify a query using current-info patterns, finance terms, and simple rules."""

        normalized_query = normalize_term(query)
        if self._has_current_info_signal(normalized_query):
            matched_terms = self._match_finance_terms(query)
            return QueryIntentResult(
                intent=QueryIntent.NEEDS_WEB,
                confidence=1.0,
                reason="matched_current_information_signal",
                matched_terms=matched_terms,
                classifier_method=ClassifierMethod.RULE,
                fixed_answer=NEEDS_WEB_FALLBACK_ANSWER,
            )

        simple_result = self._classify_simple(normalized_query)
        if simple_result is not None:
            return simple_result

        matched_terms = self._match_finance_terms(query)
        if matched_terms:
            return QueryIntentResult(
                intent=QueryIntent.NEEDS_RAG,
                confidence=1.0,
                reason="matched_finance_terms",
                matched_terms=matched_terms,
                classifier_method=ClassifierMethod.RULE,
            )

        return QueryIntentResult(
            intent=QueryIntent.CLARIFY,
            confidence=1.0,
            reason="rule_no_match",
            classifier_method=ClassifierMethod.RULE,
            fixed_answer=DEFAULT_CLARIFICATION_ANSWER,
        )

    def _match_finance_terms(self, query: str) -> list[str]:
        """Return unique finance terms matched by substring or tokenizer output."""

        substring_matches = self._match_finance_terms_by_substring(query)
        token_matches = self._match_finance_terms_by_tokens(query)
        return self._merge_finance_term_matches(substring_matches, token_matches)

    def _match_finance_terms_by_substring(self, query: str) -> list[str]:
        """Find finance terms using normalized substring matching with short-term guards."""

        normalized_query = normalize_term(query)
        if not normalized_query:
            return []

        matches: list[str] = []
        seen: set[str] = set()
        for normalized_term, terms in self.dictionary.normalized_to_terms.items():
            if len(normalized_term) < 3 and not _allows_short_substring_match(normalized_term):
                continue
            if normalized_term not in normalized_query:
                continue
            for term in terms:
                if term not in seen:
                    seen.add(term)
                    matches.append(term)
        return matches

    def _match_finance_terms_by_tokens(self, query: str) -> list[str]:
        """Find finance terms by exact normalized match against Kiwi token forms."""

        return self.dictionary.find_token_matches(self._token_forms(query))

    def _merge_finance_term_matches(
        self,
        substring_matches: list[str],
        token_matches: list[str],
    ) -> list[str]:
        """Merge finance-term matches and drop shorter terms contained in longer terms."""

        matches: list[str] = []
        seen: set[str] = set()
        for term in [*substring_matches, *token_matches]:
            if term not in seen:
                seen.add(term)
                matches.append(term)

        normalized_matches = [(term, normalize_term(term)) for term in matches]
        filtered: list[str] = []
        for term, normalized_term in normalized_matches:
            if any(
                normalized_term != other_normalized
                and normalized_term in other_normalized
                and len(normalized_term) < len(other_normalized)
                for _, other_normalized in normalized_matches
            ):
                continue
            filtered.append(term)
        return filtered

    def _token_forms(self, query: str) -> list[str]:
        """Tokenize a query with Kiwi and return token surface forms."""

        try:
            return [token.form for token in self._kiwi.tokenize(query)]
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def _has_current_info_signal(normalized_query: str) -> bool:
        """Return whether the query asks for market or time-sensitive information."""

        has_current_word = any(normalize_term(pattern) in normalized_query for pattern in _CURRENT_INFO_PATTERNS)
        has_market_word = any(normalize_term(pattern) in normalized_query for pattern in _MARKET_INFO_PATTERNS)
        has_conceptual_word = any(
            normalize_term(pattern) in normalized_query for pattern in _CONCEPTUAL_QUERY_PATTERNS
        )
        return (has_market_word and not has_conceptual_word) or (
            has_current_word and any(word in normalized_query for word in ("금리", "환율", "주가"))
        )

    @staticmethod
    def _classify_simple(normalized_query: str) -> QueryIntentResult | None:
        """Classify greetings, capability questions, and unsupported-domain queries."""

        if any(normalize_term(pattern) in normalized_query for pattern in _GREETING_PATTERNS):
            return QueryIntentResult(
                intent=QueryIntent.SIMPLE,
                confidence=1.0,
                reason="matched_greeting",
                classifier_method=ClassifierMethod.RULE,
                fixed_answer=GREETING_ANSWER,
            )
        if any(normalize_term(pattern) in normalized_query for pattern in _CAPABILITY_PATTERNS):
            return QueryIntentResult(
                intent=QueryIntent.SIMPLE,
                confidence=1.0,
                reason="matched_chatbot_capability",
                classifier_method=ClassifierMethod.RULE,
                fixed_answer=CAPABILITY_ANSWER,
            )
        if any(normalize_term(pattern) in normalized_query for pattern in _UNSUPPORTED_PATTERNS):
            return QueryIntentResult(
                intent=QueryIntent.SIMPLE,
                confidence=1.0,
                reason="unsupported_domain_fixed_answer",
                classifier_method=ClassifierMethod.RULE,
                fixed_answer=UNSUPPORTED_DOMAIN_ANSWER,
            )
        return None
