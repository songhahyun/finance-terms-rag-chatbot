from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from .io import load_json


@dataclass
class Chunk:
    chunk_id: str
    term: str
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, item: dict[str, Any]) -> "Chunk":
        """Build a Chunk instance from one raw JSON row.
        Map source-specific field names into the normalized schema."""
        return cls(
            chunk_id=item["chunk_id"],
            term=item["용어"],
            description=item["설명"],
            metadata=item.get("metadata", {}),
        )

    def to_document(self) -> Document:
        """Convert the chunk into a LangChain document.
        Carry normalized metadata needed during retrieval and display."""
        source = self.metadata.get("source", "경제금융용어700선")
        page = self.metadata.get("page")
        content = f"{self.term}\n\n{self.description}".strip()
        return Document(
            page_content=content,
            metadata={
                "chunk_id": self.chunk_id,
                "term": self.term,
                "source": source,
                "page": page,
                "related_terms": self.metadata.get("연관검색어", "없음"),
            },
        )


def load_chunks(path: str | Path) -> list[Chunk]:
    """Load chunk records from JSON into typed Chunk objects.
    Preserve file order while normalizing each row."""
    data = load_json(path)
    return [Chunk.from_dict(item) for item in data]


def chunks_to_documents(chunks: list[Chunk]) -> list[Document]:
    """Convert a list of chunks into LangChain documents.
    Use each chunk's document serialization helper."""
    return [chunk.to_document() for chunk in chunks]
