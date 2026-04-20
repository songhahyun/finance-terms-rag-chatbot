from __future__ import annotations

from pathlib import Path

from tqdm.auto import tqdm

from src.common.io import save_json
from src.ingestion.cleaning import add_chunk_ids, drop_head_tail, preprocess_chunk, remove_terms
from src.ingestion.parser import parse_pdf_to_chunks


def run_ingestion(
    pdf_path: str | Path,
    output_json_path: str | Path,
    *,
    remove_noise_terms: list[str] | None = None,
    use_kiwi: bool = True,
) -> list[dict]:
    raw_chunks = parse_pdf_to_chunks(pdf_path)
    cleaned = drop_head_tail(raw_chunks, head=5, tail=1)
    if remove_noise_terms:
        cleaned = remove_terms(cleaned, remove_noise_terms)

    processed = [preprocess_chunk(chunk, use_kiwi=use_kiwi) for chunk in tqdm(cleaned, desc="텍스트 정제")]
    final_chunks = add_chunk_ids(processed)
    save_json(output_json_path, final_chunks, indent=2)
    return final_chunks

