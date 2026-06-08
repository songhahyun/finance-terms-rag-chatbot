from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.generation.intent.constants import (
    CAPABILITY_ANSWER,
    DEFAULT_CLARIFICATION_ANSWER,
    GREETING_ANSWER,
    NEEDS_WEB_FALLBACK_ANSWER,
    UNSUPPORTED_DOMAIN_ANSWER,
    _CAPABILITY_PATTERNS,
    _CONCEPTUAL_QUERY_PATTERNS,
    _CURRENT_INFO_PATTERNS,
    _GREETING_PATTERNS,
    _LLM_ALLOWED_INTENTS,
    _MARKET_INFO_PATTERNS,
    _UNSUPPORTED_PATTERNS,
)
from src.generation.intent.normalization import _allows_short_substring_match, normalize_term
from src.generation.intent.types import ClassifierMethod, QueryIntent, QueryIntentResult


@dataclass(frozen=True)
class FinanceTermDictionary:
    """In-memory lookup table for finance terms and their normalized forms."""

    terms: tuple[str, ...]
    normalized_to_terms: dict[str, tuple[str, ...]]

    @classmethod
    def load(cls, path: str | Path) -> FinanceTermDictionary:
        """Load a TSV user dictionary into normalized term lookup structures."""

        term_order: list[str] = []
        normalized: dict[str, list[str]] = {}
        seen_terms: set[str] = set()

        for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            term = line.split("\t", 1)[0].strip()
            if not term or term in seen_terms:
                continue
            seen_terms.add(term)
            term_order.append(term)
            normalized_key = normalize_term(term)
            if normalized_key:
                normalized.setdefault(normalized_key, []).append(term)

        return cls(
            terms=tuple(term_order),
            normalized_to_terms={key: tuple(value) for key, value in normalized.items()},
        )

    def find_matches(self, query: str) -> list[str]:
        """Find finance terms whose normalized form is contained in the query."""

        normalized_query = normalize_term(query)
        if not normalized_query:
            return []

        matches: list[str] = []
        seen: set[str] = set()
        for normalized_term, terms in self.normalized_to_terms.items():
            if normalized_term not in normalized_query:
                continue
            for term in terms:
                if term not in seen:
                    seen.add(term)
                    matches.append(term)
        return matches

    def find_token_matches(self, tokens: list[str]) -> list[str]:
        """Find finance terms that exactly match normalized tokenizer outputs."""

        matches: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            normalized_token = normalize_term(token)
            if not normalized_token:
                continue
            for term in self.normalized_to_terms.get(normalized_token, ()):
                if term not in seen:
                    seen.add(term)
                    matches.append(term)
        return matches


# ---------------------------------------------------------------------------
# Rule-based intent classifier
# ---------------------------------------------------------------------------


class RuleBasedQueryClassifier:
    """Classify queries with deterministic finance-term and pattern matching."""

    def __init__(self, dictionary_path: str | Path) -> None:
        """Initialize dictionary lookup and the Kiwi tokenizer user dictionary."""

        self.dictionary = FinanceTermDictionary.load(dictionary_path)
        self._kiwi = self._build_kiwi(dictionary_path)

    @staticmethod
    def _build_kiwi(dictionary_path: str | Path) -> Any:
        """Build a Kiwi tokenizer and load the finance user dictionary if supported."""

        try:
            from kiwipiepy import Kiwi  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError("kiwipiepy is required for rule-based query classification.") from exc

        kiwi = Kiwi()
        load_user_dictionary = getattr(kiwi, "load_user_dictionary", None)
        if callable(load_user_dictionary):
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


# ---------------------------------------------------------------------------
# Optional OpenAI LLM fallback classifier
# ---------------------------------------------------------------------------


class OpenAILLMIntentClassifier:
    """Use an OpenAI chat model to classify queries that rules cannot finalize."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4.1-mini",
        timeout: float = 10,
        confidence_threshold: float = 0.7,
        client: Any | None = None,
    ) -> None:
        """Initialize the OpenAI client or accept an injected test client."""

        self._model = model
        self._confidence_threshold = confidence_threshold
        if client is not None:
            self._client = client
            return
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when INTENT_CLASSIFIER_PROVIDER=openai.")
        try:
            from openai import OpenAI  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError("The official OpenAI SDK is required. Install the `openai` package.") from exc
        self._client = OpenAI(api_key=api_key, timeout=timeout)

    def classify(self, query: str) -> QueryIntentResult:
        """Classify a query with the configured chat model and parse its JSON output."""

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Classify Korean or English user queries for a finance-term chatbot. "
                            "Return only JSON with intent, confidence, reason. "
                            "Allowed intents: simple, needs_web, clarify."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            'Examples:\n'
                            'Q: "삼성전자 주가 알려줘"\n'
                            'A: {"intent":"needs_web","confidence":0.95,"reason":"current_stock_price"}\n'
                            'Q: "안녕?"\n'
                            'A: {"intent":"simple","confidence":0.95,"reason":"greeting"}\n'
                            'Q: "이거 알려줘"\n'
                            'A: {"intent":"clarify","confidence":0.8,"reason":"ambiguous"}\n'
                            f'Query: "{query}"'
                        ),
                    },
                ],
                temperature=0,
                max_tokens=80,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or ""
            return self._parse_response(content)
        except Exception:  # noqa: BLE001
            return QueryIntentResult(
                intent=QueryIntent.CLARIFY,
                confidence=0.0,
                reason="llm_classifier_failed",
                classifier_method=ClassifierMethod.LLM,
                fixed_answer=DEFAULT_CLARIFICATION_ANSWER,
            )

    def _parse_response(self, content: str) -> QueryIntentResult:
        """Parse and validate the LLM JSON response into a query intent result."""

        try:
            payload = json.loads(content)
            intent = QueryIntent(str(payload.get("intent", "")))
            confidence = float(payload.get("confidence", 0.0))
            reason = str(payload.get("reason", "llm_classifier"))
        except Exception:  # noqa: BLE001
            return QueryIntentResult(
                intent=QueryIntent.CLARIFY,
                confidence=0.0,
                reason="llm_classifier_failed",
                classifier_method=ClassifierMethod.LLM,
                fixed_answer=DEFAULT_CLARIFICATION_ANSWER,
            )

        if intent not in _LLM_ALLOWED_INTENTS:
            return QueryIntentResult(
                intent=QueryIntent.CLARIFY,
                confidence=0.0,
                reason="llm_classifier_failed",
                classifier_method=ClassifierMethod.LLM,
                fixed_answer=DEFAULT_CLARIFICATION_ANSWER,
            )
        if confidence < self._confidence_threshold:
            return QueryIntentResult(
                intent=QueryIntent.CLARIFY,
                confidence=confidence,
                reason="llm_classifier_low_confidence",
                classifier_method=ClassifierMethod.LLM,
                fixed_answer=DEFAULT_CLARIFICATION_ANSWER,
            )
        return QueryIntentResult(
            intent=intent,
            confidence=confidence,
            reason=reason,
            classifier_method=ClassifierMethod.LLM,
            fixed_answer=DEFAULT_CLARIFICATION_ANSWER if intent == QueryIntent.CLARIFY else None,
        )


# ---------------------------------------------------------------------------
# Hybrid classifier facade
# ---------------------------------------------------------------------------


class QueryIntentClassifier:
    """Coordinate rule and optional LLM classifiers with a small query-result cache."""

    def __init__(
        self,
        *,
        rule_classifier: RuleBasedQueryClassifier,
        llm_classifier: OpenAILLMIntentClassifier | None = None,
        cache_size: int = 256,
    ) -> None:
        """Initialize the classifier facade and bounded insertion-order cache."""

        self._rule_classifier = rule_classifier
        self._llm_classifier = llm_classifier
        self._cache_size = max(cache_size, 0)
        self._cache: dict[str, QueryIntentResult] = {}

    def classify(self, query: str) -> QueryIntentResult:
        """Classify a query, using rules first and the LLM only for unresolved cases."""

        if query in self._cache:
            return self._cache[query]
        rule_result = self._rule_classifier.classify(query)
        if self._is_rule_final(rule_result):
            return self._remember(query, rule_result)
        if self._llm_classifier is None:
            return self._remember(query, rule_result)
        return self._remember(query, self._llm_classifier.classify(query))

    def _remember(self, query: str, result: QueryIntentResult) -> QueryIntentResult:
        """Store a classification result in the bounded cache and return it."""

        if self._cache_size == 0:
            return result
        if len(self._cache) >= self._cache_size:
            oldest_key = next(iter(self._cache))
            self._cache.pop(oldest_key, None)
        self._cache[query] = result
        return result

    @staticmethod
    def _is_rule_final(result: QueryIntentResult) -> bool:
        """Return whether a rule-based result should skip the LLM fallback."""

        if result.intent in {QueryIntent.NEEDS_WEB, QueryIntent.NEEDS_RAG, QueryIntent.SIMPLE}:
            return True
        return result.reason != "rule_no_match"
