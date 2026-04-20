from __future__ import annotations

import argparse

from src.common.config import get_settings
from src.evaluation.pipeline import run_evaluation


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="RAG 평가 실행")
    parser.add_argument("--eval-csv", default=str(settings.default_eval_csv_path))
    parser.add_argument("--chunk-json", default=str(settings.default_chunk_json_path))
    parser.add_argument("--output-csv", default=str(settings.eval_data_dir / "eval_result.csv"))
    parser.add_argument("--retrieval-mode", choices=["dense", "bm25", "hybrid"], default="hybrid")
    parser.add_argument("--dense-provider", choices=["openai", "clova", "local"], default="clova")
    parser.add_argument("--dense-model-name", default="bge-m3")
    parser.add_argument("--dense-collection-name", default="docs_clova")
    parser.add_argument("--dense-persist-directory", default=None)
    parser.add_argument("--ollama-model", default=settings.ollama_model)
    parser.add_argument("--ollama-base-url", default=settings.ollama_base_url)
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    df = run_evaluation(
        eval_csv_path=args.eval_csv,
        chunk_json_path=args.chunk_json,
        output_csv_path=args.output_csv,
        retrieval_mode=args.retrieval_mode,
        ollama_model=args.ollama_model,
        ollama_base_url=args.ollama_base_url,
        dense_provider=args.dense_provider,
        dense_model_name=args.dense_model_name,
        dense_collection_name=args.dense_collection_name,
        dense_persist_directory=args.dense_persist_directory,
        k=args.k,
    )
    print(df[["hit", "recall", "bert_score_f1"]].mean(numeric_only=True).to_string())
    print(f"완료: {args.output_csv}")


if __name__ == "__main__":
    main()

