from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.query_intent.normalization import normalize_term


# ---------------------------------------------------------------------------
# Finance term dictionary lookup
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FinanceTermDictionary:
    """In-memory lookup table for finance terms and their normalized forms."""

    terms: tuple[str, ...]
    normalized_to_terms: dict[str, tuple[str, ...]]
    normalized_alias_to_terms: dict[str, tuple[str, ...]]

    @classmethod
    def load(cls, path: str | Path) -> FinanceTermDictionary:
        """Load JSON intent terms or a legacy TSV dictionary into lookup structures."""

        dictionary_path = Path(path)
        if dictionary_path.suffix.casefold() == ".json":
            return cls._load_json(dictionary_path)
        return cls._load_tsv(dictionary_path)

    @classmethod
    def _load_json(cls, path: Path) -> FinanceTermDictionary:
        """Load canonical finance terms and aliases from the JSON intent dictionary."""

        try:
            records = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid finance intent dictionary JSON in {path}: {exc}") from exc
        if not isinstance(records, list):
            raise ValueError(f"Finance intent dictionary JSON must be a list of records: {path}")

        term_order: list[str] = []
        normalized: dict[str, list[str]] = {}
        seen_terms: set[str] = set()

        for index, record in enumerate(records):
            term, aliases = cls._validate_json_record(record, index, path)
            if term in seen_terms:
                continue
            seen_terms.add(term)
            term_order.append(term)
            cls._add_lookup_entry(normalized, term, term)
            seen_aliases: set[str] = set()
            for alias in aliases:
                if alias == term or alias in seen_aliases:
                    continue
                seen_aliases.add(alias)
                cls._add_lookup_entry(normalized, alias, term)

        return cls(
            terms=tuple(term_order),
            normalized_to_terms={key: tuple(value) for key, value in normalized.items()},
            normalized_alias_to_terms={key: tuple(value) for key, value in normalized.items()},
        )

    @classmethod
    def _load_tsv(cls, path: Path) -> FinanceTermDictionary:
        """Load a legacy TSV user dictionary into normalized term lookup structures."""

        term_order: list[str] = []
        normalized: dict[str, list[str]] = {}
        seen_terms: set[str] = set()

        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            term = line.split("\t", 1)[0].strip()
            if not term or term in seen_terms:
                continue
            seen_terms.add(term)
            term_order.append(term)
            cls._add_lookup_entry(normalized, term, term)

        return cls(
            terms=tuple(term_order),
            normalized_to_terms={key: tuple(value) for key, value in normalized.items()},
            normalized_alias_to_terms={key: tuple(value) for key, value in normalized.items()},
        )

    @staticmethod
    def _validate_json_record(record: Any, index: int, path: Path) -> tuple[str, list[str]]:
        """Validate one JSON dictionary record and return its term and aliases."""

        location = f"{path} record {index}"
        if not isinstance(record, dict):
            raise ValueError(f"Invalid finance intent dictionary record at {location}: expected object")
        term = record.get("term")
        if not isinstance(term, str) or not term.strip():
            raise ValueError(f"Invalid finance intent dictionary record at {location}: term must be a non-empty string")
        aliases = record.get("aliases", [])
        if aliases is None:
            aliases = []
        if not isinstance(aliases, list):
            raise ValueError(f"Invalid finance intent dictionary record at {location}: aliases must be a list")
        clean_aliases: list[str] = []
        for alias_index, alias in enumerate(aliases):
            if not isinstance(alias, str):
                raise ValueError(
                    "Invalid finance intent dictionary record at "
                    f"{location}: aliases[{alias_index}] must be a string"
                )
            stripped_alias = alias.strip()
            if stripped_alias:
                clean_aliases.append(stripped_alias)
        return term.strip(), clean_aliases

    @staticmethod
    def _add_lookup_entry(normalized: dict[str, list[str]], raw_key: str, canonical_term: str) -> None:
        """Add one normalized lookup entry while preserving deterministic order."""

        normalized_key = normalize_term(raw_key)
        if not normalized_key:
            return
        terms = normalized.setdefault(normalized_key, [])
        if canonical_term not in terms:
            terms.append(canonical_term)

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
