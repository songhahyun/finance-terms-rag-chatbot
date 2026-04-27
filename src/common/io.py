from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> Any:
    """Load a JSON file from disk.
    Return the parsed Python object with UTF-8 decoding."""
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str | Path, data: Any, *, indent: int = 2) -> None:
    """Save data as JSON to disk.
    Create parent directories first and preserve Unicode characters."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
