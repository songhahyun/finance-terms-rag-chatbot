from __future__ import annotations

from src.generation.intent.constants import (
    CAPABILITY_ANSWER,
    DEFAULT_CLARIFICATION_ANSWER,
    GREETING_ANSWER,
    NEEDS_WEB_FALLBACK_ANSWER,
    UNSUPPORTED_DOMAIN_ANSWER,
)
from src.generation.intent.normalization import normalize_term
from src.generation.intent.types import ClassifierMethod, QueryIntent, QueryIntentResult

__all__ = [
    "CAPABILITY_ANSWER",
    "ClassifierMethod",
    "DEFAULT_CLARIFICATION_ANSWER",
    "GREETING_ANSWER",
    "NEEDS_WEB_FALLBACK_ANSWER",
    "QueryIntent",
    "QueryIntentResult",
    "UNSUPPORTED_DOMAIN_ANSWER",
    "normalize_term",
]
