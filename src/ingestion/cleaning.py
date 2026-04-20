from __future__ import annotations

import re
from collections import Counter
from typing import Iterable


SYMBOL_MAPPING = {
    "\ue034": "1",
    "\ue035": "2",
    "\ue036": "3",
    "\ue037": "4",
    "\ue038": "5",
    "\ue039": "6",
    "\ue03a": "7",
    "\ue03b": "8",
    "\ue03c": "9",
    "\ue03d": "0",
    "\ue042": "%",
    "\ue044": "(",
    "\ue045": ")",
    "\ue04b": "{",
    "\ue04c": "}",
    "\ue047": "=",
    "\ue054": "/",
    "\ue048": "+",
    "\ue049": "[",
    "\ue04a": "]",
    "\ue04d": "-",
    "\ue04e": "*",
    "\ue053": ".",
    "\ue046": "-",
    "\ue0ed": "i",
    "\ue0f8": "t",
    "\ue0f6": "r",
    "\ue043": "*",
    "\ue0fd": "y",
    "\ue0ac": "π",
}
TRANS_TABLE = str.maketrans(SYMBOL_MAPPING)


def drop_head_tail(chunks: list[dict], *, head: int = 5, tail: int = 1) -> list[dict]:
    if len(chunks) <= head + tail:
        return chunks
    return chunks[head : len(chunks) - tail]


def remove_terms(chunks: list[dict], terms: Iterable[str]) -> list[dict]:
    blacklist = set(terms)
    return [chunk for chunk in chunks if chunk["용어"] not in blacklist]


def find_duplicated_terms(chunks: list[dict]) -> list[str]:
    counts = Counter(chunk["용어"] for chunk in chunks)
    return [term for term, count in counts.items() if count > 1]


def _space_with_kiwi(text: str) -> str:
    try:
        from kiwipiepy import Kiwi  # noqa: PLC0415
    except ImportError:
        return text
    kiwi = Kiwi(model_type="largest")
    return kiwi.space_tolerance(text, threshold=2.0)


def preprocess_chunk(chunk: dict, *, use_kiwi: bool = True) -> dict:
    text = chunk.get("설명", "")
    if not text:
        return chunk

    text = text.translate(TRANS_TABLE)
    text = re.sub(r"(?<![.!?])\n(?!\n)", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if use_kiwi:
        try:
            text = _space_with_kiwi(text)
        except Exception:
            pass

    return {**chunk, "설명": text}


def add_chunk_ids(chunks: list[dict], *, prefix: str = "econ") -> list[dict]:
    output = []
    for i, chunk in enumerate(chunks, start=1):
        chunk = dict(chunk)
        chunk["chunk_id"] = f"{prefix}_{i:04d}"
        md = dict(chunk.get("metadata", {}))
        if not md.get("연관검색어"):
            md["연관검색어"] = "없음"
        chunk["metadata"] = md
        output.append(chunk)
    return output

