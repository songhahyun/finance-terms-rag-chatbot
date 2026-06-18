# Refactoring Roadmap

This roadmap is based on:

- `docs/ARCHITECTURE_REVIEW.md`
- `docs/DEAD_CODE_ANALYSIS.md`
- `docs/RAG_PIPELINE_ANALYSIS.md`

It is intentionally staged. Phase 1 reduces risk and clarifies contracts without changing behavior. Phase 2 reshapes core modules after tests exist. Phase 3 adds capabilities or infrastructure changes with higher design and operational impact.

## Phase 1: Safe Refactoring

### 1. Add Contract Tests Around Current Chat Behavior

| Field | Detail |
|---|---|
| Description | Add tests for `/api/chat` response shape, non-RAG intent paths, source serialization, and pipeline cache behavior. Include tests for `simple`, `needs_web`, `clarify`, and `needs_rag`. |
| Expected benefit | Creates a safety net before touching `RAGService`, `RAGPipeline`, or response schemas. |
| Estimated complexity | Medium |
| Files affected | `tests/test_chat_response_schema.py`, `tests/test_rag_service_query_intent.py`, new tests such as `tests/test_chat_api_contract.py` |
| Risk level | Low |

### 2. Add Retrieval Unit Tests for Factory, BM25, and Hybrid Fusion

| Field | Detail |
|---|---|
| Description | Cover `build_retriever` modes, invalid modes, BM25 cache hit/miss behavior, hybrid RRF ordering, deduplication, and missing `chunk_id` handling. |
| Expected benefit | Makes later retrieval refactors safer, especially splitting `bm25.py` and exposing retrieval config. |
| Estimated complexity | Medium |
| Files affected | `tests/test_chroma_http_retriever.py`, new tests such as `tests/test_retriever_factory.py`, `tests/test_bm25_retriever.py`, `tests/test_hybrid_retriever.py` |
| Risk level | Low |

### 3. Align Backend Monitor API and Frontend Types

| Field | Detail |
|---|---|
| Description | Decide whether backend monitor responses should remain nested or become frontend-friendly flattened payloads, then update `frontend-web/src/types/api.ts`, `frontend-web/src/pages/admin-dashboard-page.tsx`, and backend docs/tests accordingly. |
| Expected benefit | Removes a known contract mismatch and makes dashboard behavior trustworthy before deeper monitoring changes. |
| Estimated complexity | Medium |
| Files affected | `src/monitor/pipeline_monitor.py`, `backend/app/routers/monitor.py`, `frontend-web/src/types/api.ts`, `frontend-web/src/pages/admin-dashboard-page.tsx`, `backend/app/README.md`, tests |
| Risk level | Medium |

### 4. Align `ChatResponse` Schema With Actual Serialized Output

| Field | Detail |
|---|---|
| Description | Either add `regeneration_count`, `language_validation`, and `monitoring` to `ChatResponse`, or stop including ignored fields from `RAGService._serialize_result`. Prefer explicit schema fields if the UI/admin tooling will use them. |
| Expected benefit | Clarifies API contract and prevents hidden data loss through Pydantic response filtering. |
| Estimated complexity | Low |
| Files affected | `backend/app/schemas/chat.py`, `src/serving/rag_service.py`, `frontend-web/src/types/api.ts`, tests |
| Risk level | Low to Medium |

### 5. Normalize Monitor Stage Names

| Field | Detail |
|---|---|
| Description | Fix the inconsistent `stage1_1_retrieval_dense` name or introduce a compatibility mapping if existing logs/dashboards rely on it. |
| Expected benefit | Simplifies dashboard aggregation and stage-based metrics queries. |
| Estimated complexity | Low |
| Files affected | `src/generation/rag_pipeline.py`, monitor tests, dashboard/tests if stage names are displayed |
| Risk level | Medium |

### 6. Remove High-Confidence Local Dead Code

| Field | Detail |
|---|---|
| Description | Remove `import math` from `src/evaluation/metrics.py`; remove unused frontend scaffold files only if no upcoming UI work needs them; remove generated artifacts from version control if tracked. |
| Expected benefit | Reduces noise without changing runtime behavior. |
| Estimated complexity | Low |
| Files affected | `src/evaluation/metrics.py`, `frontend-web/src/components/ui/card.tsx`, `frontend-web/src/components/ui/textarea.tsx`, `frontend-web/tsconfig.tsbuildinfo` |
| Risk level | Low |

### 7. Migrate Legacy Imports Before Removing Facades

| Field | Detail |
|---|---|
| Description | Change production and evaluation imports from compatibility modules to canonical modules, especially `src.generation.query_intent` to `src.query_intent` and `src.generation.llm.OllamaGenerator` to `src.generation.ollama.OllamaGenerator`. Do not delete facades yet. |
| Expected benefit | Makes eventual cleanup safe and reduces duplicate import surfaces. |
| Estimated complexity | Low to Medium |
| Files affected | `src/serving/rag_service.py`, `src/evaluation/generation_pipeline.py`, notebooks/docs as appropriate |
| Risk level | Low |

### 8. Add Prompt and Context Construction Tests

| Field | Detail |
|---|---|
| Description | Test `build_context` with empty docs, missing metadata, and long content; test `_build_answer_prompt` for `ko`, `en`, and `None`. |
| Expected benefit | Protects prompt behavior before resolving language-policy conflicts or adding context budgeting. |
| Estimated complexity | Low |
| Files affected | `src/generation/context.py`, `src/generation/rag_pipeline.py`, new tests such as `tests/test_generation_context.py`, `tests/test_prompt_construction.py` |
| Risk level | Low |

## Phase 2: Structural Improvements

### 1. Split `RAGService` Into Focused Components

| Field | Detail |
|---|---|
| Description | Extract intent classifier construction, pipeline cache/building, non-RAG answer handling, and response serialization from `src/serving/rag_service.py`. Keep public `answer_query` and `stream_answer` wrappers stable during migration. |
| Expected benefit | Reduces the highest fan-in/fan-out module and makes future changes easier to test. |
| Estimated complexity | High |
| Files affected | `src/serving/rag_service.py`, possible new modules under `src/serving/`, `tests/test_rag_service_query_intent.py` |
| Risk level | Medium to High |

### 2. Introduce Typed Pipeline DTOs

| Field | Detail |
|---|---|
| Description | Replace raw dictionaries passed between `RAGPipeline`, `RAGService`, and API schemas with dataclasses or Pydantic models for pipeline result, source item, classifier metadata, and monitoring metadata. |
| Expected benefit | Clarifies boundaries and prevents response/schema drift. |
| Estimated complexity | Medium |
| Files affected | `src/generation/rag_pipeline.py`, `src/serving/rag_service.py`, `backend/app/schemas/chat.py`, `frontend-web/src/types/api.ts`, tests |
| Risk level | Medium |

### 3. Move Retrieval Defaults Into Configuration

| Field | Detail |
|---|---|
| Description | Add settings for dense provider/model, dense `fetch_k`, dense `lambda_mult`, hybrid `rrf_k`, and BM25 cache path. Replace hard-coded `clova` / `bge-m3` in serving. |
| Expected benefit | Makes deployment behavior explicit and aligns code with documented environment configurability. |
| Estimated complexity | Medium |
| Files affected | `src/common/config.py`, `.env.example`, `.env.deploy.example`, `src/serving/rag_service.py`, `src/retrieval/factory.py`, `src/retrieval/dense.py`, `src/retrieval/hybrid.py`, docs/tests |
| Risk level | Medium |

### 4. Introduce Retriever Configuration Object

| Field | Detail |
|---|---|
| Description | Replace the long `build_retriever(...)` argument list with a `RetrieverConfig` dataclass or Pydantic model, with explicit validation for mode/provider/client mode. |
| Expected benefit | Makes retriever construction easier to reason about and reduces duplicated defaults across serving/evaluation/embedding paths. |
| Estimated complexity | Medium |
| Files affected | `src/retrieval/factory.py`, `src/serving/rag_service.py`, `src/evaluation/retrieval_pipeline.py`, `src/evaluation/generation_pipeline.py`, `notebooks/*`, tests |
| Risk level | Medium |

### 5. Split BM25 Module by Responsibility

| Field | Detail |
|---|---|
| Description | Separate user-dictionary extraction/IO, Kiwi tokenization, BM25 cache IO, and retriever construction currently concentrated in `src/retrieval/bm25.py`. |
| Expected benefit | Reduces a large, stateful module and makes cache/tokenizer behavior independently testable. |
| Estimated complexity | High |
| Files affected | `src/retrieval/bm25.py`, new modules such as `src/retrieval/bm25_cache.py`, `src/retrieval/kiwi_tokenizer.py`, tests |
| Risk level | Medium to High |

### 6. Encapsulate Kiwi State

| Field | Detail |
|---|---|
| Description | Move global mutable `Kiwi` instances and loaded dictionary tracking into an explicit tokenizer/service object. |
| Expected benefit | Reduces hidden state and makes repeated tests or multi-pipeline usage safer. |
| Estimated complexity | Medium |
| Files affected | `src/retrieval/bm25.py`, possibly new tokenizer module, tests |
| Risk level | Medium |

### 7. Share Knowledge Document Normalization

| Field | Detail |
|---|---|
| Description | Create a shared document/source normalization layer used by `knowledge_documents.py`, `RAGService._serialize_source`, and `src.common.schema`. Preserve router support for alternate field names. |
| Expected benefit | Reduces duplicate parsing and prevents UI source display from drifting from knowledge-document display. |
| Estimated complexity | Medium |
| Files affected | `backend/app/routers/knowledge_documents.py`, `src/common/schema.py`, `src/serving/rag_service.py`, tests |
| Risk level | Medium |

### 8. Resolve Prompt Language Policy

| Field | Detail |
|---|---|
| Description | Decide whether the app supports English answers. If not, remove/disable `language="en"` from API/frontend. If yes, update `RAG_PROMPT`, language validator, and response tests. |
| Expected benefit | Removes conflicting prompt instructions and makes behavior predictable. |
| Estimated complexity | Medium |
| Files affected | `backend/app/schemas/chat.py`, `frontend-web/src/types/api.ts`, `src/generation/prompts.py`, `src/generation/rag_pipeline.py`, `src/generation/language_validator.py`, tests |
| Risk level | Medium |

### 9. Add Prompt Versioning and Metadata

| Field | Detail |
|---|---|
| Description | Version the RAG prompt and include prompt version in monitoring/evaluation output. Keep prompt text in code or a controlled template module. |
| Expected benefit | Improves evaluation reproducibility and makes prompt changes auditable. |
| Estimated complexity | Low to Medium |
| Files affected | `src/generation/prompts.py`, `src/generation/rag_pipeline.py`, `src/monitor/pipeline_monitor.py`, `src/evaluation/generation_pipeline.py`, tests |
| Risk level | Low |

### 10. Clean Up Legacy Facades After Migration Window

| Field | Detail |
|---|---|
| Description | After imports and deployment commands are migrated, remove or formally deprecate `src/generation/query_intent.py`, `src/generation/llm.py`, `src/ollama_client.py`, and possibly `src/serving/app.py`. |
| Expected benefit | Removes duplicate import paths and reduces maintenance overhead. |
| Estimated complexity | Medium |
| Files affected | Compatibility modules, README, notebooks, tests, deployment configs |
| Risk level | Medium |

## Phase 3: Advanced Improvements

### 1. Concurrent Hybrid Retrieval

| Field | Detail |
|---|---|
| Description | Run dense and BM25 retrieval concurrently in hybrid mode, then fuse results when both finish. Use a simple executor or async strategy compatible with current libraries. |
| Expected benefit | Reduces hybrid latency when dense retrieval and BM25 can run independently. |
| Estimated complexity | Medium to High |
| Files affected | `src/retrieval/hybrid.py`, `src/generation/rag_pipeline.py`, monitor tests |
| Risk level | Medium |

### 2. Add Optional Reranker Interface

| Field | Detail |
|---|---|
| Description | Add a disabled-by-default reranker stage after retrieval/fusion and before context construction. Start with a no-op interface, then support simple term boosting or a model reranker later. |
| Expected benefit | Creates a clean extension point for retrieval quality improvements without rewriting retrieval. |
| Estimated complexity | High |
| Files affected | New `src/reranking/*` or `src/retrieval/rerank.py`, `src/generation/rag_pipeline.py`, config, monitor/evaluation tests |
| Risk level | High |

### 3. Add Context Budgeting

| Field | Detail |
|---|---|
| Description | Add token/character budgeting for context construction, with deterministic truncation and test coverage. |
| Expected benefit | Controls generation cost/latency and prevents oversized prompts as `k` grows. |
| Estimated complexity | Medium |
| Files affected | `src/generation/context.py`, `src/generation/rag_pipeline.py`, config, tests |
| Risk level | Medium |

### 4. Separate Generation, Validation, and Regeneration Metrics

| Field | Detail |
|---|---|
| Description | Split `stage_2_generation` into generation, validation, and optional regeneration stages. Preserve a backwards-compatible aggregate if the dashboard needs it. |
| Expected benefit | Makes latency bottlenecks and language-drift recovery visible. |
| Estimated complexity | Medium |
| Files affected | `src/generation/rag_pipeline.py`, `src/monitor/pipeline_monitor.py`, monitor endpoints, frontend dashboard, tests |
| Risk level | Medium |

### 5. Add Real Generation Timeout/Cancellation

| Field | Detail |
|---|---|
| Description | Replace post-hoc timeout marking with actual provider-level timeout/cancellation behavior where supported. |
| Expected benefit | Prevents slow or hung generation calls from tying up request workers indefinitely. |
| Estimated complexity | High |
| Files affected | `src/generation/openai_provider.py`, `src/common/ollama_client.py`, `src/generation/rag_pipeline.py`, config, tests |
| Risk level | High |

### 6. Move Monitoring to Persistent/External Storage

| Field | Detail |
|---|---|
| Description | Replace process-local monitor history with durable storage or external observability, while keeping current summary/recent endpoints stable. |
| Expected benefit | Preserves metrics across restarts and supports multi-instance deployments. |
| Estimated complexity | High |
| Files affected | `src/monitor/pipeline_monitor.py`, `backend/app/routers/monitor.py`, deployment config, frontend dashboard, tests |
| Risk level | High |

### 7. Replace Demo Auth With Production-Grade User Storage

| Field | Detail |
|---|---|
| Description | Replace `InMemorySession` and plain-text passwords with persistent users, password hashing, controlled admin provisioning, and role management. |
| Expected benefit | Removes a major deployment risk and makes auth behavior survive restarts. |
| Estimated complexity | High |
| Files affected | `backend/app/db/session.py`, `backend/app/db/models.py`, `backend/app/auth/*`, `backend/app/routers/auth.py`, config, tests, deployment migration docs |
| Risk level | High |

### 8. Add Web Retrieval Path for `needs_web`

| Field | Detail |
|---|---|
| Description | Implement a separate retrieval/generation path for current market/news/rate queries currently classified as `needs_web` and answered with a fixed fallback. |
| Expected benefit | Turns an existing routing category into real product capability. |
| Estimated complexity | High |
| Files affected | `src/query_intent/*`, new web retrieval modules, `src/serving/rag_service.py`, response schemas, frontend source rendering, tests |
| Risk level | High |

### 9. Improve Streaming Semantics

| Field | Detail |
|---|---|
| Description | Decide whether streaming should emit unvalidated model tokens, validated full-answer chunks, or delayed streamed final text. Then wire frontend chat to `/api/chat/stream` if useful. |
| Expected benefit | Clarifies streaming contract and can improve perceived latency. |
| Estimated complexity | High |
| Files affected | `backend/app/routers/chat.py`, `src/serving/rag_service.py`, `src/generation/rag_pipeline.py`, `frontend-web/src/pages/chat-page.tsx`, tests |
| Risk level | High |

### 10. Centralize Evaluation and Runtime Defaults

| Field | Detail |
|---|---|
| Description | Move duplicated provider/model defaults and HF-token validation from evaluation pipelines, embedding CLI, and retrieval factory into shared configuration helpers. |
| Expected benefit | Reduces drift between experiments, notebooks, and deployed behavior. |
| Estimated complexity | Medium |
| Files affected | `src/common/config.py`, `src/evaluation/retrieval_pipeline.py`, `src/evaluation/generation_pipeline.py`, `src/embedding/__main__.py`, `src/retrieval/factory.py`, notebooks |
| Risk level | Medium |

## Recommended Execution Order

1. Add tests first: chat contract, retrieval behavior, prompt/context behavior.
2. Fix schema/contract mismatches: monitor response and chat response extras.
3. Do low-risk cleanup and legacy import migration.
4. Move retrieval defaults into config and introduce typed retriever config.
5. Split `RAGService` and BM25 internals.
6. Tackle advanced latency/quality work: concurrent hybrid retrieval, context budgeting, optional reranking.
7. Address operational architecture: persistent monitoring and production auth.

## Roadmap Guardrails

- Keep public API behavior stable during Phase 1.
- Do not remove compatibility facades until imports, notebooks, docs, and deployment commands are migrated.
- Add tests before changing `RAGService`, `RAGPipeline`, `bm25.py`, or auth modules.
- Prefer small contract-preserving changes over broad rewrites.
- Treat retrieval quality as measurable: run retrieval/generation evaluations before and after structural changes.
