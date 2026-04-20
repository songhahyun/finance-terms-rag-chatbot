from __future__ import annotations

import ast
from typing import Iterable


def parse_golden_ids(raw_value) -> list[str]:
    if isinstance(raw_value, list):
        return [str(v) for v in raw_value]
    if isinstance(raw_value, str):
        if raw_value.startswith("["):
            try:
                parsed = ast.literal_eval(raw_value)
                if isinstance(parsed, list):
                    return [str(v) for v in parsed]
            except (SyntaxError, ValueError):
                pass
        return [raw_value]
    return [str(raw_value)]


def hit_score(retrieved_ids: Iterable[str], golden_ids: Iterable[str]) -> int:
    return int(bool(set(retrieved_ids).intersection(set(golden_ids))))


def recall_score(retrieved_ids: Iterable[str], golden_ids: Iterable[str]) -> float:
    golden = set(golden_ids)
    if not golden:
        return 0.0
    return len(golden.intersection(set(retrieved_ids))) / len(golden)


def bertscore_f1(predictions: list[str], references: list[str], lang: str = "ko") -> list[float]:
    try:
        from bert_score import score  # noqa: PLC0415
    except ImportError:
        return [0.0 for _ in predictions]
    _, _, f1 = score(predictions, references, lang=lang, verbose=False)
    return [float(v) for v in f1]

