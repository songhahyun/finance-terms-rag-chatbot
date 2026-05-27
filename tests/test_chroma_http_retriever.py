# Run from the project root: python -m pytest tests/test_chroma_http_retriever.py

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.retrieval.dense import build_dense_retriever


def test_dense_retriever_http_client_path_uses_chroma_http_client() -> None:
    retriever = object()
    store = MagicMock()
    store.as_retriever.return_value = retriever

    with (
        patch("src.retrieval.dense.create_embedding_model", return_value=object()) as create_embedding,
        patch("src.retrieval.dense.chromadb.HttpClient", return_value=object()) as http_client,
        patch("src.retrieval.dense.Chroma", return_value=store) as chroma,
    ):
        result = build_dense_retriever(
            provider="clova",
            model_name="bge-m3",
            collection_name="finance_clova",
            client_mode="http",
            chroma_host="chroma",
            chroma_port=8000,
            chroma_ssl=False,
        )

    assert result is retriever
    create_embedding.assert_called_once_with("clova", "bge-m3")
    http_client.assert_called_once_with(host="chroma", port=8000, ssl=False)
    chroma.assert_called_once()
    assert chroma.call_args.kwargs["collection_name"] == "finance_clova"
    assert "persist_directory" not in chroma.call_args.kwargs
