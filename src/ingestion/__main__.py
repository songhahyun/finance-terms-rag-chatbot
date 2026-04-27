from __future__ import annotations

import argparse

from src.common.config import get_settings
from src.ingestion.pipeline import run_ingestion


def main() -> None:
    """Parse CLI arguments and run the ingestion pipeline.
    Convert the source PDF into cleaned chunk JSON output."""
    settings = get_settings()
    parser = argparse.ArgumentParser(description="PDF를 파싱하여 청크 JSON 생성")
    parser.add_argument("--pdf-path", default=str(settings.default_pdf_path))
    parser.add_argument("--output", default=str(settings.default_chunk_json_path))
    parser.add_argument("--no-kiwi", action="store_true")
    parser.add_argument("--remove-term", action="append", default=["ABC"])
    args = parser.parse_args()

    chunks = run_ingestion(
        pdf_path=args.pdf_path,
        output_json_path=args.output,
        remove_noise_terms=args.remove_term,
        use_kiwi=not args.no_kiwi,
    )
    print(f"완료: {len(chunks)}개 chunk -> {args.output}")


if __name__ == "__main__":
    main()
