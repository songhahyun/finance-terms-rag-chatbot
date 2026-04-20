from __future__ import annotations

import argparse

from src.common.config import get_settings
from src.embedding.pipeline import EmbeddingTarget, run_embedding


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="JSON chunk를 벡터스토어에 임베딩")
    parser.add_argument("--chunk-json", default=str(settings.default_chunk_json_path))
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument(
        "--provider",
        choices=["openai", "clova", "local", "all"],
        default="all",
    )
    args = parser.parse_args()

    mapping = {
        "openai": EmbeddingTarget(
            provider="openai",
            model_name="text-embedding-3-small",
            collection_name="docs_openai",
            persist_directory=settings.chroma_openai_dir,
            sleep_sec=0.5,
        ),
        "clova": EmbeddingTarget(
            provider="clova",
            model_name="bge-m3",
            collection_name="docs_clova",
            persist_directory=settings.chroma_clova_dir,
            sleep_sec=2.0,
        ),
        "local": EmbeddingTarget(
            provider="local",
            model_name="BAAI/bge-m3",
            collection_name="docs_local",
            persist_directory=settings.chroma_local_dir,
            sleep_sec=0.0,
        ),
    }

    targets = list(mapping.values()) if args.provider == "all" else [mapping[args.provider]]
    run_embedding(args.chunk_json, targets, batch_size=args.batch_size)
    print("완료: 벡터스토어 생성")


if __name__ == "__main__":
    main()

