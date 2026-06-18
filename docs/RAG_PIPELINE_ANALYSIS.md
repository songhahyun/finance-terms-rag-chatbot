# RAG Pipeline Analysis

This document analyzes the retrieval and generation path used by the deployed FastAPI backend. It is documentation-only; no code was changed.

## Executive Summary

The runtime RAG path is:

```text
POST /api/chat
  -> backend.app.routers.chat.chat
  -> src.serving.rag_service.answer_query
  -> RAGService.answer
  -> intent classification
  -> cached RAGPipeline(mode, k)
  -> retrieval
  -> context construction
  -> prompt construction
  -> generator execution
  -> language validation / optional regeneration
  -> API response serialization
```

The current production-like default is hybrid retrieval over:

- Dense retrieval: Chroma + Clova embeddings, using LangChain MMR retrieval.
- Sparse retrieval: Kiwi-tokenized BM25 over `data/processed/final_chunk.json`.
- Fusion: reciprocal rank fusion in `HybridRetriever`.

There is no separate learned reranker or cross-encoder reranker in the current code.

## 1. Query Flow

### Input

From `backend/app/schemas/chat.py`:

```json
{
  "question": "가산금리란 무엇인가요?",
  "mode": "hybrid",
  "k": 5,
  "language": "ko"
}
```

### Output

`ChatResponse` shape:

```json
{
  "question": "...",
  "answer": "...",
  "retrieved_ids": ["..."],
  "sources": [],
  "intent": "needs_rag",
  "routing_reason": "...",
  "matched_terms": [],
  "classifier": {
    "method": "rule",
    "confidence": 1.0
  }
}
```

`RAGService._serialize_result` also includes `regeneration_count`, `language_validation`, and `monitoring`, but `backend/app/schemas/chat.py` does not currently declare those fields on `ChatResponse`; Pydantic's default behavior ignores extras in the response model.

### Main Classes and Functions

- `backend.app.routers.chat.chat`
- `src.serving.rag_service.answer_query`
- `src.serving.rag_service.RAGRequest`
- `src.serving.rag_service.RAGService.answer`
- `src.query_intent.QueryIntentClassifier`
- `src.generation.rag_pipeline.RAGPipeline.answer`

### Configuration Values

- Request-level: `mode`, `k`, `language`.
- `API_AUTH_REQUIRED` controls whether auth is required before the route runs.
- `MONITOR_STAGE_LOG_PATH` configures stage logging.
- `MONITOR_STAGE3_TIMEOUT_SEC` marks slow generation stages as failed after completion.
- Intent classifier:
  - `INTENT_CLASSIFIER_PROVIDER`
  - `INTENT_CLASSIFIER_MODEL`
  - `INTENT_CLASSIFIER_TIMEOUT`
  - `INTENT_CLASSIFIER_CONFIDENCE_THRESHOLD`
  - `OPENAI_API_KEY`

### Potential Bottlenecks

- First request for a `(mode, k)` pair builds a retriever/generator pipeline.
- First BM25 setup may load/build user dictionary and BM25 index.
- Intent classification may call OpenAI for unresolved rule cases.
- The singleton `RAGService` uses a lock around pipeline cache creation; this is fine for startup but can serialize first-time pipeline creation.

### Refactoring Opportunities

- Make `RAGService` a thin orchestrator by extracting classifier setup, pipeline cache, and response serialization.
- Align `ChatResponse` schema with actual serialized result fields or stop producing ignored fields.
- Represent pipeline stages with explicit typed objects instead of raw dictionaries.
- Make intent routing and RAG execution independently testable at the API boundary.

## 2. Retriever Selection

### Input

`RAGService.get_pipeline(mode, k)` receives:

- `mode`: `"dense"`, `"bm25"`, or `"hybrid"`.
- `k`: requested number of final retrieved documents.

`RAGService._build_pipeline` calls:

```python
build_retriever(
    mode=mode,
    dense_provider="clova",
    dense_model_name="bge-m3",
    chunk_json_path=str(settings.default_chunk_json_path),
    k=k,
)
```

### Output

One of:

- LangChain dense retriever from `Chroma.as_retriever(...)`.
- LangChain `BM25Retriever`.
- Custom `HybridRetriever`.

### Main Classes and Functions

- `src.serving.rag_service.RAGService.get_pipeline`
- `src.serving.rag_service.RAGService._build_pipeline`
- `src.retrieval.factory.build_retriever`
- `src.retrieval.dense.build_dense_retriever`
- `src.retrieval.bm25.build_bm25_retriever`
- `src.retrieval.hybrid.HybridRetriever`

### Configuration Values

From `src/common/config.py`:

- `FINRAG_CHUNK_PATH`: default chunk JSON override.
- `CHROMA_CLIENT_MODE`: `"http"` or `"persistent"`.
- `CHROMA_HOST`
- `CHROMA_PORT`
- `CHROMA_SSL`
- `CHROMA_COLLECTION_NAME`
- Chroma local directories:
  - `chroma_clova_dir`
  - `chroma_openai_dir`
  - `chroma_local_dir`

Hard-coded in serving:

- `dense_provider="clova"`
- `dense_model_name="bge-m3"`

### Potential Bottlenecks

- Pipeline cache cardinality grows by `(mode, k)` and never evicts.
- Serving retrieval provider/model cannot be changed through environment variables alone.
- Hybrid mode constructs both dense and BM25 retrievers.
- `build_retriever` calls `get_settings()` each time, so settings are reloaded from `.env` repeatedly.

### Refactoring Opportunities

- Add explicit retrieval settings for dense provider/model, fetch size, MMR lambda, and hybrid RRF constant.
- Introduce a retriever configuration dataclass instead of a long factory argument list.
- Move serving-specific hard-coded defaults into configuration.
- Add bounded cache or startup initialization for expected modes.

## 3. Dense Retrieval

### Input

`build_dense_retriever` receives:

- `provider`: `"clova"`, `"openai"`, or `"local"`.
- `model_name`: serving uses `"bge-m3"`.
- `collection_name`: from `CHROMA_COLLECTION_NAME`.
- `client_mode`: from `CHROMA_CLIENT_MODE`.
- `persist_directory`: local Chroma path for persistent mode.
- `chroma_host`, `chroma_port`, `chroma_ssl`: for HTTP mode.
- `k`: final dense result count.
- `fetch_k`: default `20`.
- `lambda_mult`: default `0.7`.

Runtime query input:

- Plain user query string.

### Output

A LangChain retriever. At query time it returns a list of LangChain `Document` objects with:

- `page_content`
- `metadata.chunk_id`
- `metadata.term`
- `metadata.source`
- `metadata.page`
- `metadata.related_terms`

### Main Classes and Functions

- `src.retrieval.dense.build_dense_retriever`
- `src.embedding.chroma_builder.create_embedding_model`
- `langchain_chroma.Chroma`
- `chromadb.HttpClient`
- Provider embedding clients:
  - `langchain_naver.ClovaXEmbeddings`
  - `langchain_openai.OpenAIEmbeddings`
  - `langchain_huggingface.HuggingFaceEmbeddings`

### Configuration Values

- `CHROMA_CLIENT_MODE`
- `CHROMA_HOST`
- `CHROMA_PORT`
- `CHROMA_SSL`
- `CHROMA_COLLECTION_NAME`
- `CLOVASTUDIO_API_KEY` and `NCP_APIGW_API_KEY` indirectly through `ClovaXEmbeddings`.
- `OPENAI_API_KEY` indirectly through `OpenAIEmbeddings`.
- `HF_TOKEN` or `HUGGING_FACE_HUB_TOKEN` for local Hugging Face embeddings.

Dense retrieval search settings:

- `search_type="mmr"`
- `search_kwargs={"k": k, "fetch_k": 20, "lambda_mult": 0.7}`

### Potential Bottlenecks

- Embedding API call latency per query.
- Chroma HTTP network latency.
- Chroma collection availability and cold-start behavior.
- MMR fetches `fetch_k=20` candidates and then diversifies, which costs more than plain similarity search.
- Chroma/embedding client construction during first pipeline creation.

### Refactoring Opportunities

- Expose `fetch_k` and `lambda_mult` in configuration or request-level advanced settings.
- Add health checks for Chroma collection existence and embedding credentials.
- Add instrumentation for embedding latency vs vector-store latency; current dense stage combines both.
- Add graceful error messages for missing Chroma collection or provider credentials.
- Consider reusing embedding/vector-store clients across retrievers when possible.

## 4. BM25 Retrieval

### Input

Builder input:

- `chunk_json_path`: usually `data/processed/final_chunk.json`.
- `k`: number of documents.
- `preprocess_func`: default `tokenize_ko`.
- `index_path`: optional override.

Query-time input:

- Plain user query string.

### Output

LangChain `BM25Retriever` returning a list of `Document` objects.

Document construction uses `src.common.schema.Chunk.to_document`:

```text
page_content = "{term}\n\n{description}"
metadata = {
  chunk_id,
  term,
  source,
  page,
  related_terms
}
```

### Main Classes and Functions

- `src.retrieval.bm25.build_bm25_retriever`
- `src.retrieval.bm25.tokenize_ko`
- `src.retrieval.bm25._load_kiwi_user_dictionary`
- `src.retrieval.bm25._load_cached_bm25_retriever`
- `src.retrieval.bm25._write_cached_bm25_retriever`
- `src.common.schema.load_chunks`
- `src.common.schema.chunks_to_documents`
- `langchain_community.retrievers.BM25Retriever`
- `kiwipiepy.Kiwi`

### Configuration Values

- `FINRAG_CHUNK_PATH`
- Default chunk path: `data/processed/final_chunk.json`.
- Default user dictionary path: `data/processed/kiwi_user_dict.tsv`.
- Default BM25 cache path: `data/processed/bm25_index.pkl`.
- BM25 tokenization constants:
  - `KEEP_POS_PREFIXES = ("NN", "SL", "SN")`
  - `STOPWORDS`
  - `DOMAIN_WHITELIST`
  - `BAD_USER_DICT_SUFFIXES`

### Potential Bottlenecks

- Building BM25 from documents if cache is missing or invalid.
- Loading and mutating a global Kiwi instance.
- Generating `kiwi_user_dict.tsv` from all chunks when the dictionary file is missing.
- Pickle cache read/write on shared or read-only filesystems.
- Cache metadata invalidates on source mtime/size, not on all tokenizer/global-dictionary changes.

### Refactoring Opportunities

- Split `bm25.py` into dictionary generation, tokenization, cache IO, and retriever construction modules.
- Make BM25 cache location configurable for read-only deployments.
- Add a cache version field that changes when tokenizer logic changes.
- Avoid global mutable Kiwi state or encapsulate it in a retriever object.
- Add explicit startup diagnostics for cache hit/miss and dictionary load status.

## 5. Hybrid Retrieval

### Input

Builder input:

- Dense retriever.
- BM25 retriever.
- `k`: final number of fused documents.
- `rrf_k`: default `60`.

Query-time input:

- Plain user query string.

### Output

Top `k` `Document` objects after reciprocal rank fusion.

### Main Classes and Functions

- `src.retrieval.hybrid.HybridRetriever`
- `HybridRetriever.invoke`
- `HybridRetriever.retrieve_bm25`
- `HybridRetriever.retrieve_dense`
- `HybridRetriever.fuse`
- `HybridRetriever._rrf_merge`

### Configuration Values

- Request `k`.
- `rrf_k=60` hard-coded default in `HybridRetriever.__init__`.
- Dense config from dense retrieval.
- BM25 config from BM25 retrieval.

### Algorithm

Hybrid retrieval runs:

1. BM25 retrieval.
2. Dense retrieval.
3. Reciprocal rank fusion:

```text
score(chunk_id) += 1 / (rrf_k + rank)
```

Documents are deduplicated by `metadata["chunk_id"]`. Documents without a `chunk_id` are skipped.

### Potential Bottlenecks

- Hybrid latency is roughly BM25 latency plus dense latency because current execution is sequential.
- Dense API/vector-store latency dominates when remote embedding/Chroma calls are slow.
- No score calibration or detailed debug output is returned.
- Fusion uses only rank position, not raw BM25/vector scores.

### Refactoring Opportunities

- Run dense and BM25 retrieval concurrently for hybrid queries.
- Expose `rrf_k` in configuration.
- Include fusion debug metadata for evaluation and troubleshooting.
- Add tests for missing `chunk_id`, duplicate chunks, and tie behavior.
- Consider a second-stage reranker if answer quality requires it.

## 6. Reranking

### Current State

There is no separate reranking model or cross-encoder reranker.

Ranking mechanisms currently present:

- Dense retrieval uses Chroma MMR:
  - `search_type="mmr"`
  - `fetch_k=20`
  - `lambda_mult=0.7`
- Hybrid retrieval uses reciprocal rank fusion.

### Input

- Dense: vector-store candidate set from Chroma.
- Hybrid: dense ranked list and BM25 ranked list.

### Output

- Dense: MMR-diversified documents.
- Hybrid: RRF-fused top `k` documents.

### Main Classes and Functions

- `langchain_chroma.Chroma.as_retriever`
- `HybridRetriever._rrf_merge`

### Configuration Values

- Dense MMR values are fixed defaults in `build_dense_retriever`.
- Hybrid `rrf_k` is a constructor default.

### Potential Bottlenecks

- MMR increases dense retrieval work by fetching more candidates than final `k`.
- Without a learned reranker, final context quality depends heavily on first-stage retrieval.
- No reranking explanations or scores are exposed for analysis.

### Refactoring Opportunities

- Add optional reranker interface after retrieval/fusion and before context construction.
- Keep reranking disabled by default behind configuration.
- Record pre-rerank and post-rerank ids in monitoring/evaluation.
- Evaluate simple reranking first, such as exact term boost, before adding model latency.

## 7. Context Construction

### Input

List of retrieved LangChain `Document` objects.

Each expected document has:

- `page_content`: term and explanation text.
- `metadata.chunk_id`
- `metadata.source`

### Output

A single string:

```text
[문서 1] chunk_id=econ_0001, source=...
용어

설명...

[문서 2] chunk_id=econ_0002, source=...
...
```

### Main Classes and Functions

- `src.generation.context.build_context`
- `src.common.schema.Chunk.to_document`

### Configuration Values

- Indirectly affected by `k`; more documents create longer context.
- No token budget, truncation, or source prioritization config exists.

### Potential Bottlenecks

- Context size grows linearly with `k`.
- Long document text can increase generation latency and cost.
- No token counting or model-context-window protection.
- No source-level filtering after retrieval.

### Refactoring Opportunities

- Add context budget management by tokens or characters.
- Add structured context objects and a renderer, rather than only a string builder.
- Include page/source metadata consistently for citations.
- Add tests for empty docs, missing metadata, and long context truncation.

## 8. Prompt Construction

### Input

- `query`: original user question.
- `context`: string from `build_context`.
- `language`: optional `"ko"` or `"en"`.

### Output

Prompt string from `RAG_PROMPT`, plus optional language instruction:

- `"Respond in Korean."`
- `"Respond in English."`

### Main Classes and Functions

- `src.generation.prompts.RAG_PROMPT`
- `src.generation.rag_pipeline.RAGPipeline._build_answer_prompt`

### Configuration Values

- Prompt text is static source code.
- Request-level `language`.

### Potential Bottlenecks

- Static prompt is not versioned or externally configurable.
- There is potential instruction duplication: the base prompt says always answer in Korean, while `_build_answer_prompt` can append `"Respond in English."`.
- No prompt metadata/version is returned in monitoring.
- No guard against empty context besides the model instruction.

### Refactoring Opportunities

- Add prompt versioning for evaluation reproducibility.
- Resolve language-policy conflict before supporting English responses.
- Separate system/developer/user prompt roles for OpenAI instead of passing the whole prompt as one user message.
- Add tests for prompt construction and language options.

## 9. Generator Execution

### Input

Final prompt string.

Generator chosen by `src.generation.factory.build_generator(settings)`:

- `GENERATION_PROVIDER=ollama`
- `GENERATION_PROVIDER=openai`

### Output

Answer string plus validation metadata:

```json
{
  "answer": "...",
  "language_validation": {
    "is_valid": true,
    "reason": "...",
    "detected_issues": [],
    "regeneration_count": 0
  }
}
```

If language validation fails, the pipeline makes one regeneration attempt with `temperature=0.0` and a strict Korean instruction.

### Main Classes and Functions

- `src.generation.factory.build_generator`
- `src.generation.openai_provider.OpenAIGenerator`
- `src.generation.ollama.OllamaGenerator`
- `src.common.ollama_client.OllamaClient`
- `src.generation.rag_pipeline.RAGPipeline._generate_text`
- `src.generation.rag_pipeline.RAGPipeline._generate_validated_answer_result`
- `src.generation.language_validator.validate_answer_language`

### Configuration Values

OpenAI:

- `OPENAI_API_KEY`
- `OPENAI_GENERATION_MODEL`
- `GENERATION_TEMPERATURE`
- `GENERATION_MAX_TOKENS`

Ollama:

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_TIMEOUT`
- `OLLAMA_TEMPERATURE`
- `OLLAMA_TOP_P`
- `OLLAMA_REPEAT_PENALTY`
- `OLLAMA_KEEP_ALIVE`

Monitoring:

- `MONITOR_STAGE3_TIMEOUT_SEC`

### Potential Bottlenecks

- LLM latency is likely the largest single stage.
- Language validation can double generation cost when regeneration is triggered.
- The monitor timeout does not cancel generation; it marks the stage as failed after the call returns.
- OpenAI streaming exists, but validated generation currently gathers full text before emitting chunks.
- `_generate_text` catches `TypeError` for generator option compatibility, which can hide interface mismatches.

### Refactoring Opportunities

- Add explicit generator protocol/interface tests.
- Add real cancellation or request timeout support for generation.
- Split generation latency from validation/regeneration latency in monitoring.
- Use OpenAI role-separated messages rather than a single user prompt.
- Make regeneration policy configurable.

## 10. Response Formatting

### Input

`RAGPipeline.answer` result:

```python
{
    "query": query,
    "answer": answer,
    "language_validation": ...,
    "regeneration_count": ...,
    "retrieved_ids": [...],
    "contexts": docs,
    "monitoring": trace.to_dict(),
}
```

Classification metadata:

```python
classification.routing_metadata()
```

### Output

Serialized response dictionary passed into `ChatResponse`.

Source items contain:

- `chunk_id`
- `source`
- `text`
- `term`
- `explanation`
- `related_terms`

### Main Classes and Functions

- `src.serving.rag_service.RAGService._serialize_result`
- `src.serving.rag_service.RAGService._serialize_source`
- `src.serving.rag_service.RAGService._source_explanation`
- `src.serving.rag_service.RAGService._normalize_related_terms`
- `src.query_intent.types.QueryIntentResult.routing_metadata`
- `backend.app.schemas.chat.ChatResponse`

### Configuration Values

No direct configuration. Output is shaped by:

- Retrieved document metadata.
- Intent classifier result.
- Pydantic response model behavior.

### Potential Bottlenecks

- Source serialization is cheap, but it duplicates some knowledge-document normalization concerns.
- Extra generated fields may be discarded by `ChatResponse`, which can confuse API contract expectations.
- `related_terms` normalization assumes comma-separated strings or lists.
- `_source_explanation` assumes document text begins with `"{term}\n\n"`.

### Refactoring Opportunities

- Align backend response model with actual response content.
- Introduce explicit DTOs for pipeline result vs API response.
- Share source/document normalization with `knowledge_documents.py`.
- Add tests for source serialization edge cases.

## End-to-End Stage Table

| Stage | Input | Output | Main functions/classes | Key config | Bottlenecks | Refactoring opportunities |
|---|---|---|---|---|---|---|
| Query entry | `ChatRequest` | `RAGRequest` | `chat`, `answer_query` | `API_AUTH_REQUIRED` | Auth lookup, request validation | Keep route thin; add full API contract tests |
| Intent routing | Question | `QueryIntentResult` | `QueryIntentClassifier`, `RuleBasedQueryClassifier`, `OpenAILLMIntentClassifier` | classifier env vars, `OPENAI_API_KEY` | LLM fallback latency | Separate routing policy from service |
| Retriever selection | `mode`, `k` | Retriever object | `RAGService.get_pipeline`, `build_retriever` | Chroma/chunk settings | First-build latency | Config dataclass; cache lifecycle |
| Dense retrieval | Query | Dense docs | `build_dense_retriever`, Chroma retriever | Chroma + embedding provider config | Embedding and Chroma latency | Expose MMR config; add diagnostics |
| BM25 retrieval | Query | BM25 docs | `build_bm25_retriever`, `tokenize_ko` | chunk path, BM25 cache | Cache build, Kiwi tokenization | Split module; configurable cache |
| Hybrid fusion | Dense + BM25 docs | Fused docs | `HybridRetriever` | `k`, `rrf_k` | Sequential retrieval | Concurrent retrieval; debug scores |
| Reranking | Retrieved docs | Ranked docs | MMR/RRF only | fixed MMR/RRF defaults | No learned reranker | Optional reranker interface |
| Context | Docs | Context string | `build_context` | `k` | Long context | Token budget and truncation |
| Prompt | Query + context | Prompt string | `RAG_PROMPT`, `_build_answer_prompt` | `language` | Prompt conflict for English | Prompt versioning and role separation |
| Generation | Prompt | Answer + validation | `build_generator`, `OpenAIGenerator`, `OllamaGenerator`, validator | generation env vars | LLM latency, regeneration | Real timeout/cancellation; separate metrics |
| Response | Pipeline result | `ChatResponse` | `_serialize_result`, `_serialize_source` | response schema | Contract mismatch | Typed DTOs; schema alignment |

## Monitoring Notes

When a trace is present, `RAGPipeline._retrieve` records:

- `stage_1_retrieval_bm25` for hybrid BM25 branch.
- `stage1_1_retrieval_dense` for hybrid dense branch.
- `stage_1_retrieval_fusion` for hybrid fusion or any non-hybrid retriever invocation.
- `stage_2_generation` for generation and language validation.

`RAGService.answer` records:

- `stage_0_intent_classification`

The stage naming has one inconsistent pattern: `stage1_1_retrieval_dense` lacks the underscore after `stage`. This should be considered before dashboards or metric queries depend on stage names.

## Main Risks Before Refactoring

1. `RAGService` mixes orchestration, configuration, cache ownership, classification, and serialization.
2. Serving retrieval provider/model are hard-coded while environment variables imply broader configurability.
3. Hybrid retrieval is sequential and likely slower than necessary.
4. BM25 uses global mutable Kiwi state and pickle cache files.
5. Prompt language policy conflicts with the request schema allowing English.
6. Response serialization produces fields that are not declared by `ChatResponse`.
7. Monitor timeout marks slow generation only after completion.

## Suggested Test Coverage Before Changes

- Retriever factory behavior for all modes and invalid modes.
- Dense retriever construction for HTTP and persistent Chroma modes.
- BM25 cache hit/miss and cache invalidation behavior.
- Hybrid RRF ordering, deduplication, and missing `chunk_id` handling.
- Context construction with missing metadata and empty docs.
- Prompt construction for `ko`, `en`, and `None`.
- Generator factory for OpenAI and Ollama with mocked clients.
- Language-validation regeneration branch.
- API response schema including source serialization and ignored/extra fields.
- Monitoring stage names and metrics for dense, BM25, and hybrid paths.
