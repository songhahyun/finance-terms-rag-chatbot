from __future__ import annotations

import argparse

from src.common.config import get_settings
from src.evaluation.ragas_pipeline import run_ragas_evaluation


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation pipeline")
    parser.add_argument("--eval-csv", default=str(settings.default_eval_csv_path))
    parser.add_argument("--chunk-json", default=str(settings.default_chunk_json_path))
    parser.add_argument("--output-csv", default=str(settings.eval_data_dir / "ragas_eval_result.csv"))
    parser.add_argument("--output-summary-csv", default=str(settings.eval_data_dir / "ragas_eval_summary.csv"))
    parser.add_argument("--retrieval-mode", choices=["dense", "bm25", "hybrid"], default="hybrid")
    parser.add_argument("--dense-provider", choices=["openai", "clova", "local"], default="clova")
    parser.add_argument("--dense-model-name", default="bge-m3")
    parser.add_argument("--dense-collection-name", default="docs_clova")
    parser.add_argument("--dense-persist-directory", default=None)
    parser.add_argument("--ollama-model", default=settings.ollama_model)
    parser.add_argument("--ollama-base-url", default=settings.ollama_base_url)
    parser.add_argument("--ollama-timeout", type=int, default=settings.ollama_timeout)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--judge-model", default="gpt-4o-mini")
    parser.add_argument("--judge-embedding-model", default="text-embedding-3-small")
    args = parser.parse_args()

    _, summary = run_ragas_evaluation(
        eval_csv_path=args.eval_csv,
        chunk_json_path=args.chunk_json,
        output_csv_path=args.output_csv,
        output_summary_path=args.output_summary_csv,
        retrieval_mode=args.retrieval_mode,
        ollama_model=args.ollama_model,
        ollama_base_url=args.ollama_base_url,
        ollama_timeout=args.ollama_timeout,
        dense_provider=args.dense_provider,
        dense_model_name=args.dense_model_name,
        dense_collection_name=args.dense_collection_name,
        dense_persist_directory=args.dense_persist_directory,
        k=args.k,
        judge_model=args.judge_model,
        judge_embedding_model=args.judge_embedding_model,
    )
    print("RAGAS summary")
    for key, value in summary.items():
        print(f"- {key}: {value:.4f}")
    print(f"detail saved: {args.output_csv}")
    print(f"summary saved: {args.output_summary_csv}")


if __name__ == "__main__":
    main()
