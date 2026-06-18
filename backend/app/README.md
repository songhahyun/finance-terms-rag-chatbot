# FastAPI Backend API

FastAPI application entrypoint is `backend.app.main:app`.

Run locally:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Most API routes are mounted under `/api`. The health check is mounted without the `/api` prefix.

## Authentication

When `API_AUTH_REQUIRED=true`, protected endpoints require a bearer token.

```http
Authorization: Bearer <access_token>
```

Tokens are returned by `/api/auth/login` and `/api/auth/signup`.

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Health check |
| `POST` | `/api/auth/login` | None | Authenticate an existing user |
| `POST` | `/api/auth/signup` | None | Register a user |
| `POST` | `/api/chat` | Bearer token when auth is enabled | Synchronous RAG chat |
| `POST` | `/api/chat/stream` | Bearer token when auth is enabled | Streaming RAG chat using NDJSON events |
| `GET` | `/api/knowledge-documents` | `user` or `admin` | List normalized knowledge documents |
| `GET` | `/api/monitor/summary` | `admin` | Return aggregated stage monitoring metrics |
| `GET` | `/api/monitor/recent` | `admin` | Return recent stage monitoring traces |

## GET /health

Returns a minimal health check payload.

Request:

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "ok"
}
```

## POST /api/auth/login

Authenticates an existing user and returns a bearer token.

Request:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Error example:

```json
{
  "detail": "Invalid credentials."
}
```

## POST /api/auth/signup

Creates a new user and returns a bearer token. `role` must be either `user` or `admin`.

Request:

```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user1",
    "email": "user1@example.com",
    "password": "pass1234",
    "role": "user"
  }'
```

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Error example:

```json
{
  "detail": "User already exists."
}
```

## POST /api/chat

Runs a synchronous chat request through the RAG pipeline.

Request:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "question": "가산금리란 무엇인가요?",
    "mode": "hybrid",
    "k": 5,
    "language": "ko"
  }'
```

Response:

```json
{
  "question": "가산금리란 무엇인가요?",
  "answer": "가산금리는 기준금리에 신용위험 등을 반영해 추가로 붙는 금리입니다.",
  "regeneration_count": 0,
  "language_validation": {
    "is_valid": true,
    "reason": "passed",
    "detected_issues": []
  },
  "retrieved_ids": ["econ_0009", "econ_0123", "econ_0311"],
  "sources": [
    {
      "chunk_id": "econ_0009",
      "source": "한국은행 2020_경제금융용어 700선.pdf",
      "text": "가산금리: ..."
    }
  ],
  "monitoring": {
    "query": "가산금리란 무엇인가요?",
    "stages": []
  },
  "intent": "needs_rag",
  "routing_reason": "matched_finance_terms",
  "matched_terms": ["가산금리"],
  "classifier": {
    "method": "rule",
    "confidence": 1.0
  }
}
```

Request field notes:

- `question`: required, non-empty string
- `mode`: retrieval mode, default `hybrid`
- `k`: number of retrieved chunks, `1` to `20`, default `5`
- `language`: `ko` or `en`, default `ko`

Response routing metadata:

- `intent`: query routing result, such as `needs_rag`, `needs_web`, `simple`, or `clarify`
- `routing_reason`: classifier reason code
- `matched_terms`: finance dictionary terms matched in the query
- `classifier`: classifier method and confidence

Example response for a query that requires real-time market information:

```json
{
  "question": "기준금리 오늘 얼마야?",
  "answer": "현재 시세, 뉴스, 환율처럼 실시간 정보가 필요한 질문입니다. 웹 조회 기능은 추후 개발 예정입니다.",
  "regeneration_count": 0,
  "language_validation": null,
  "retrieved_ids": [],
  "sources": [],
  "monitoring": {
    "query": "기준금리 오늘 얼마야?",
    "stages": []
  },
  "intent": "needs_web",
  "routing_reason": "matched_current_information_signal",
  "matched_terms": ["기준금리"],
  "classifier": {
    "method": "rule",
    "confidence": 1.0
  }
}
```

## POST /api/chat/stream

Runs the same RAG request as `/api/chat`, but streams newline-delimited JSON events.

Request:

```bash
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "question": "기준금리란 무엇인가요?",
    "mode": "hybrid",
    "k": 5,
    "language": "ko"
  }'
```

Token event:

```json
{"type":"token","content":"기준금리는 ..."}
```

Final event:

```json
{
  "type": "final",
  "question": "기준금리란 무엇인가요?",
  "answer": "기준금리는 중앙은행이 통화정책을 운영할 때 기준으로 삼는 금리입니다.",
  "regeneration_count": 0,
  "language_validation": {
    "is_valid": true,
    "reason": "passed",
    "detected_issues": []
  },
  "retrieved_ids": ["econ_0123"],
  "sources": [
    {
      "chunk_id": "econ_0123",
      "source": "한국은행 2020_경제금융용어 700선.pdf",
      "text": "기준금리: ..."
    }
  ],
  "monitoring": {
    "query": "기준금리란 무엇인가요?",
    "stages": []
  },
  "intent": "needs_rag",
  "routing_reason": "matched_finance_terms",
  "matched_terms": ["기준금리"],
  "classifier": {
    "method": "rule",
    "confidence": 1.0
  }
}
```

Error event:

```json
{"type":"error","message":"ValueError: `generator` is required."}
```

Response media type:

```text
application/x-ndjson
```

## GET /api/knowledge-documents

Returns normalized knowledge documents from the configured chunk JSON file.

Request:

```bash
curl http://localhost:8000/api/knowledge-documents \
  -H "Authorization: Bearer <access_token>"
```

Response:

```json
{
  "items": [
    {
      "id": "knowledge-1",
      "term": "가산금리",
      "explanation": "기준금리에 신용도 등의 차이에 따라 덧붙이는 금리를 말한다.",
      "relatedTerms": ["기준금리", "스프레드"]
    }
  ]
}
```

Error example:

```json
{
  "detail": "Knowledge document file not found: data/processed/final_chunk.json"
}
```

## GET /api/monitor/summary

Returns aggregated monitoring metrics. This endpoint requires an `admin` role.

Request:

```bash
curl http://localhost:8000/api/monitor/summary \
  -H "Authorization: Bearer <admin_access_token>"
```

Response:

```json
{
  "total_traces": 10,
  "stages": {
    "stage_1_retrieval_bm25": {
      "count": 10,
      "success_rate": 1.0,
      "avg_elapsed_sec": 0.02,
      "avg_throughput": 250.0
    }
  }
}
```

## GET /api/monitor/recent

Returns recent monitoring traces. This endpoint requires an `admin` role.

Trace `metadata` includes query intent classifier details, and `stages` includes
`stage_0_intent_classification` when a chat request has been classified.

Query parameters:

- `limit`: max number of traces to return, default `20`

Request:

```bash
curl "http://localhost:8000/api/monitor/recent?limit=5" \
  -H "Authorization: Bearer <admin_access_token>"
```

Response:

```json
{
  "items": [
    {
      "query": "가산금리란 무엇인가요?",
      "metadata": {
        "mode": "hybrid",
        "k": 5,
        "language": "ko",
        "intent": "needs_rag",
        "routing_reason": "matched_finance_terms",
        "matched_terms": ["가산금리"],
        "classifier_method": "rule",
        "confidence": 1.0
      },
      "stages": [
        {
          "name": "stage_0_intent_classification",
          "success": true,
          "elapsed_sec": 0.001,
          "throughput": 1000.0,
          "throughput_unit": "queries/sec",
          "error": null
        },
        {
          "name": "stage_1_retrieval_bm25",
          "success": true,
          "elapsed_sec": 0.02,
          "throughput": 250.0,
          "throughput_unit": "docs/sec",
          "error": null
        }
      ]
    }
  ]
}
```

## Common Auth Errors

Missing token:

```json
{
  "detail": "Missing bearer token."
}
```

Invalid or inactive user:

```json
{
  "detail": "User is not active."
}
```

Insufficient role:

```json
{
  "detail": "Insufficient role."
}
```
