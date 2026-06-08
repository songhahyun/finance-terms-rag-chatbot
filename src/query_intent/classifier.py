from __future__ import annotations

from src.generation.intent.llm_classifier import OpenAILLMIntentClassifier
from src.generation.intent.rule_classifier import RuleBasedQueryClassifier
from src.generation.intent.types import QueryIntent, QueryIntentResult


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
