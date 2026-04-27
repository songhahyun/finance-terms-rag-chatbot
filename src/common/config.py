from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


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
    ollama_small_model: str
    ollama_complex_model: str
    ollama_timeout: int
    monitor_stage_log_path: Path
    monitor_stage3_timeout_sec: float


def get_settings() -> Settings:
    """Load application settings from the project root and environment.
    Build canonical paths and runtime defaults for the whole project."""
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")

    data_dir = root / "data"
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    eval_dir = data_dir / "eval"
    default_pdf_name = os.getenv("DEFAULT_PDF_FILENAME", "2020_경제금융용어 700선.pdf")

    return Settings(
        root_dir=root,
        raw_data_dir=raw_dir,
        processed_data_dir=processed_dir,
        eval_data_dir=eval_dir,
        chroma_openai_dir=root / "chroma_openai",
        chroma_clova_dir=root / "chroma_clova",
        chroma_local_dir=root / "chroma_local",
        default_pdf_path=raw_dir / default_pdf_name,
        default_chunk_json_path=processed_dir / "final_chunk.json",
        default_eval_csv_path=eval_dir / "golden_testset.csv",
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "deepseek-r1:7b"),
        ollama_small_model=os.getenv("OLLAMA_SMALL_MODEL", "deepseek-r1:1.5b"),
        ollama_complex_model=os.getenv("OLLAMA_COMPLEX_MODEL", "llama3.2:3b"),
        ollama_timeout=int(os.getenv("OLLAMA_TIMEOUT", "300")),
        monitor_stage_log_path=Path(
            os.getenv("MONITOR_STAGE_LOG_PATH", str(root / "logs" / "stage_monitor.log"))
        ),
        monitor_stage3_timeout_sec=float(os.getenv("MONITOR_STAGE3_TIMEOUT_SEC", "120")),
    )
