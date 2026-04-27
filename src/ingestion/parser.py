from __future__ import annotations

import re
from pathlib import Path

import pymupdf
from tqdm.auto import tqdm


def parse_pdf_to_chunks(
    pdf_path: str | Path,
    *,
    header_limit: int = 80,
    footer_limit: int = 700,
    title_size_threshold: float = 11.0,
) -> list[dict]:
    """Parse the source PDF into term-description chunks.
    Detect titles, skip headers and footers, and capture related keywords."""
    doc = pymupdf.open(str(pdf_path))
    chunks: list[dict] = []
    current_chunk: dict | None = None

    for page_num in tqdm(range(len(doc)), desc="PDF 페이지 처리"):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        blocks.sort(key=lambda b: b["bbox"][1])

        for block in blocks:
            if block["type"] != 0 or "lines" not in block:
                continue

            block_y0, block_y1 = block["bbox"][1], block["bbox"][3]
            if block_y0 < header_limit or block_y1 > footer_limit:
                continue

            for line in block["lines"]:
                line_text = "".join(span["text"] for span in line["spans"]).strip()
                if not line_text:
                    continue

                sample_span = line["spans"][0]
                is_bold = "Bold" in sample_span.get("font", "")
                is_large = sample_span.get("size", 0) > title_size_threshold
                has_content = re.search(r"[가-힣a-zA-Z]", line_text) is not None
                is_title = (is_bold or is_large) and has_content and len(line_text) > 1 and "연관검색어" not in line_text

                if is_title:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = {
                        "용어": line_text,
                        "설명": "",
                        "metadata": {"source": str(pdf_path), "page": page_num + 1, "연관검색어": []},
                    }
                    continue

                if not current_chunk:
                    continue

                if "연관검색어" in line_text:
                    match = re.search(r"연관검색어\s*:\s*(.*)", line_text)
                    if match:
                        keywords = re.split(r"[,/]", match.group(1).strip())
                        current_chunk["metadata"]["연관검색어"] = [k.strip() for k in keywords if k.strip()]
                elif re.search(r"[가-힣a-zA-Z0-9]", line_text):
                    current_chunk["설명"] += f"{line_text} "

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
