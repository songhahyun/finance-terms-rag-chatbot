# RAGAS Baseline 001 Summary

## Scope

This report summarizes the RAGAS evaluation outputs under `data/eval/outputs/ragas_001_baseline/`.

Input files reviewed:

- `ragas_experiment_summary.csv`
- `dense_clova_bge-m3_ragas.csv`
- `hybrid_clova_bge-m3_ragas.csv`
- `hybrid_openai_text-embedding-3-small_ragas.csv`

Some metric cells are empty in the detailed outputs because of OpenAI rate limit issues during RAGAS evaluation. The aggregate values in `ragas_experiment_summary.csv` should therefore be interpreted as averages over the successfully evaluated rows for each metric, not as complete 100-row coverage for every metric.

## Overall Results

| Experiment | Rows | Answer Relevancy | Faithfulness | Context Precision | Context Recall |
|---|---:|---:|---:|---:|---:|
| `dense_clova_bge-m3` | 100 | 0.814 | 0.863 | 0.972 | 0.982 |
| `hybrid_clova_bge-m3` | 100 | 0.823 | 0.866 | 0.960 | 0.975 |
| `hybrid_openai_text-embedding-3-small` | 100 | 0.809 | 0.814 | 0.960 | 0.972 |

## Missing Evaluation Values

| Experiment | Answer Relevancy Valid / Blank | Faithfulness Valid / Blank | Context Precision Valid / Blank | Context Recall Valid / Blank | Rows With Any Blank |
|---|---:|---:|---:|---:|---:|
| `dense_clova_bge-m3` | 100 / 0 | 100 / 0 | 100 / 0 | 99 / 1 | 1 |
| `hybrid_clova_bge-m3` | 100 / 0 | 99 / 1 | 100 / 0 | 98 / 2 | 3 |
| `hybrid_openai_text-embedding-3-small` | 100 / 0 | 97 / 3 | 100 / 0 | 98 / 2 | 5 |

Blank values were concentrated in faithfulness and context recall. This means answer relevancy and context precision are complete for all three experiments, while faithfulness/context recall comparisons have a small amount of missing data.

## Metric Interpretation

`hybrid_clova_bge-m3` has the best answer-level scores. It ranks first on answer relevancy at 0.823 and faithfulness at 0.866. This suggests that, among the three tested generation pipelines, the hybrid Clova retriever produced answers that were slightly more aligned with the question and marginally more grounded in the retrieved context.

`dense_clova_bge-m3` has the best context-level scores. It ranks first on context precision at 0.972 and context recall at 0.982, while also staying very close to `hybrid_clova_bge-m3` on faithfulness. This result is consistent with the retrieval baseline where dense Clova had perfect MRR and strong recall.

`hybrid_openai_text-embedding-3-small` is weaker on RAGAS answer quality. Its context metrics remain strong, but it has the lowest answer relevancy at 0.809 and the lowest faithfulness at 0.814. The lower faithfulness score suggests more unsupported or less tightly grounded answer content compared with the two Clova-based configurations.

## Best and Weakest Case Patterns

### `dense_clova_bge-m3`

Best cases:

| Question ID | Query | RAGAS Scores | Reason |
|---|---|---|---|
| `q074` | 비용인상 인플레이션와 수요견인 인플레이션의 차이점과 관계를 설명해주세요. | answer relevancy 0.969, faithfulness 1.000, context precision 1.000, context recall 1.000 | The answer was highly relevant, fully grounded, and the retrieved context covered the needed comparison. |
| `q005` | 본원소득수지는 무엇인가요? | answer relevancy 0.965, faithfulness 1.000, context precision 1.000, context recall 1.000 | The answer matched the question closely and used the retrieved evidence without unsupported claims. |
| `q079` | 대체비용리스크와 외환결제리스크는 무엇이며 어떻게 다른가요? | answer relevancy 0.905, faithfulness 1.000, context precision 1.000, context recall 1.000 | The answer correctly distinguished two related risk terms and stayed faithful to the context. |

Weak cases:

| Question ID | Query | RAGAS Scores | Reason |
|---|---|---|---|
| `q096` | 직접투자, 가계부실위험지수(HDRI), 가계수지의 의미를 설명하고 이 세 용어의 관계를 비교해주세요. | answer relevancy 0.000, faithfulness 0.375, context precision 1.000, context recall 1.000 | Context retrieval was strong, but the generated answer was judged poorly aligned with the question and only weakly faithful. |
| `q090` | 수출보험, 가계부실위험지수(HDRI) 및 가계수지에 대해 설명하고 서로 어떻게 연관되는지 알려주세요. | answer relevancy 0.898, faithfulness 0.200, context precision 1.000, context recall 0.300 | The answer was topically relevant, but grounding was weak and the retrieved context did not cover all required concepts. |
| `q064` | 예대율와 빅맥지수에 대해 각각 설명하고 둘의 관계를 설명하세요. | answer relevancy 0.000, faithfulness 0.786, context precision 0.887, context recall 1.000 | The answer had usable context coverage but was judged irrelevant to the expected answer, likely because the relationship explanation was weak or misaligned. |

### `hybrid_clova_bge-m3`

Best cases:

| Question ID | Query | RAGAS Scores | Reason |
|---|---|---|---|
| `q004` | 사회보장제도의 의미는 무엇인가요? | answer relevancy 0.963, faithfulness 1.000, context precision 1.000, context recall 1.000 | The answer was complete, directly addressed the definition, and matched the retrieved context. |
| `q015` | 경영실태평가/은행경영실태등급평가제도는 무엇인가요? | answer relevancy 0.916, faithfulness 1.000, context precision 1.000, context recall 1.000 | The model generated a grounded explanation of a specific institutional term with no context gaps. |
| `q091` | 매매보호 서비스(escrow), 가계부실위험지수(HDRI), 가계수지의 정의와 차이점을 설명해주세요. | answer relevancy 0.906, faithfulness 1.000, context precision 1.000, context recall 1.000 | Despite being a multi-term comparison question, retrieval and generation both stayed complete and faithful. |

Weak cases:

| Question ID | Query | RAGAS Scores | Reason |
|---|---|---|---|
| `q016` | 국제원유가격란 무엇을 의미하나요? | answer relevancy 0.000, faithfulness 0.556, context precision 1.000, context recall 1.000 | The context was sufficient, but the generated answer was not judged relevant, consistent with the language-contamination issue seen in generation review. |
| `q056` | 국고대리점와 자연실업률에 대해 각각 설명하고 둘의 관계를 설명하세요. | answer relevancy 0.000, faithfulness 0.588, context precision 1.000, context recall 1.000 | The retrieved context was complete, but the answer did not satisfy the expected relationship/comparison framing. |
| `q034` | 모바일뱅킹의 의미는 무엇인가요? | answer relevancy 0.000, faithfulness N/A, context precision 1.000, context recall 1.000 | Answer relevancy failed and faithfulness was blank because of the OpenAI rate limit issue, so this row is both weak and partially unevaluated. |

### `hybrid_openai_text-embedding-3-small`

Best cases:

| Question ID | Query | RAGAS Scores | Reason |
|---|---|---|---|
| `q026` | 물가지수란 무엇을 의미하나요? | answer relevancy 0.971, faithfulness 1.000, context precision 1.000, context recall 1.000 | This was the strongest overall case for this experiment, with a relevant answer and complete grounding. |
| `q081` | VAN사업자, 지급결제시스템, 전자금융는 무엇이며 각각 어떤 차이가 있나요? | answer relevancy 0.943, faithfulness 1.000, context precision 1.000, context recall 1.000 | The model handled a three-term comparison well and used the retrieved context faithfully. |
| `q074` | 비용인상 인플레이션와 수요견인 인플레이션의 차이점과 관계를 설명해주세요. | answer relevancy 0.972, faithfulness 0.944, context precision 1.000, context recall 1.000 | The answer was highly relevant and context coverage was complete, with only a small faithfulness drop. |

Weak cases:

| Question ID | Query | RAGAS Scores | Reason |
|---|---|---|---|
| `q056` | 국고대리점와 자연실업률에 대해 각각 설명하고 둘의 관계를 설명하세요. | answer relevancy 0.000, faithfulness 0.353, context precision 1.000, context recall 1.000 | The generated answer was poorly aligned with the expected answer and had the lowest faithfulness among the selected weak cases. |
| `q066` | 자발적 실업와 마찰적 실업의 차이점과 관계를 설명해주세요. | answer relevancy 0.000, faithfulness 0.813, context precision 1.000, context recall N/A | Answer relevancy failed, and context recall is missing because of the rate limit issue. |
| `q064` | 예대율와 빅맥지수에 대해 각각 설명하고 둘의 관계를 설명하세요. | answer relevancy 0.000, faithfulness 0.444, context precision 1.000, context recall 1.000 | Retrieval precision was high, but the answer was not relevant enough and had weak grounding. |

## Key Findings

All three selected generation pipelines show strong context retrieval quality under RAGAS, with context precision and context recall generally above 0.96. The main differentiation is in answer-level quality rather than context retrieval.

`hybrid_clova_bge-m3` is the strongest overall RAGAS configuration because it has the best answer relevancy and faithfulness. `dense_clova_bge-m3` is a close second and has the strongest context metrics. `hybrid_openai_text-embedding-3-small` remains viable but is weaker on faithfulness and has the largest number of missing RAGAS metric cells due to rate limit interruptions.

## Conclusion

Based on the available RAGAS results, `hybrid_clova_bge-m3` is the best answer-quality baseline, while `dense_clova_bge-m3` is the best context-quality baseline. `hybrid_openai_text-embedding-3-small` performs reasonably on context metrics but trails the Clova-based runs on answer relevancy and faithfulness.

Because several detailed rows have blank RAGAS values due to OpenAI rate limit issues, the current result should be treated as a baseline rather than a final statistically complete comparison. A follow-up run should re-evaluate only the missing rows, then regenerate the summary to confirm whether the ranking remains stable.
