# Retrieval Baseline 002 Summary

## Scope

This report summarizes the retrieval experiment outputs under `data/eval/outputs/retrieval_002_baseline/`.

Input files reviewed:

- `retriever_comparison_summary.csv`
- `retriever_comparison_detail.csv`

The evaluation compares retrieval methods using recall, MRR, hit rate, and query latency. The goal is to choose retrieval configurations that provide strong retrieval quality while keeping latency practical for the downstream generation pipeline.

## Overall Results

| Experiment | Mode | Hit | Recall | MRR | Avg Query Latency (s) |
|---|---|---:|---:|---:|---:|
| `bm25` | bm25 | 0.960 | 0.903 | 0.920 | 0.003 |
| `dense:clova:bge-m3` | dense | 1.000 | 0.968 | 1.000 | 0.096 |
| `dense:local:BAAI/bge-m3` | dense | 1.000 | 0.972 | 1.000 | 0.314 |
| `dense:openai:text-embedding-3-small` | dense | 1.000 | 0.925 | 0.978 | 0.204 |
| `hybrid:clova:bge-m3` | hybrid | 1.000 | 0.980 | 0.978 | 0.105 |
| `hybrid:local:BAAI/bge-m3` | hybrid | 1.000 | 0.980 | 0.978 | 0.376 |
| `hybrid:openai:text-embedding-3-small` | hybrid | 1.000 | 0.958 | 0.970 | 0.166 |

## Detail Distribution

| Experiment | Queries | Recall < 1.0 | MRR < 1.0 | Misses | P50 Latency (s) | P95 Latency (s) | Max Latency (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `bm25` | 100 | 16 | 11 | 4 | 0.003 | 0.005 | 0.007 |
| `dense:clova:bge-m3` | 100 | 8 | 0 | 0 | 0.091 | 0.124 | 0.227 |
| `dense:local:BAAI/bge-m3` | 100 | 7 | 0 | 0 | 0.284 | 0.496 | 0.737 |
| `dense:openai:text-embedding-3-small` | 100 | 17 | 4 | 0 | 0.142 | 0.273 | 2.544 |
| `hybrid:clova:bge-m3` | 100 | 6 | 4 | 0 | 0.092 | 0.133 | 0.354 |
| `hybrid:local:BAAI/bge-m3` | 100 | 6 | 4 | 0 | 0.308 | 0.701 | 0.949 |
| `hybrid:openai:text-embedding-3-small` | 100 | 10 | 5 | 0 | 0.145 | 0.264 | 0.293 |

## Selection Rationale

`hybrid:clova:bge-m3` is the strongest overall retrieval-quality option. It has the highest recall among the tested configurations at 0.980, no misses, and a practical average latency of 0.105 seconds. It matches the local hybrid model on recall and MRR while being much faster.

`dense:clova:bge-m3` is the best precision/ranking option. It has perfect hit and MRR scores, strong recall at 0.968, and the lowest latency among the dense neural retrievers at 0.096 seconds. It is a strong default when top-rank correctness is more important than the small recall gain from hybrid retrieval.

`hybrid:openai:text-embedding-3-small` provides the best OpenAI-based retrieval tradeoff. Compared with `dense:openai:text-embedding-3-small`, it improves recall from 0.925 to 0.958 and lowers average latency from 0.204 seconds to 0.166 seconds, while keeping hit rate at 1.000. Its MRR is slightly lower than the dense OpenAI variant, but the recall and latency gains make it the better candidate for downstream generation.

## Excluded Configurations

`bm25` is extremely fast, but its recall of 0.903, MRR of 0.920, and 4 missed queries make it too weak as a final retrieval candidate for generation.

`dense:local:BAAI/bge-m3` has excellent quality metrics, but its average latency of 0.314 seconds is more than three times slower than `dense:clova:bge-m3` while offering only a small recall gain.

`hybrid:local:BAAI/bge-m3` ties `hybrid:clova:bge-m3` on recall and MRR, but its average latency is 0.376 seconds, about 3.6 times slower than the Clova hybrid configuration.

`dense:openai:text-embedding-3-small` is dominated by the OpenAI hybrid configuration on recall and latency. It has a slightly higher MRR, but the lower recall and one large latency outlier make it less attractive for the final shortlist.

## Final Decision

Considering latency, recall, and MRR together, the final selected retrieval methods are:

1. `hybrid_clova_bge-m3`
2. `dense_clova_bge-m3`
3. `hybrid_openai_text-embedding-3-small`

These three configurations provide the best practical balance across retrieval quality and runtime. `hybrid_clova_bge-m3` is selected as the highest-recall option, `dense_clova_bge-m3` as the strongest low-latency and perfect-MRR dense option, and `hybrid_openai_text-embedding-3-small` as the best OpenAI embedding based hybrid option.
