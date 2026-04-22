from __future__ import annotations

from src.generation.context import build_context
from src.generation.prompts import RAG_PROMPT


class RAGPipeline:
    def __init__(self, retriever, generator) -> None:
        self.retriever = retriever
        self.generator = generator

    def answer(self, query: str, language: str | None = None) -> dict:
        docs = self.retriever.invoke(query)
        context = build_context(docs)
        prompt = RAG_PROMPT.format(context=context, question=query)
        if language == "ko":
            prompt += "\n\nRespond in Korean."
        elif language == "en":
            prompt += "\n\nRespond in English."
        answer = self.generator.generate(prompt)
        return {
            "query": query,
            "answer": answer,
            "retrieved_ids": [doc.metadata.get("chunk_id") for doc in docs],
            "contexts": docs,
        }
