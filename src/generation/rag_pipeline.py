from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from src.generation.context import build_context
from src.generation.language_validator import validate_answer_language
from src.generation.prompts import RAG_PROMPT
from src.monitor import PipelineMonitor

logger = logging.getLogger(__name__)

STRICT_KOREAN_REGENERATION_INSTRUCTION = (
    "The previous answer contained non-Korean text. Rewrite the answer in Korean only. "
    "Do not use Simplified Chinese, Traditional Chinese, or Japanese. Use English only "
    "for official financial abbreviations or proper nouns."
)


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
    def _generate_text(
        generator,
        prompt: str,
        on_chunk: Callable[[str], None] | None = None,
        *,
        options: dict[str, float | int] | None = None,
    ) -> str:
        """Run a prompt through the selected generator.
        Use streaming only when a chunk callback has been provided."""
        if on_chunk is None:
            if options is None:
                return generator.generate(prompt)
            try:
                return generator.generate(prompt, options=options)
            except TypeError:
                logger.debug("Generator does not support per-call options; retrying without overrides.")
                return generator.generate(prompt)
        if options is None:
            return generator.generate(prompt, stream=True, on_chunk=on_chunk)
        try:
            return generator.generate(prompt, stream=True, on_chunk=on_chunk, options=options)
        except TypeError:
            logger.debug("Generator does not support per-call options; retrying without overrides.")
            return generator.generate(prompt, stream=True, on_chunk=on_chunk)

    def _generate_validated_answer_result(
        self,
        answer_prompt: str,
        *,
        on_chunk: Callable[[str], None] | None = None,
    ) -> dict:
        """Generate an answer, validate language, and return language metadata."""
        answer = self._generate_text(self.generator, answer_prompt)
        validation = validate_answer_language(answer)
        if validation["is_valid"]:
            logger.info("Answer language validation passed.")
            if on_chunk is not None:
                on_chunk(answer)
            return {
                "answer": answer,
                "language_validation": {
                    **validation,
                    "regeneration_count": 0,
                },
            }

        logger.warning(
            "Answer language validation failed: reason=%s issues=%s",
            validation["reason"],
            validation["detected_issues"],
        )
        retry_prompt = f"{answer_prompt}\n\n{STRICT_KOREAN_REGENERATION_INSTRUCTION}"
        regenerated_answer = self._generate_text(
            self.generator,
            retry_prompt,
            options={"temperature": 0.0},
        )
        retry_validation = validate_answer_language(regenerated_answer)
        if retry_validation["is_valid"]:
            logger.info("Regenerated answer language validation passed.")
        else:
            logger.warning(
                "Regenerated answer language validation failed: reason=%s issues=%s",
                retry_validation["reason"],
                retry_validation["detected_issues"],
            )
        if on_chunk is not None:
            on_chunk(regenerated_answer)
        return {
            "answer": regenerated_answer,
            "language_validation": {
                **retry_validation,
                "regeneration_count": 1,
                "initial_validation": validation,
            },
        }

    def _generate_validated_answer(
        self,
        answer_prompt: str,
        *,
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        """Generate an answer, validate language, and return answer text only."""
        return str(
            self._generate_validated_answer_result(
                answer_prompt,
                on_chunk=on_chunk,
            )["answer"]
        )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token count when provider usage is unavailable."""
        stripped = text.strip()
        if not stripped:
            return 0
        try:
            import tiktoken  # noqa: PLC0415

            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(stripped))
        except Exception:  # noqa: BLE001
            return max(1, len(stripped) // 3)

    def _generation_metric_extra(self, prompt: str, result: dict[str, Any], elapsed_sec: float) -> dict[str, Any]:
        """Build provider-agnostic generation metrics for the monitor."""
        answer = str(result.get("answer", ""))
        chars = len(answer)
        usage = getattr(self.generator, "last_usage", None)
        provider = str(getattr(self.generator, "provider", "unknown") or "unknown")
        model = str(getattr(self.generator, "model", "unknown") or "unknown")
        input_tokens: int | None = None
        output_tokens: int | None = None
        total_tokens: int | None = None
        input_tokens_per_sec: float | None = None
        output_tokens_per_sec: float | None = None
        token_count_source = "unavailable"
        raw_usage = dict(usage) if isinstance(usage, dict) else None

        if provider == "openai" and raw_usage:
            input_tokens = self._to_int(raw_usage.get("prompt_tokens"))
            output_tokens = self._to_int(raw_usage.get("completion_tokens"))
            total_tokens = self._to_int(raw_usage.get("total_tokens"))
            token_count_source = "provider_usage"
            output_tokens_per_sec = output_tokens / elapsed_sec if output_tokens is not None else None
        elif provider == "ollama" and raw_usage:
            input_tokens = self._to_int(raw_usage.get("prompt_eval_count"))
            output_tokens = self._to_int(raw_usage.get("eval_count"))
            if input_tokens is not None and output_tokens is not None:
                total_tokens = input_tokens + output_tokens
            prompt_duration = self._duration_sec(raw_usage.get("prompt_eval_duration"))
            eval_duration = self._duration_sec(raw_usage.get("eval_duration"))
            input_tokens_per_sec = input_tokens / prompt_duration if input_tokens is not None and prompt_duration else None
            output_tokens_per_sec = output_tokens / eval_duration if output_tokens is not None and eval_duration else None
            if output_tokens_per_sec is None and output_tokens is not None:
                output_tokens_per_sec = output_tokens / elapsed_sec
            token_count_source = "provider_usage"

        if token_count_source == "unavailable" and provider in {"openai", "ollama"}:
            input_tokens = self._estimate_tokens(prompt)
            output_tokens = self._estimate_tokens(answer)
            total_tokens = input_tokens + output_tokens
            output_tokens_per_sec = output_tokens / elapsed_sec if elapsed_sec > 0 else None
            token_count_source = "tokenizer_estimate"

        return {
            "stage_type": "generation",
            "provider": provider,
            "model": model,
            "generation_elapsed_sec": elapsed_sec,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "output_tokens_per_sec": output_tokens_per_sec,
            "input_tokens_per_sec": input_tokens_per_sec,
            "chars": chars,
            "chars_per_sec": chars / elapsed_sec if elapsed_sec > 0 else 0.0,
            "status": "success",
            "token_count_source": token_count_source,
            "raw_usage": raw_usage,
        }

    @staticmethod
    def _to_int(value: Any) -> int | None:
        """Convert provider token usage values to integers when available."""
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _duration_sec(value: Any) -> float | None:
        """Convert Ollama nanosecond durations to seconds."""
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        return numeric / 1_000_000_000 if numeric > 0 else None

    def _retrieve(self, query: str, trace=None):
        """Run retrieval with split hybrid monitoring when the retriever supports it."""
        if all(hasattr(self.retriever, name) for name in ("retrieve_bm25", "retrieve_dense", "fuse")):
            if trace is None:
                return self.retriever.invoke(query)

            bm25_docs = trace.run_stage(
                "stage_1_retrieval_bm25",
                lambda: self.retriever.retrieve_bm25(query),
                throughput_unit="calls/sec",
                throughput_fn=lambda out: 1,
                result_count_fn=len,
            )
            dense_docs = trace.run_stage(
                "stage_1_retrieval_dense",
                lambda: self.retriever.retrieve_dense(query),
                throughput_unit="calls/sec",
                throughput_fn=lambda out: 1,
                result_count_fn=len,
            )
            return trace.run_stage(
                "stage_1_retrieval_fusion",
                lambda: self.retriever.fuse(dense_docs=dense_docs, bm25_docs=bm25_docs),
                throughput_unit="calls/sec",
                throughput_fn=lambda out: 1,
                result_count_fn=len,
            )

        if trace is not None:
            return trace.run_stage(
                "stage_1_retrieval_fusion",
                lambda: self.retriever.invoke(query),
                throughput_unit="calls/sec",
                throughput_fn=lambda out: 1,
                result_count_fn=len,
            )
        return self.retriever.invoke(query)

    def answer(
        self,
        query: str,
        language: str | None = None,
        *,
        on_chunk: Callable[[str], None] | None = None,
        trace=None,
    ) -> dict:
        """Answer a user query through the configured RAG flow.
        Return the answer text, retrieved ids, contexts, and monitoring metadata."""
        if self.generator is None:
            raise ValueError("`generator` is required.")

        if self.monitor is not None:
            trace = trace or self.monitor.start_trace(
                query=query,
                metadata={"mode": "single_generator"},
            )

        docs = self._retrieve(query, trace=trace)

        context = build_context(docs)
        answer_prompt = self._build_answer_prompt(query, context, language=language)
        if trace is not None:
            generation_result = trace.run_stage(
                "stage_2_generation",
                lambda: self._generate_validated_answer_result(answer_prompt, on_chunk=on_chunk),
                throughput_unit="chars/sec",
                throughput_fn=lambda out: len(str(out.get("answer", ""))),
                metric_extra_fn=lambda out, elapsed: self._generation_metric_extra(answer_prompt, out, elapsed),
                timeout_sec=self.monitor_stage3_timeout_sec,
            )
        else:
            generation_result = self._generate_validated_answer_result(answer_prompt, on_chunk=on_chunk)

        result = {
            "query": query,
            "answer": generation_result["answer"],
            "language_validation": generation_result["language_validation"],
            "regeneration_count": generation_result["language_validation"]["regeneration_count"],
            "retrieved_ids": [doc.metadata.get("chunk_id") for doc in docs],
            "contexts": docs,
        }
        if trace is not None:
            result["monitoring"] = trace.to_dict()
        return result
