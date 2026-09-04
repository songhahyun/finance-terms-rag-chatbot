"""Small deterministic benchmark for hybrid retrieval concurrency.

Run from the repository root:
    python benchmarks/benchmark_hybrid_retriever.py
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import statistics
import time
from dataclasses import dataclass

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "retrieval" / "hybrid.py"
SPEC = importlib.util.spec_from_file_location("hybrid_retriever_benchmark", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
HybridRetriever = MODULE.HybridRetriever


@dataclass
class FakeDocument:
    page_content: str
    metadata: dict[str, str]


class DelayedRetriever:
    def __init__(self, delay_seconds: float, chunk_id: str) -> None:
        self.delay_seconds = delay_seconds
        self.document = FakeDocument(page_content=chunk_id, metadata={"chunk_id": chunk_id})

    async def ainvoke(self, query: str) -> list[FakeDocument]:
        await asyncio.sleep(self.delay_seconds)
        return [self.document]


async def measure(retriever: HybridRetriever, runs: int = 10) -> list[float]:
    durations = []
    for _ in range(runs):
        started = time.perf_counter()
        await retriever.ainvoke("기준금리")
        durations.append(time.perf_counter() - started)
    return durations


if __name__ == "__main__":
    dense_delay = 0.08
    bm25_delay = 0.05
    samples = asyncio.run(measure(
        HybridRetriever(
            DelayedRetriever(dense_delay, "dense"),
            DelayedRetriever(bm25_delay, "bm25"),
            k=2,
        )
    ))
    median = statistics.median(samples)
    sequential_baseline = dense_delay + bm25_delay
    print(f"runs={len(samples)}")
    print(f"sequential_baseline={sequential_baseline:.4f}s")
    print(f"parallel_median={median:.4f}s")
    print(f"latency_reduction={(1 - median / sequential_baseline) * 100:.1f}%")
