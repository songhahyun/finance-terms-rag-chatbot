from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Term normalization
# ---------------------------------------------------------------------------


_NORMALIZE_PATTERN = re.compile(r"[\s\-_./()（）·･ㆍ]+")
_ASCII_ALNUM_PATTERN = re.compile(r"[a-z0-9]")


def normalize_term(value: str) -> str:
    """Normalize query and dictionary terms for cheap exact containment checks."""
    return _NORMALIZE_PATTERN.sub("", value).casefold()


def _allows_short_substring_match(normalized_term: str) -> bool:
    """Return whether a normalized term can be matched as a short substring."""

    return bool(_ASCII_ALNUM_PATTERN.search(normalized_term))

