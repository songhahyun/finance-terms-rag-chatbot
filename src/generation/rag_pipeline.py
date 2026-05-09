from __future__ import annotations

from collections.abc import Callable

from src.generation.context import build_context
from src.generation.prompts import RAG_PROMPT
from src.monitor import PipelineMonitor


class RAGPipeline:
    def __init__(
        self,
        retriever,
        generator=None,
        *,
        monitor: PipelineMonitor | None = None,
        monitor_stage3_timeout_sec: float | None = None,
    ) -> None:
        """Initialize the RAG pipeline with retrieval, generation, and monitoring pieces.
        Use a single fixed generator for every answer."""
        self.retriever = retriever
        self.generator = generator
        self.monitor = monitor
        self.monitor_stage3_timeout_sec = monitor_stage3_timeout_sec

    def _build_answer_prompt(self, query: str, context: str, language: str | None = None) -> str:
        """Construct the final generation prompt for the answer model.
        Append a language instruction when the caller specifies one."""
        prompt = RAG_PROMPT.format(context=context, question=query)
        if language == "ko":
            prompt += "\n\nRespond in Korean."
        elif language == "en":
            prompt += "\n\nRespond in English."
        return prompt

    @staticmethod
    def _generate_text(generator, prompt: str, on_chunk: Callable[[str], None] | None = None) -> str:
        """Run a prompt through the selected generator.
        Use streaming only when a chunk callback has been provided."""
        if on_chunk is None:
            return generator.generate(prompt)
        return generator.generate(prompt, stream=True, on_chunk=on_chunk)

    def answer(
        self,
        query: str,
        language: str | None = None,
        *,
        on_chunk: Callable[[str], None] | None = None,
    ) -> dict:
        """Answer a user query through the configured RAG flow.
        Return the answer text, retrieved ids, contexts, and monitoring metadata."""
        if self.generator is None:
            raise ValueError("`generator` is required.")

        trace = None
        if self.monitor is not None:
            trace = self.monitor.start_trace(
                query=query,
                metadata={"mode": "single_generator"},
            )

        if trace is not None:
            docs = trace.run_stage(
                "stage_1_retrieval",
                lambda: self.retriever.invoke(query),
                throughput_unit="docs/sec",
                throughput_fn=lambda out: len(out),
            )
        else:
            docs = self.retriever.invoke(query)

        context = build_context(docs)
        answer_prompt = self._build_answer_prompt(query, context, language=language)
        if trace is not None:
            answer = trace.run_stage(
                "stage_2_generation",
                lambda: self._generate_text(self.generator, answer_prompt, on_chunk),
                throughput_unit="chars/sec",
                throughput_fn=lambda out: len(str(out)),
                timeout_sec=self.monitor_stage3_timeout_sec,
            )
        else:
            answer = self._generate_text(self.generator, answer_prompt, on_chunk)

        result = {
            "query": query,
            "answer": answer,
            "retrieved_ids": [doc.metadata.get("chunk_id") for doc in docs],
            "contexts": docs,
        }
        if trace is not None:
            result["monitoring"] = trace.to_dict()
        return result
