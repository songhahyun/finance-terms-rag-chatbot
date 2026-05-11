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
    eval_input_dir: Path
    eval_output_dir: Path
    chroma_openai_dir: Path
    chroma_clova_dir: Path
    chroma_local_dir: Path
    default_pdf_path: Path
    default_chunk_json_path: Path
    default_eval_csv_path: Path
    ollama_base_url: str
    ollama_model: str
    ollama_timeout: int
    ollama_temperature: float
    ollama_top_p: float
    ollama_repeat_penalty: float
    ollama_keep_alive: str
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
    eval_input_dir = data_dir / "eval" / "testset"
    eval_output_dir = data_dir / "eval" / "outputs"
    default_pdf_name = os.getenv("DEFAULT_PDF_FILENAME", "2020_경제금융용어 700선.pdf")

    return Settings(
        root_dir=root,
        raw_data_dir=raw_dir,
        processed_data_dir=processed_dir,
        eval_input_dir=eval_input_dir,
        eval_output_dir=eval_output_dir,
        chroma_openai_dir=root / "chroma_openai",
        chroma_clova_dir=root / "chroma_clova",
        chroma_local_dir=root / "chroma_local",
        default_pdf_path=raw_dir / default_pdf_name,
        default_chunk_json_path=processed_dir / "final_chunk.json",
        default_eval_csv_path=eval_input_dir / "golden_testset_v2.csv",
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct"),
        ollama_timeout=int(os.getenv("OLLAMA_TIMEOUT", "300")),
        ollama_temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.1")),
        ollama_top_p=float(os.getenv("OLLAMA_TOP_P", "0.8")),
        ollama_repeat_penalty=float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.2")),
        ollama_keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
        monitor_stage_log_path=Path(
            os.getenv("MONITOR_STAGE_LOG_PATH", str(root / "logs" / "stage_monitor.log"))
        ),
        monitor_stage3_timeout_sec=float(os.getenv("MONITOR_STAGE3_TIMEOUT_SEC", "120")),
    )
