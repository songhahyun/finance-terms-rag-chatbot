from __future__ import annotations


def build_context(docs: list) -> str:
    """Convert retrieved documents into a single prompt context block.
    Preserve chunk metadata so the generator can cite grounded evidence."""
    parts = []
    for i, doc in enumerate(docs, start=1):
        chunk_id = doc.metadata.get("chunk_id", f"unknown_{i}")
        source = doc.metadata.get("source", "unknown_source")
        content = doc.page_content.strip()
        parts.append(f"[문서 {i}] chunk_id={chunk_id}, source={source}\n{content}")
    return "\n\n".join(parts)
