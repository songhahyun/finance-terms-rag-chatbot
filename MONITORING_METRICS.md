# Monitoring Metrics

이 문서는 `/api/chat` 호출 시 생성되는 stage 모니터링 로그의 적재 흐름과 관리자 대시보드/API에서 산출하는 지표를 정리합니다.

## 적재 흐름

1. `RAGService.answer()`가 사용자 질의마다 `PipelineMonitor.start_trace()`를 호출해 `trace_id`, `query`, `created_at`, 요청 메타데이터를 생성합니다.
2. 각 처리 단계는 `QueryTrace.run_stage()`로 감싸 실행됩니다. stage 실행 전후 시각, 처리 시간, 성공 여부, 오류 메시지, 처리량 관련 필드가 `StageMetric`으로 기록됩니다.
3. `PipelineMonitor`는 stage metric을 프로세스 메모리의 bounded history와 row queue에 적재합니다. 기본 서비스 설정은 최대 1000개 trace를 유지합니다.
4. `MONITOR_STAGE_LOG_PATH`가 설정되어 있으면 stage metric 로그를 파일에도 남깁니다. 기본 경로는 `logs/stage_monitor.log`입니다.
5. Admin API는 같은 `PipelineMonitor` 인스턴스에서 집계 결과와 최근 row를 조회합니다.

관리자 전용 모니터링 API:

- `GET /api/monitor/summary`: stage별 집계와 대시보드용 schema 반환
- `GET /api/monitor/recent?limit=20&page=1&errors_only=false`: 최근 stage row와 pagination 정보 반환

## Stage 구성

| Stage | 유형 | 설명 |
| --- | --- | --- |
| `stage_0_intent_classification` | call_based | 질의가 RAG가 필요한 질문인지, 단순 응답/명확화 대상인지 분류 |
| `stage_1_retrieval_bm25` | call_based | BM25 기반 sparse 검색 |
| `stage_1_retrieval_dense` | call_based | Clova embedding 기반 dense 검색 |
| `stage_1_retrieval_fusion` | call_based | BM25와 dense 검색 결과 fusion |
| `stage_2_generation` | generation | 검색 context 기반 답변 생성과 언어 검증 |

## 공통 Row 필드

- `timestamp`: stage 종료 시각
- `trace_id`: 질의 단위 추적 ID
- `stage`: stage 이름
- `stage_type`: `call_based`, `generation`, `unknown`
- `user_query`: 사용자 질의
- `status`: `success`, `zero_result`, `error`, `timeout`
- `error_message`: 예외 또는 timeout 메시지
- `elapsed_sec`: stage 처리 시간
- `throughput`: 레거시 호환용 처리량 값

## Call-Based 지표

대상 stage: `stage_0_intent_classification`, `stage_1_retrieval_bm25`, `stage_1_retrieval_dense`, `stage_1_retrieval_fusion`

- `attempted_count`: stage 시도 횟수
- `success_count`: 성공 횟수
- `fail_count`: 실패 횟수
- `result_count`: 검색/처리 결과 개수
- `attempted_calls_per_sec`: `attempted_count / elapsed_sec`
- `successful_calls_per_sec`: `success_count / elapsed_sec`
- `success_rate`: 집계 구간의 성공 row 비율
- `avg_elapsed_sec`: 집계 구간의 평균 stage 처리 시간

검색 stage에서 결과가 0건이면 `status`는 `zero_result`로 기록됩니다. 이는 오류가 아니라 성공 처리된 무결과 상태입니다.

`stage_1_retrieval_fusion`은 매우 짧은 micro-stage이므로 대시보드에서는 elapsed time 중심으로 표시하고 RPS/count/status 필드는 표시하지 않습니다.

## Generation 지표

대상 stage: `stage_2_generation`

- `provider`: 생성 provider (`openai`, `ollama`, `unknown`)
- `model`: 생성 모델명
- `generation_elapsed_sec`: 답변 생성 stage 처리 시간
- `input_tokens`: 입력 token 수
- `output_tokens`: 출력 token 수
- `total_tokens`: 입력+출력 token 수
- `output_tokens_per_sec`: 출력 token 처리량
- `input_tokens_per_sec`: 입력 token 처리량
- `chars`: 생성 답변 문자 수
- `chars_per_sec`: `chars / generation_elapsed_sec`
- `token_count_source`: `provider_usage`, `tokenizer_estimate`, `unavailable`
- `raw_usage`: provider가 반환한 원본 usage 메타데이터

OpenAI와 Ollama가 usage를 제공하면 provider usage를 사용합니다. usage가 없고 provider가 지원 대상이면 tokenizer 기반 추정치를 사용합니다.

## 대시보드 집계 지표

`/api/monitor/summary`는 두 종류의 summary를 반환합니다.

- `stage_summary`: 레거시 호환 summary
  - `count`
  - `success_count`
  - `success_rate`
  - `avg_elapsed_sec`
  - `avg_throughput`
  - `throughput_unit`
- `dashboard_stage_summary`: stage 유형별 대시보드 schema
  - call-based: `elapsed_sec`, `attempted_rps`, `successful_rps`, `result_count`, `status`
  - generation: `elapsed_sec`, `output_tps`, `chars_per_sec`, `rpm`, `output_tpm`, `total_tpm`, token 합계, `token_count_source`, `status`

대시보드 throughput chart는 최근 row를 기준으로 다음 값을 계산합니다.

- Intent/retrieval stage: `successful_calls_per_sec`
- Generation RPM: `60 / elapsed_sec`
- Generation Output TPM: `output_tokens_per_sec * 60`
- Generation Total TPM: `(total_tokens / generation_elapsed_sec) * 60`
