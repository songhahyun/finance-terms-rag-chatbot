# Generation Baseline Experiment Summary

## Scope

This report summarizes the generation baseline outputs under `data/eval/outputs/generation_001_baseline/`.

Input files reviewed:

- `generation_experiment_summary.csv`
- `dense_clova_bge-m3.csv`
- `hybrid_clova_bge-m3.csv`
- `hybrid_openai_text-embedding-3-small.csv`

The comparison below focuses on the main metrics in `generation_experiment_summary.csv`: average recall, average MRR, retrieval latency, generation latency, and total latency. Case-level comments are based on manual review of the generated answers in each experiment CSV.

## Overall Results

| Experiment | Rows | Avg Recall | Avg MRR | Avg Retrieval Latency (s) | Avg Generation Latency (s) | Avg Total Latency (s) |
|---|---:|---:|---:|---:|---:|---:|
| `hybrid_clova_bge-m3` | 100 | 0.980 | 0.978 | 0.473 | 11.467 | 11.939 |
| `dense_clova_bge-m3` | 100 | 0.968 | 1.000 | 0.466 | 10.597 | 11.062 |
| `hybrid_openai_text-embedding-3-small` | 100 | 0.958 | 0.970 | 0.388 | 10.310 | 10.698 |

## Key Findings

`hybrid_clova_bge-m3` produced the best average recall at 0.980, so it retrieved the broadest set of gold documents overall. However, it was also the slowest configuration, mostly because generation latency averaged 11.467 seconds.

`dense_clova_bge-m3` had the best average MRR at 1.000, meaning the first relevant document was consistently ranked at the top when measured by this dataset. Its recall was slightly lower than the hybrid Clova setting, but it had a better speed/quality balance than `hybrid_clova_bge-m3`.

`hybrid_openai_text-embedding-3-small` was the fastest configuration, with the lowest retrieval, generation, and total latency. Its quality metrics were the weakest of the three, with average recall at 0.958 and average MRR at 0.970. The lower recall showed up most clearly in multi-term comparison questions.

Across all experiments, many failures were not captured by recall or MRR alone. Several rows had perfect retrieval metrics but poor generation due to Chinese text leakage, duplicated reasoning, malformed wording, or incorrect interpretation of a financial term. Generation quality therefore needs an additional answer-level evaluation beyond retrieval metrics.

## Experiment Case Review

### `dense_clova_bge-m3`

Good generation cases:

| Question ID | Query | Metrics | Why It Worked |
|---|---|---|---|
| `q003` | 경기동향지수(경기확산지수)의 정의를 알려주세요. | recall 1.000, MRR 1.000, total 5.217s | The answer directly defined the diffusion index, explained the 50 threshold, and stayed grounded without language leakage. |
| `q038` | 국채의 정의를 알려주세요. | recall 1.000, MRR 1.000, total 6.073s | The answer clearly described government bond issuance, purpose, maturities, and issuance method. |
| `q049` | 청년실업률의 의미는 무엇인가요? | recall 1.000, MRR 1.000, total 6.511s | The answer correctly identified the 15-29 age range and explained the denominator/exclusions in a useful way. |

Poor generation cases:

| Question ID | Query | Metrics | Issue |
|---|---|---|---|
| `q016` | 국제원유가격란 무엇을 의미하나요? | recall 1.000, MRR 1.000, total 5.014s | Retrieval was perfect, but the answer was almost entirely in Chinese, so it failed the expected Korean response format. |
| `q090` | 수출보험, 가계부실위험지수(HDRI) 및 가계수지에 대해 설명하고 서로 어떻게 연관되는지 알려주세요. | recall 0.333, MRR 1.000, total 12.063s | Only one of three gold documents was retrieved; the answer became broad and partly speculative, especially around relationships among unrelated concepts. |
| `q094` | 자동안정화장치, 가계부실위험지수(HDRI) 및 가계수지에 대해 설명하고 서로 어떻게 연관되는지 알려주세요. | recall 1.000, MRR 1.000, total 12.268s | Despite perfect retrieval, the answer leaked Chinese text and began with malformed mixed-language headings such as `-automatic`. |

### `hybrid_clova_bge-m3`

Good generation cases:

| Question ID | Query | Metrics | Why It Worked |
|---|---|---|---|
| `q003` | 경기동향지수(경기확산지수)의 정의를 알려주세요. | recall 1.000, MRR 1.000, total 9.086s | The answer explained definition, calculation intuition, and interpretation of the 50 threshold. |
| `q038` | 국채의 정의를 알려주세요. | recall 1.000, MRR 1.000, total 5.673s | The answer was concise and accurately covered purpose, maturity structure, and issuance method. |
| `q049` | 청년실업률의 의미는 무엇인가요? | recall 1.000, MRR 1.000, total 8.152s | The answer defined the indicator and explained why non-economically active youth are excluded. |

Poor generation cases:

| Question ID | Query | Metrics | Issue |
|---|---|---|---|
| `q078` | 페더럴펀드와 스마트계약의 차이점과 관계를 설명해주세요. | recall 1.000, MRR 1.000, total 23.890s | The answer had severe Chinese prompt/reasoning leakage and duplicated structure; it was also an extreme latency outlier. |
| `q094` | 자동안정화장치, 가계부실위험지수(HDRI) 및 가계수지에 대해 설명하고 서로 어떻게 연관되는지 알려주세요. | recall 1.000, MRR 1.000, total 12.347s | The answer mixed Korean and Chinese and used malformed wording, so generation failed even though retrieval was correct. |
| `q081` | VAN사업자, 지급결제시스템, 전자금융는 무엇이며 각각 어떤 차이가 있나요? | recall 0.667, MRR 1.000, total 12.244s | One gold item was missed, and the answer compressed differences among three concepts too broadly. |

### `hybrid_openai_text-embedding-3-small`

Good generation cases:

| Question ID | Query | Metrics | Why It Worked |
|---|---|---|---|
| `q003` | 경기동향지수(경기확산지수)의 정의를 알려주세요. | recall 1.000, MRR 1.000, total 8.258s | The answer correctly summarized the definition and interpretation of the index. |
| `q028` | 통화안정증권의 정의를 알려주세요. | recall 1.000, MRR 1.000, total 7.092s | The answer gave a strong definition and included legal basis, purpose, maturity, and policy role. |
| `q049` | 청년실업률의 의미는 무엇인가요? | recall 1.000, MRR 1.000, total 7.039s | The answer was clear, complete, and free of visible formatting or language artifacts. |

Poor generation cases:

| Question ID | Query | Metrics | Issue |
|---|---|---|---|
| `q016` | 국제원유가격란 무엇을 의미하나요? | recall 1.000, MRR 1.000, total 5.910s | The answer was mostly Chinese despite perfect retrieval, showing that retrieval quality did not guarantee usable generation. |
| `q087` | 결제완결성, 가계부실위험지수(HDRI), 가계수지의 정의와 차이점을 설명해주세요. | recall 0.667, MRR 1.000, total 12.189s | The answer incorrectly described settlement finality as a household/business ability to settle expenses, indicating a term-level grounding error. |
| `q082` | 한국은행, 중앙은행 및 금융안정에 대해 설명하고 서로 어떻게 연관되는지 알려주세요. | recall 0.333, MRR 1.000, total 12.237s | The lowest recall case for this experiment; the answer drifted into loosely related topics such as government deposit accounts and international input-output tables. |

## Conclusion

For retrieval-oriented metrics, `hybrid_clova_bge-m3` is strongest on recall, while `dense_clova_bge-m3` is strongest on MRR. For runtime, `hybrid_openai_text-embedding-3-small` is clearly fastest.

For generation quality, the main risk is not retrieval rank alone. The most important failure mode is answer contamination: Chinese text, internal reasoning fragments, malformed mixed-language terms, and occasional incorrect concept grounding. The next evaluation pass should add answer-level checks for language consistency, term correctness, unsupported reasoning, and response format compliance.
