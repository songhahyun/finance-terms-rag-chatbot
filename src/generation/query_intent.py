from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class QueryIntent(StrEnum):
    SIMPLE = "simple"
    NEEDS_RAG = "needs_rag"
    NEEDS_WEB = "needs_web"
    CLARIFY = "clarify"


class ClassifierMethod(StrEnum):
    RULE = "rule"
    LLM = "llm"
    MERGED = "merged"


@dataclass(frozen=True)
class QueryIntentResult:
    intent: QueryIntent
    confidence: float
    reason: str
    matched_terms: list[str] = field(default_factory=list)
    classifier_method: ClassifierMethod = ClassifierMethod.RULE
    fixed_answer: str | None = None

    def routing_metadata(self) -> dict[str, object]:
        return {
            "intent": self.intent.value,
            "routing_reason": self.reason,
            "matched_terms": list(self.matched_terms),
            "classifier": {
                "method": self.classifier_method.value,
                "confidence": self.confidence,
            },
        }


_NORMALIZE_PATTERN = re.compile(r"[\s\-_./]+")


def normalize_term(value: str) -> str:
    """Normalize query and dictionary terms for cheap exact containment checks."""
    return _NORMALIZE_PATTERN.sub("", value).casefold()


@dataclass(frozen=True)
class FinanceTermDictionary:
    terms: tuple[str, ...]
    normalized_to_terms: dict[str, tuple[str, ...]]

    @classmethod
    def load(cls, path: str | Path) -> FinanceTermDictionary:
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
