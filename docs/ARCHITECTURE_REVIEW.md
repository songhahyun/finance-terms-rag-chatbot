# Architecture Review

This document describes the current architecture of `finance-terms-rag-chatbot` after deployment. It is intentionally observational: no application code was refactored while preparing this review.

## 1. High-Level Architecture Overview

### Runtime Topology

```text
Browser
  -> Vite React app (`frontend-web`)
  -> FastAPI backend (`backend.app.main:app`)
  -> RAG service adapter (`src.serving.rag_service`)
  -> Intent classifier, retriever, generator, monitor (`src/*`)
  -> Chroma vector store, BM25 index, OpenAI/Ollama/Clova providers
```

Deployment described by the repository:

- Frontend: Vercel-hosted Vite React app.
- Backend: Dockerized FastAPI service from `Dockerfile.backend`.
- Vector store: separate Chroma service/container, typically mounted from `chroma_clova`.
- Generation: OpenAI in deployment, Ollama for local development.
- Dense embeddings: Clova by default in serving code.
- Sparse retrieval: local BM25 index built from `data/processed/final_chunk.json`.

### Frontend Components

Entry points and application shell:

- `frontend-web/src/main.tsx`: mounts React, `BrowserRouter`, and `AuthProvider`.
- `frontend-web/src/app/app.tsx`: route table.
- `frontend-web/src/app/app-shell.tsx`: authenticated layout and navigation.
- `frontend-web/src/app/auth-context.tsx`: token storage, JWT payload parsing, login/signup/logout state.
- `frontend-web/src/app/route-guards.tsx`: protected route and role-based route guards.

Pages:

- `frontend-web/src/pages/login-page.tsx`: login/signup UI, stores the returned bearer token through `AuthProvider`.
- `frontend-web/src/pages/chat-page.tsx`: local conversation history, asks questions through `postChat`, renders answers and sources.
- `frontend-web/src/pages/knowledge-documents-page.tsx`: lists normalized knowledge documents from the backend.
- `frontend-web/src/pages/admin-dashboard-page.tsx`: calls monitor endpoints and renders table/charts.
- `frontend-web/src/pages/settings-page.tsx`: retrieval settings UI.

API and local state helpers:

- `frontend-web/src/lib/api.ts`: wraps `fetch`, appends `/api`, attaches bearer tokens for protected endpoints.
- `frontend-web/src/lib/retrieval-settings.ts`: stores retrieval mode/top-k in `localStorage`; maps frontend `"sparse"` to backend `"bm25"`.
- `frontend-web/src/lib/conversations.ts`: stores per-user recent conversations in `localStorage`.

### Backend Components

FastAPI layer:

- `backend/app/main.py`: creates the app, configures CORS, request logging, and routers.
- `backend/app/routers/health.py`: `GET /health`.
- `backend/app/routers/auth.py`: `POST /api/auth/login`, `POST /api/auth/signup`.
- `backend/app/routers/chat.py`: `POST /api/chat`, `POST /api/chat/stream`.
- `backend/app/routers/knowledge_documents.py`: `GET /api/knowledge-documents`.
- `backend/app/routers/monitor.py`: `GET /api/monitor/summary`, `GET /api/monitor/recent`.
- `backend/app/middleware/request_logging.py`: logs method, path, status, and latency.

Auth and user state:

- `backend/app/auth/jwt.py`: custom HMAC-SHA256 JWT create/decode.
- `backend/app/auth/deps.py`: resolves the current bearer-token user or anonymous guest when auth is disabled.
- `backend/app/auth/rbac.py`: role guard dependency.
- `backend/app/db/session.py`: process-local in-memory user store seeded with the configured admin account.
- `backend/app/db/models.py`: `UserRecord` dataclass.

Serving adapter:

- `src/serving/rag_service.py`: singleton `RAGService`, request object, intent routing, pipeline cache, response serialization, monitor access, streaming worker.
- `src/serving/app.py`: legacy compatibility re-export of `backend.app.main`.

### Retrieval Pipeline

The active serving retriever is built in `src.retrieval.factory.build_retriever`.

Modes:

- `dense`: `src/retrieval/dense.py` builds a LangChain Chroma retriever using MMR search.
- `bm25`: `src/retrieval/bm25.py` builds or loads a Kiwi-tokenized BM25 retriever from chunk JSON.
- `hybrid`: `src/retrieval/hybrid.py` runs dense and BM25 retrieval, then fuses rankings with reciprocal rank fusion.

Important retrieval behavior:

- `RAGService._build_pipeline` currently hard-codes `dense_provider="clova"` and `dense_model_name="bge-m3"` for serving.
- Chroma connection mode is controlled by `CHROMA_CLIENT_MODE`.
- HTTP mode uses `chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT, ssl=CHROMA_SSL)`.
- Persistent mode uses local Chroma persistence under `chroma_clova` by default.
- BM25 loads `data/processed/final_chunk.json` and persists `bm25_index.pkl` beside the chunk file.
- BM25 also creates/loads `kiwi_user_dict.tsv` from chunk contents when needed.

### Generation Pipeline

Primary modules:

- `src/generation/factory.py`: chooses `OllamaGenerator` or `OpenAIGenerator` from settings.
- `src/generation/rag_pipeline.py`: orchestrates retrieval, context building, prompt construction, answer generation, language validation, and monitoring.
- `src/generation/context.py`: converts retrieved documents into prompt context blocks.
- `src/generation/prompts.py`: RAG prompt template.
- `src/generation/language_validator.py`: rejects likely Chinese/Japanese drift and triggers one regeneration attempt.
- `src/generation/openai_provider.py`: OpenAI chat-completions generator with optional streaming.
- `src/generation/ollama.py` and `src/common/ollama_client.py`: Ollama generator and low-level HTTP client.

Serving generation flow:

1. `RAGPipeline.answer` retrieves documents.
2. `build_context` formats documents.
3. `_build_answer_prompt` fills `RAG_PROMPT` and appends language instruction.
4. `_generate_validated_answer_result` generates the answer.
5. `validate_answer_language` checks for language drift.
6. If validation fails, the pipeline regenerates once with a stricter instruction and temperature override.

### Authentication Flow

Login/signup:

1. Frontend calls `/api/auth/login` or `/api/auth/signup`.
2. `backend/app/routers/auth.py` checks or creates a user in `InMemorySession`.
3. `create_access_token` signs a JWT containing `sub`, `roles`, and `exp`.
4. Frontend stores the token in `localStorage` under `finance_rag_auth`.
5. Frontend decodes the token client-side to derive username and roles.

Protected requests:

1. Frontend sends `Authorization: Bearer <token>`.
2. `get_current_user` decodes the token and looks up the subject in `InMemorySession`.
3. If `API_AUTH_REQUIRED=false` and no token is present, the backend returns an anonymous guest user.
4. `require_roles` gates admin/user endpoints.

Current limitations:

- Users are not persisted outside the running process.
- Passwords are stored in plain text in memory.
- Signup allows users to choose `admin`.
- JWT `alg` is written from configuration but verification always uses HMAC-SHA256.

### Monitoring Flow

Modules:

- `src/monitor/pipeline_monitor.py`: in-memory trace history, stage metrics, optional file logger.
- `backend/app/routers/monitor.py`: admin-only monitor endpoints.
- `backend/app/middleware/request_logging.py`: coarse HTTP request logs separate from RAG stage logs.

Flow:

1. `RAGService.answer` starts a `QueryTrace`.
2. Intent classification runs as `stage_0_intent_classification`.
3. RAG queries record retrieval stages:
   - `stage_1_retrieval_bm25`
   - `stage1_1_retrieval_dense`
   - `stage_1_retrieval_fusion`
4. Generation records `stage_2_generation`.
5. Each `run_stage` records success, elapsed time, throughput, work units, timestamps, and error.
6. `PipelineMonitor` keeps a bounded in-memory deque and optionally logs stage events to `MONITOR_STAGE_LOG_PATH`.
7. Admin endpoints expose `summary()` and `recent()`.

Important note: the backend monitor response shape currently differs from the frontend TypeScript expectations in `frontend-web/src/types/api.ts`.

## 2. Request Lifecycle

### User Question to Final Response

Synchronous path currently used by the UI:

```text
ChatPage.ask()
  -> loadChatRetrievalPayload()
  -> postChat()
  -> POST /api/chat
  -> backend.app.routers.chat.chat()
  -> get_current_user()
  -> src.serving.rag_service.answer_query()
  -> get_rag_service().answer()
  -> QueryIntentClassifier.classify()
  -> RAGPipeline.answer() if intent is needs_rag
  -> retriever stages
  -> build_context()
  -> _build_answer_prompt()
  -> generator.generate()
  -> validate_answer_language()
  -> RAGService._serialize_result()
  -> ChatResponse
  -> ChatPage saves assistant message in localStorage
```

Detailed trace:

1. `ChatPage.ask` builds a user message and stores it in local conversation state.
2. `loadChatRetrievalPayload` reads `finrag.retrievalSettings`.
3. `postChat` sends `{ question, mode, k, language: "ko" }` to `/api/chat`.
4. `backend.app.routers.chat.chat` validates `ChatRequest`.
5. `get_current_user` validates bearer auth when configured.
6. `answer_query` creates a `RAGRequest` and delegates to the singleton `RAGService`.
7. `RAGService.answer` starts a monitor trace with mode, `k`, and language metadata.
8. `QueryIntentClassifier.classify` checks its cache.
9. `RuleBasedQueryClassifier.classify` runs current-info, simple, and finance-term rules.
10. If rules return a final non-RAG answer, `_answer_without_rag` returns immediately with no sources.
11. If rules cannot decide and OpenAI intent fallback is configured, `OpenAILLMIntentClassifier.classify` classifies unresolved simple/web/clarify cases.
12. If intent is `needs_rag`, `RAGService.get_pipeline(mode, k)` reuses or builds a cached `RAGPipeline`.
13. `RAGPipeline.answer` calls `_retrieve`.
14. Hybrid retrievers split into BM25, dense, and fusion monitor stages.
15. `build_context` formats retrieved documents.
16. `_build_answer_prompt` creates the final RAG prompt.
17. `_generate_validated_answer_result` calls the selected generator.
18. `validate_answer_language` validates Korean output and may trigger one regeneration.
19. `RAGPipeline.answer` returns answer, retrieved ids, contexts, validation data, and monitoring.
20. `RAGService._serialize_result` maps LangChain documents into API source items.
21. `ChatResponse` serializes the response.
22. `ChatPage` appends the assistant message and sources to local conversation history.

### Streaming Path

`POST /api/chat/stream` exists but the current React chat page does not use it.

```text
chat_stream()
  -> stream_answer()
  -> worker thread calls answer_query(..., on_chunk=_on_chunk)
  -> queue receives token/full-answer chunks
  -> StreamingResponse yields NDJSON token events
  -> final event contains the full serialized result
```

Provider caveat:

- `OpenAIGenerator` and `OllamaGenerator` can stream chunks.
- `RAGPipeline._generate_validated_answer_result` does not stream the initial answer directly because it first validates the full answer. On successful validation it emits the full answer through `on_chunk`; on regeneration it emits the regenerated full answer.

### Non-RAG Intent Responses

Intent routes that bypass retrieval:

- `simple`: fixed greeting/capability/unsupported answer or `_answer_simple_with_llm`.
- `needs_web`: fixed fallback answer because web retrieval is not implemented.
- `clarify`: fixed clarification answer.

These responses include no retrieved ids or sources but still include routing metadata and monitoring.

## 3. Dependency Map

### Major Module Relationships

```text
frontend-web/src/pages/*
  -> frontend-web/src/lib/api.ts
  -> backend/app/routers/*
  -> backend/app/auth/*
  -> src/serving/rag_service.py

src/serving/rag_service.py
  -> src/common/config.py
  -> src/query_intent/*
  -> src/retrieval/factory.py
  -> src/generation/factory.py
  -> src/generation/rag_pipeline.py
  -> src/monitor/pipeline_monitor.py

src/retrieval/factory.py
  -> src/retrieval/dense.py
  -> src/retrieval/bm25.py
  -> src/retrieval/hybrid.py
  -> src/embedding/chroma_builder.py
  -> src/common/schema.py

src/generation/rag_pipeline.py
  -> src/generation/context.py
  -> src/generation/prompts.py
  -> src/generation/language_validator.py
  -> generator from src/generation/factory.py

src/embedding/pipeline.py
  -> src/common/schema.py
  -> src/embedding/chroma_builder.py

src/ingestion/pipeline.py
  -> src/ingestion/parser.py
  -> src/ingestion/cleaning.py
  -> src/common/io.py

src/evaluation/*
  -> src/retrieval/factory.py
  -> src/generation/rag_pipeline.py
  -> src/evaluation/metrics.py
```

### Critical Entry Points

Runtime:

- Backend API: `backend.app.main:app`.
- Legacy backend import: `src.serving.app:app`.
- React app: `frontend-web/src/main.tsx`.
- RAG service singleton: `src.serving.rag_service.get_rag_service`.

Data and offline pipelines:

- Ingestion CLI/module: `src/ingestion/__main__.py`, `src.ingestion.pipeline.run_ingestion`.
- Embedding CLI/module: `src/embedding/__main__.py`, `src.embedding.pipeline.run_embedding`.
- Evaluation CLI/module: `src/evaluation/__main__.py`.

Critical internal classes/functions:

- `RAGService`: web/RAG boundary, pipeline cache, intent routing, serialization.
- `RAGPipeline`: retrieval + prompt + generation + validation.
- `QueryIntentClassifier`: rule/LLM routing facade with cache.
- `RuleBasedQueryClassifier`: deterministic finance/current/simple routing.
- `HybridRetriever`: dense/BM25 reciprocal-rank fusion.
- `PipelineMonitor`: trace lifecycle and aggregation.
- `InMemorySession`: runtime auth user store.

## 4. Configuration Analysis

### Backend and RAG Environment Variables

| Variable | Used in | Purpose |
|---|---|---|
| `GENERATION_PROVIDER` | `src/common/config.py`, `src/generation/factory.py`, `docker-compose.yml` | Selects `ollama` or `openai` generator. |
| `OLLAMA_BASE_URL` | `src/common/config.py`, `src/common/ollama_client.py` | Ollama API origin. |
| `OLLAMA_MODEL` | `src/common/config.py`, `src/generation/ollama.py` | Ollama model name. |
| `OLLAMA_TIMEOUT` | `src/common/config.py`, `src/common/ollama_client.py` | Ollama HTTP timeout. |
| `OLLAMA_TEMPERATURE` | `src/common/config.py` | Default Ollama temperature. |
| `OLLAMA_TOP_P` | `src/common/config.py` | Default Ollama top-p. |
| `OLLAMA_REPEAT_PENALTY` | `src/common/config.py` | Default Ollama repetition penalty. |
| `OLLAMA_KEEP_ALIVE` | `src/common/config.py`, `src/common/ollama_client.py` | Ollama model keep-alive option. |
| `OPENAI_API_KEY` | `src/common/config.py`, `src/generation/openai_provider.py`, `src/query_intent/llm_classifier.py` | Required for OpenAI generation and optional LLM intent fallback. |
| `OPENAI_GENERATION_MODEL` | `src/common/config.py`, `src/generation/factory.py` | OpenAI model for final answer generation. |
| `GENERATION_TEMPERATURE` | `src/common/config.py`, `src/generation/factory.py` | OpenAI answer temperature. |
| `GENERATION_MAX_TOKENS` | `src/common/config.py`, `src/generation/factory.py` | OpenAI answer max tokens. |
| `INTENT_CLASSIFIER_PROVIDER` | `src/common/config.py`, `src/serving/rag_service.py` | Enables OpenAI fallback classifier when set to `openai` and API key exists. |
| `INTENT_CLASSIFIER_MODEL` | `src/common/config.py`, `src/serving/rag_service.py` | OpenAI model for intent classification. |
| `INTENT_CLASSIFIER_TIMEOUT` | `src/common/config.py`, `src/serving/rag_service.py` | Intent classifier OpenAI timeout. |
| `INTENT_CLASSIFIER_CONFIDENCE_THRESHOLD` | `src/common/config.py`, `src/query_intent/llm_classifier.py` | Minimum LLM classifier confidence. |
| `CHROMA_CLIENT_MODE` | `src/common/config.py`, `src/retrieval/dense.py`, `docker-compose.yml` | `http` or `persistent` Chroma client mode. |
| `CHROMA_HOST` | `src/common/config.py`, `src/retrieval/dense.py`, `docker-compose.yml` | Chroma HTTP host. |
| `CHROMA_PORT` | `src/common/config.py`, `src/retrieval/dense.py`, `docker-compose.yml` | Chroma HTTP port. |
| `CHROMA_SSL` | `src/common/config.py`, `src/retrieval/dense.py`, `docker-compose.yml` | Whether Chroma HTTP uses SSL. |
| `CHROMA_COLLECTION_NAME` | `src/common/config.py`, `src/retrieval/factory.py` | Chroma collection used by serving retriever. |
| `CLOVASTUDIO_API_KEY` | Provider SDK via `langchain_naver.ClovaXEmbeddings` | Clova embedding API credential. |
| `NCP_APIGW_API_KEY` | Provider SDK via `langchain_naver.ClovaXEmbeddings` | Naver API gateway credential for Clova embeddings. |
| `CLOVA_EMBEDDING_MODEL` | `.env.example`, README | Documented embedding model, but serving code hard-codes `bge-m3` rather than reading this variable directly. |
| `HF_TOKEN` | `src/embedding/chroma_builder.py`, `src/evaluation/*` | Hugging Face token for local embedding provider. |
| `HUGGING_FACE_HUB_TOKEN` | `src/embedding/chroma_builder.py`, `src/evaluation/*` | Alternative Hugging Face token variable. |
| `DEFAULT_PDF_FILENAME` | `src/common/config.py` | Default raw PDF filename for ingestion-related defaults. |
| `FINRAG_CHUNK_PATH` | `src/common/config.py` | Overrides default chunk JSON path. |
| `MONITOR_STAGE_LOG_PATH` | `src/common/config.py`, `src/monitor/pipeline_monitor.py` | Optional file path for pipeline stage logs. |
| `MONITOR_STAGE3_TIMEOUT_SEC` | `src/common/config.py`, `src/generation/rag_pipeline.py` | Generation-stage timeout threshold for monitor marking. It records timeout status after completion; it does not cancel execution. |
| `WEAVE_PROJECT` | `src/evaluation/generation_pipeline.py` | Optional W&B Weave project override for generation experiments. |

### Backend API/Auth Variables

| Variable | Used in | Purpose |
|---|---|---|
| `API_AUTH_REQUIRED` | `backend/app/config.py`, `backend/app/auth/deps.py`, `docker-compose.yml` | Requires bearer auth when true. |
| `API_JWT_SECRET` | `backend/app/config.py`, `backend/app/auth/jwt.py` | HMAC signing secret. |
| `API_JWT_ALGORITHM` | `backend/app/config.py`, `backend/app/auth/jwt.py` | Written into JWT header. Verification currently always uses HMAC-SHA256. |
| `API_JWT_EXP_MINUTES` | `backend/app/config.py`, `backend/app/auth/jwt.py` | Token expiration duration. |
| `API_ADMIN_USERNAME` | `backend/app/config.py`, `backend/app/db/session.py` | Default seeded admin username. |
| `API_ADMIN_PASSWORD` | `backend/app/config.py`, `backend/app/db/session.py` | Default seeded admin password. |
| `API_ADMIN_ROLE` | `backend/app/config.py`, `backend/app/db/session.py` | Default seeded admin role. |
| `CORS_ALLOWED_ORIGINS` | `backend/app/config.py`, `backend/app/main.py` | CORS allowlist. |

### Frontend Variables

| Variable | Used in | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `frontend-web/src/lib/api.ts` | Backend origin. API helper appends `/api`. |

### Docker/Chroma Service Variables

| Variable | Used in | Purpose |
|---|---|---|
| `IS_PERSISTENT` | `docker-compose.yml` Chroma service | Enables Chroma persistence. |
| `PERSIST_DIRECTORY` | `docker-compose.yml` Chroma service | Chroma data directory inside the container. |

## 5. Technical Debt Analysis

### Duplicate Logic

- `src/generation/query_intent.py` is a compatibility re-export of `src/query_intent/*`. This is useful for migration but creates two import surfaces.
- `src/ollama_client.py` is a compatibility re-export of `src/common/ollama_client.py`.
- Retrieval evaluation and generation evaluation both carry local-provider resolution and Hugging Face token checks.
- Monitor response contracts are described in backend docs, backend code, and frontend TypeScript, but the shapes are not aligned.

### Large Classes and Modules

Largest files by line count include:

- `src/evaluation/ragas_pipeline.py`: 422 lines.
- `src/retrieval/bm25.py`: 352 lines.
- `src/evaluation/generation_pipeline.py`: 328 lines.
- `src/serving/rag_service.py`: 248 lines.
- `frontend-web/src/pages/chat-page.tsx`: 231 lines.
- `src/monitor/pipeline_monitor.py`: 220 lines.
- `frontend-web/src/pages/login-page.tsx`: 216 lines.
- `src/generation/rag_pipeline.py`: 197 lines.

The most important runtime concentration is `RAGService`: it owns classifier construction, pipeline construction, pipeline caching, non-RAG answers, response serialization, streaming, and monitor access.

### Tight Coupling

- `RAGService._build_pipeline` hard-codes Clova `bge-m3`, so serving cannot select OpenAI/local embeddings through environment variables alone.
- `RAGService` depends directly on concrete OpenAI intent and simple-answer generator classes.
- `RAGPipeline` depends on retrievers having LangChain-style `invoke` and optionally hybrid-specific `retrieve_bm25`, `retrieve_dense`, and `fuse` methods.
- `knowledge_documents.py` independently parses chunk JSON instead of sharing a document repository/normalizer with `src.common.schema`.
- Frontend auth trust is based on locally decoded JWT payload for route gating; backend still enforces roles, but the UI role model is tightly tied to token internals.
- Monitor API consumers assume a specific shape, but backend and frontend currently disagree.

### Dead Code Candidates

These are candidates only and need usage verification before removal:

- `src/generation/llm.py`: LangChain `ChatOpenAI` wrapper is not used by the serving path.
- `src/serving/app.py`: legacy entrypoint retained for compatibility.
- `src/ollama_client.py`: compatibility re-export.
- `/api/chat/stream`: implemented in backend but not used by current frontend.
- Login page forgot-password UI: simulates success locally and is not backed by an API.
- Several notebooks and evaluation reports are historical/experimental rather than runtime code.

### Over-Engineered Areas

- Custom JWT implementation duplicates standard library/package functionality and partially exposes algorithm configuration without algorithm agility.
- BM25 module performs candidate extraction, dictionary generation, TSV IO, Kiwi mutation, cache metadata, tokenization, and retriever construction in one module.
- Streaming endpoint complexity exists despite the current validated-generation flow emitting full answers after validation and the frontend not consuming it.
- Evaluation pipelines include substantial Weave logging machinery separate from runtime needs.

### Under-Engineered Areas

- Auth uses process-local in-memory users, plain-text passwords, and user-selectable admin role during signup.
- Monitoring is process-local and loses history on restart; deployed multi-instance behavior would fragment metrics.
- `MONITOR_STAGE3_TIMEOUT_SEC` only marks a completed stage as timed out; it does not enforce cancellation.
- No persistent conversation/session storage exists on the backend.
- No web retrieval implementation exists for `needs_web` queries.
- The admin dashboard includes static filters/model labels and appears mismatched with backend monitor response shapes.
- Runtime provider/model selection for retrieval is less configurable than the documented environment variables imply.

## 6. Risk Analysis

### Difficult to Modify Safely

- `src/serving/rag_service.py`: high fan-in/fan-out module. Changes can affect auth-visible API responses, intent routing, generation, monitoring, streaming, and source serialization.
- `src/generation/rag_pipeline.py`: central answer path. Changes may affect evaluation metrics, language validation, streaming behavior, and monitor metrics.
- `src/retrieval/bm25.py`: mutates a global Kiwi instance and writes cache/user dictionary files. Changes can affect retrieval quality and cache compatibility.
- `src/retrieval/factory.py`: serving and evaluation both depend on this factory; changing defaults can silently alter deployed behavior.
- `src/query_intent/rule_classifier.py`: small rule changes can reroute queries away from RAG or into fixed fallbacks.
- `backend/app/auth/*` and `backend/app/db/session.py`: current auth is simple but security-sensitive.
- `frontend-web/src/types/api.ts` and `frontend-web/src/pages/admin-dashboard-page.tsx`: monitor contract mismatch means fixes need backend/frontend coordination.
- `src/common/config.py` and `backend/app/config.py`: settings are cached or loaded at module/session initialization; changes may require restart and careful test isolation.

### Tests Needed Before Refactoring

Existing tests cover query intent, RAG service query intent behavior, language validation, Chroma HTTP retriever construction, chat response schema, and intent config. Before major refactoring, add or strengthen tests for:

- End-to-end `/api/chat` contract with auth enabled and disabled.
- `/api/chat` non-RAG paths: `simple`, `needs_web`, and `clarify`.
- `/api/chat/stream` NDJSON event order and error behavior.
- `RAGService` pipeline cache behavior by `(mode, k)`.
- Source serialization from LangChain documents, including `term`, `explanation`, and `related_terms`.
- Monitor API response shape and frontend-compatible transformation.
- Auth token expiration, invalid signatures, inactive users, and role enforcement.
- Signup role policy, especially preventing unauthorized admin creation if this moves beyond a demo.
- BM25 cache invalidation when `final_chunk.json` changes.
- Hybrid fusion ordering and duplicate handling.
- Generation provider selection for `openai` and `ollama` with mocked clients.
- Chroma HTTP vs persistent mode configuration.
- Knowledge document normalization against expected chunk JSON variants.

### Highest-Risk Current Gaps

1. Auth is not production-grade despite deployment settings enabling it.
2. Monitor backend response shape likely does not match frontend dashboard types.
3. Retrieval provider/model defaults are hard-coded in serving code.
4. `needs_web` classification is implemented, but web retrieval is not.
5. Runtime state is mostly in memory: users, monitor traces, frontend conversations.
6. The RAG path crosses many concrete provider dependencies, so refactoring without mocks will be brittle.

## Appendix: Current Test Surface

Current test files:

- `tests/test_chat_response_schema.py`
- `tests/test_chroma_http_retriever.py`
- `tests/test_language_validator.py`
- `tests/test_query_intent_config.py`
- `tests/test_query_intent.py`
- `tests/test_rag_service_query_intent.py`

These are a good base for intent and response-shape safety, but they do not yet fully protect auth, monitor contracts, streaming, full chat lifecycle, or retrieval quality.
