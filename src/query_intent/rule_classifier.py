from __future__ import annotations

from pathlib import Path

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
from src.query_intent.normalization import normalize_term
from src.query_intent.types import ClassifierMethod, QueryIntent, QueryIntentResult


# ---------------------------------------------------------------------------
# Rule-based intent classifier
# ---------------------------------------------------------------------------


class RuleBasedQueryClassifier:
    """Classify queries with deterministic finance-term and pattern matching."""

    def __init__(self, intent_dictionary_path: str | Path) -> None:
        """Initialize lookup from the strict finance intent dictionary."""

        intent_path = Path(intent_dictionary_path)
        if intent_path.suffix.casefold() != ".json":
            raise ValueError("RuleBasedQueryClassifier requires a JSON intent dictionary.")
        self.dictionary = FinanceTermDictionary.load(intent_path)

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
        """Return unique finance terms matched by normalized dictionary lookup."""

        return self._filter_longest_finance_term_matches(self._match_finance_terms_by_substring(query))

    def _match_finance_terms_by_substring(self, query: str) -> list[str]:
        """Find finance terms using normalized substring matching with short-term guards."""

        normalized_query = normalize_term(query)
        if not normalized_query:
            return []

        matches: list[str] = []
        seen: set[str] = set()
        for normalized_term, terms in self.dictionary.normalized_to_terms.items():
            if self._requires_ascii_boundary(normalized_term):
                if not self._contains_with_ascii_boundary(normalized_query, normalized_term):
                    continue
            elif normalized_term not in normalized_query:
                continue
            for term in terms:
                if term not in seen:
                    seen.add(term)
                    matches.append(term)
        return matches

    @staticmethod
    def _requires_ascii_boundary(normalized_term: str) -> bool:
        """Return whether a normalized term needs ASCII neighbor checks."""

        return len(normalized_term) <= 3 and normalized_term.isascii() and normalized_term.isalnum()

    @staticmethod
    def _contains_with_ascii_boundary(normalized_query: str, normalized_term: str) -> bool:
        """Find a short ASCII term only when adjacent chars are not ASCII alnum."""

        start = normalized_query.find(normalized_term)
        while start != -1:
            end = start + len(normalized_term)
            left = normalized_query[start - 1] if start > 0 else ""
            right = normalized_query[end] if end < len(normalized_query) else ""
            left_ok = not left or not (left.isascii() and left.isalnum())
            right_ok = not right or not (right.isascii() and right.isalnum())
            if left_ok and right_ok:
                return True
            start = normalized_query.find(normalized_term, start + 1)
        return False

    def _filter_longest_finance_term_matches(self, matches: list[str]) -> list[str]:
        """Drop shorter finance terms contained in longer matched terms."""

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

