from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    raw_data_dir: Path
    processed_data_dir: Path
    eval_data_dir: Path
    chroma_openai_dir: Path
    chroma_clova_dir: Path
    chroma_local_dir: Path
    default_pdf_path: Path
    default_chunk_json_path: Path
    default_eval_csv_path: Path
    ollama_base_url: str
    ollama_model: str


def get_settings() -> Settings:
    root = Path(__file__).resolve().parents[2]
    data_dir = root / "data"
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    eval_dir = data_dir / "eval"

    return Settings(
        root_dir=root,
        raw_data_dir=raw_dir,
        processed_data_dir=processed_dir,
        eval_data_dir=eval_dir,
        chroma_openai_dir=root / "chroma_openai",
        chroma_clova_dir=root / "chroma_clova",
        chroma_local_dir=root / "chroma_local",
        default_pdf_path=raw_dir / "2020_경제금융용어 700선_게시.pdf",
        default_chunk_json_path=processed_dir / "final_chunk.json",
        default_eval_csv_path=eval_dir / "golden_testset.csv",
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
    )

