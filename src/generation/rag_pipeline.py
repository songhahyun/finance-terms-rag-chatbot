from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
from typing import Any

from src.generation.context import build_context
from src.generation.prompts import (
    KEYWORD_EXTRACTION_PROMPT,
    QUERY_COMPLEXITY_PROMPT,
    RAG_PROMPT,
    ROUTED_RAG_PROMPT,
)
from src.monitor import PipelineMonitor


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    """Extract the first valid JSON object from model output.
    Handle both clean JSON responses and noisy text-wrapped payloads."""
    text = raw_text.strip()
    try:
        loaded = json.loads(text)
        return loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        loaded = json.loads(match.group(0))
        return loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError:
        return {}


def _normalize_keywords(items: Any) -> list[str]:
    """Normalize extracted keywords into a deduplicated list.
    Keep insertion order and cap the result size at eight items."""
    if not isinstance(items, list):
        return []
    seen: set[str] = set()
    keywords: list[str] = []
    for item in items:
        token = str(item).strip()
        if not token:
            continue
        lowered = token.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        keywords.append(token)
        if len(keywords) >= 8:
            break
    return keywords


class RAGPipeline:
    def __init__(
        self,
        retriever,
        generator=None,
        *,
        keyword_extractor=None,
        complexity_classifier=None,
        simple_generator=None,
        complex_generator=None,
        monitor: PipelineMonitor | None = None,
        monitor_stage3_timeout_sec: float | None = None,
    ) -> None:
        """Initialize the RAG pipeline with retrieval, generation, and monitoring pieces.
        Support either single-generator mode or routed multi-model mode."""
        self.retriever = retriever
        self.generator = generator
        self.keyword_extractor = keyword_extractor
        self.complexity_classifier = complexity_classifier
        self.simple_generator = simple_generator
        self.complex_generator = complex_generator
        self.monitor = monitor
        self.monitor_stage3_timeout_sec = monitor_stage3_timeout_sec

    @property
    def is_multi_agent_enabled(self) -> bool:
        """Check whether all routed-generation components are present.
        Return true only when keyword, routing, and both generators exist."""
        return all(
            (
                self.keyword_extractor is not None,
                self.complexity_classifier is not None,
                self.simple_generator is not None,
                self.complex_generator is not None,
            )
        )

    def _extract_keywords(self, query: str) -> list[str]:
        """Generate retrieval keywords from the user query.
        Return an empty list when no keyword extractor is configured."""
        if self.keyword_extractor is None:
            return []
        prompt = KEYWORD_EXTRACTION_PROMPT.format(question=query)
        raw = self.keyword_extractor.generate(prompt)
        payload = _extract_json_object(raw)
        return _normalize_keywords(payload.get("keywords"))

    def _classify_query(self, query: str) -> tuple[str, str]:
        """Classify the query as simple or complex.
        Return both the routing label and the model-provided reason."""
        if self.complexity_classifier is None:
            return "complex_reasoning", "default_fallback"
        prompt = QUERY_COMPLEXITY_PROMPT.format(question=query)
        raw = self.complexity_classifier.generate(prompt)
        payload = _extract_json_object(raw)
        label = str(payload.get("label", "")).strip().lower()
        reason = str(payload.get("reason", "")).strip()
        if label not in {"simple_definition", "complex_reasoning"}:
            label = "complex_reasoning"
        return label, reason

    def _build_retrieval_query(self, query: str, keywords: list[str]) -> str:
        """Augment the retrieval query with extracted keywords.
        Fall back to the original query when no keywords are available."""
        if not keywords:
            return query
        return f"{query}\n\n[검색 키워드] " + ", ".join(keywords)

    def _build_answer_prompt(self, query: str, context: str, language: str | None = None) -> str:
        """Construct the final generation prompt for the answer model.
        Append a language instruction when the caller specifies one."""
        prompt = ROUTED_RAG_PROMPT.format(context=context, question=query)
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
        Return the answer text, retrieved ids, contexts, and routing metadata."""
        trace = None
        if self.monitor is not None:
            trace = self.monitor.start_trace(
                query=query,
                metadata={"mode": "multi_agent" if self.is_multi_agent_enabled else "single_agent"},
            )

        if not self.is_multi_agent_enabled:
            if self.generator is None:
                raise ValueError("`generator` is required when multi-agent mode is disabled.")
            if trace is not None:
                docs = trace.run_stage(
                    "stage_2a_retrieval",
                    lambda: self.retriever.invoke(query),
                    throughput_unit="docs/sec",
                    throughput_fn=lambda out: len(out),
                )
            else:
                docs = self.retriever.invoke(query)
            context = build_context(docs)
            prompt = RAG_PROMPT.format(context=context, question=query)
            if language == "ko":
                prompt += "\n\nRespond in Korean."
            elif language == "en":
                prompt += "\n\nRespond in English."
            if trace is not None:
                answer = trace.run_stage(
                    "stage_3_answer_generation",
                    lambda: self._generate_text(self.generator, prompt, on_chunk),
                    throughput_unit="chars/sec",
                    throughput_fn=lambda out: len(str(out)),
                    timeout_sec=self.monitor_stage3_timeout_sec,
                )
            else:
                answer = self._generate_text(self.generator, prompt, on_chunk)
            result = {
                "query": query,
                "answer": answer,
                "retrieved_ids": [doc.metadata.get("chunk_id") for doc in docs],
                "contexts": docs,
            }
            if trace is not None:
                result["monitoring"] = trace.to_dict()
            return result

        # Stage 1: keyword extraction (small model)
        if trace is not None:
            keywords = trace.run_stage(
                "stage_1_keyword_extraction",
                lambda: self._extract_keywords(query),
                throughput_unit="keywords/sec",
                throughput_fn=lambda out: len(out),
            )
        else:
            keywords = self._extract_keywords(query)
        retrieval_query = self._build_retrieval_query(query, keywords)

        # Stage 2-a, 2-b: parallel execution
        with ThreadPoolExecutor(max_workers=2) as executor:
            if trace is not None:
                retrieval_future = executor.submit(
                    lambda: trace.run_stage(
                        "stage_2a_retrieval",
                        lambda: self.retriever.invoke(retrieval_query),
                        throughput_unit="docs/sec",
                        throughput_fn=lambda out: len(out),
                    )
                )
                classify_future = executor.submit(
                    lambda: trace.run_stage(
                        "stage_2b_complexity_classification",
                        lambda: self._classify_query(query),
                        throughput_unit="labels/sec",
                        throughput_fn=lambda _: 1.0,
                    )
                )
            else:
                retrieval_future = executor.submit(self.retriever.invoke, retrieval_query)
                classify_future = executor.submit(self._classify_query, query)
            docs = retrieval_future.result()
            query_type, route_reason = classify_future.result()

        # Stage 3: route answer generation
        context = build_context(docs)
        answer_prompt = self._build_answer_prompt(query, context, language=language)
        if query_type == "simple_definition":
            router_target = "simple_generator"
            if trace is not None:
                answer = trace.run_stage(
                    "stage_3_answer_generation_simple",
                    lambda: self._generate_text(self.simple_generator, answer_prompt, on_chunk),
                    throughput_unit="chars/sec",
                    throughput_fn=lambda out: len(str(out)),
                    timeout_sec=self.monitor_stage3_timeout_sec,
                )
            else:
                answer = self._generate_text(self.simple_generator, answer_prompt, on_chunk)
        else:
            router_target = "complex_generator"
            if trace is not None:
                answer = trace.run_stage(
                    "stage_3_answer_generation_complex",
                    lambda: self._generate_text(self.complex_generator, answer_prompt, on_chunk),
                    throughput_unit="chars/sec",
                    throughput_fn=lambda out: len(str(out)),
                    timeout_sec=self.monitor_stage3_timeout_sec,
                )
            else:
                answer = self._generate_text(self.complex_generator, answer_prompt, on_chunk)

        result = {
            "query": query,
            "answer": answer,
            "retrieved_ids": [doc.metadata.get("chunk_id") for doc in docs],
            "contexts": docs,
            "keywords": keywords,
            "query_type": query_type,
            "route_reason": route_reason,
            "router_target": router_target,
        }
        if trace is not None:
            result["monitoring"] = trace.to_dict()
        return result
