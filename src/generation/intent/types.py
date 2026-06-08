from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


# ---------------------------------------------------------------------------
# Public result types
# ---------------------------------------------------------------------------


class QueryIntent(StrEnum):
    """Routing destinations supported by the query intent classifier."""

    SIMPLE = "simple"
    NEEDS_RAG = "needs_rag"
    NEEDS_WEB = "needs_web"
    CLARIFY = "clarify"


class ClassifierMethod(StrEnum):
    """Classifier sources used to produce a query intent decision."""

    RULE = "rule"
    LLM = "llm"
    MERGED = "merged"


@dataclass(frozen=True)
class QueryIntentResult:
    """Structured output returned by intent classifiers."""

    intent: QueryIntent
    confidence: float
    reason: str
    matched_terms: list[str] = field(default_factory=list)
    classifier_method: ClassifierMethod = ClassifierMethod.RULE
    fixed_answer: str | None = None

    def routing_metadata(self) -> dict[str, object]:
        """Return serializable routing metadata for traces and API responses."""

        return {
            "intent": self.intent.value,
            "routing_reason": self.reason,
            "matched_terms": list(self.matched_terms),
            "classifier": {
                "method": self.classifier_method.value,
                "confidence": self.confidence,
            },
        }
