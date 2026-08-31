from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Term normalization
# ---------------------------------------------------------------------------


_NORMALIZE_PATTERN = re.compile(r"[\s\-_./()（）·･ㆍ]+")


def normalize_term(value: str) -> str:
    """Normalize query and dictionary terms for cheap exact containment checks."""
    return _NORMALIZE_PATTERN.sub("", value).casefold()
