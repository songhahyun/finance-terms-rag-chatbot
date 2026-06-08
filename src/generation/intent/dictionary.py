from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.generation.intent.normalization import normalize_term


# ---------------------------------------------------------------------------
# Finance term dictionary lookup
# ---------------------------------------------------------------------------


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
