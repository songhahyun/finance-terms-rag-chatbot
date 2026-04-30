# finance-terms-rag-chatbot

금융 용어 문서를 기반으로 답변하는 RAG 챗봇 프로젝트입니다.

## 1) 설치

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

환경변수는 루트의 `.env`를 사용합니다.

주요 LLM 관련 환경변수:

```env
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="deepseek-r1:7b"
OLLAMA_SMALL_MODEL="deepseek-r1:1.5b"
OLLAMA_COMPLEX_MODEL="llama3.2:3b"
OLLAMA_TIMEOUT=300
```

- `OLLAMA_SMALL_MODEL`: Stage 1(키워드 추출), Stage 2-b(질의 분류), Stage 3 단순 정의 답변
- `OLLAMA_COMPLEX_MODEL`: Stage 3 복합 추론 답변

## 2) 백엔드 실행 (FastAPI)

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

레거시 호환 경로인 `src.serving.app:app`도 유지되지만, 새 엔트리포인트는 `backend.app.main:app`입니다.

기본 API 엔드포인트:
- `GET /health`
- `POST /auth/login`
- `POST /auth/signup`
- `POST /chat`
- `GET /monitor/summary`
- `GET /monitor/recent?limit=20`

## 3) 프론트엔드 실행 (Vite + React + TypeScript)

```bash
cd frontend-web
cp .env.example .env
npm install
npm run dev
```

기본적으로 `VITE_API_BASE_URL=http://localhost:8000` 백엔드와 연동합니다.

역할 기반 라우팅:
- `user`: `/chat`만 접근 가능
- `admin`: `/chat`, `/admin` 접근 가능

## 4) 인증 방식 (Admin, General User)
```
`.env` 파일에 아래 값을 추가할 경우 JWT 기반 인증 모듈이 활성화됩니다.

```env
API_AUTH_REQUIRED=true
API_JWT_SECRET=user-generated-password
API_JWT_ALGORITHM=HS256
API_ADMIN_USERNAME=admin
API_ADMIN_PASSWORD=admin123
API_ADMIN_ROLE=admin
```

인증 동작:
- `POST /auth/login`: 기존 사용자 로그인 후 bearer token 반환
- `POST /auth/signup`: 새 사용자 생성 후 bearer token 반환
- `/chat` 및 `/chat/stream`: 인증 필요
- `/monitor/summary`, `/monitor/recent`: 인증 필요, `admin` 역할만 허용

PowerShell에서 로그인 예시:

```powershell
$body = @{
  username = "admin"
  password = "admin123"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/auth/login" `
  -ContentType "application/json" `
  -Body $body
```

회원가입 예시:

```powershell
$body = @{
  username = "user1"
  password = "pass1234"
  role = "user"   # or "admin"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/auth/signup" `
  -ContentType "application/json" `
  -Body $body
```

주의:
- 현재 사용자 계정은 로컬 DB에 저장되지 않습니다.
- 회원가입한 사용자는 백엔드 프로세스가 실행 중일 때만 메모리에 유지됩니다.
- 백엔드 재시작 후에는 `.env`의 기본 admin 계정만 다시 생성됩니다.

## 5) Multi-agent 질의 처리 흐름

- Stage 1: 사용자 질의에서 키워드 추출 (`OLLAMA_SMALL_MODEL`)
- Stage 2-a: 키워드 + 원문 질의 기반 Hybrid RAG 검색
- Stage 2-b: 질의를 `simple_definition` / `complex_reasoning`으로 분류 (`OLLAMA_SMALL_MODEL`)
- Stage 2-a, 2-b는 병렬 실행
- Stage 3:
  - `simple_definition` -> `OLLAMA_SMALL_MODEL`로 답변 생성
  - `complex_reasoning` -> `OLLAMA_COMPLEX_MODEL`로 답변 생성

## 6) Stage 모니터링 로그 (Admin 계정만 접근 가능)

`/chat` 호출 시 stage별 실행 지표가 서버 메모리에 누적됩니다.

- `GET /monitor/summary`: stage별 `success_rate`, `avg_elapsed_sec`, `avg_throughput` 확인
- `GET /monitor/recent`: 최근 trace의 stage 상세(`success`, `elapsed_sec`, `throughput`, `error`) 확인

## 7) 프로젝트 디렉토리 구조

```text
finance-terms-rag-chatbot/
├─ data/
│  ├─ raw/                  # 원본 PDF
│  ├─ processed/            # 전처리 결과 (예: final_chunk.json)
│  └─ eval/                 # 평가 데이터셋 (예: golden_testset.csv)
├─ notebooks/               # 실험/분석 노트북
├─ backend/
│  └─ app/                  # FastAPI 전용 계층 (auth/JWT/RBAC/router/middleware/DB session)
├─ frontend-web/            # Vite + React + TypeScript 프론트엔드
├─ src/
│  ├─ serving/              # FastAPI와 RAG 파이프라인 사이 어댑터
│  │  ├─ app.py
│  │  └─ rag_service.py
│  ├─ ingestion/            # 데이터 파싱/정제
│  ├─ embedding/            # 임베딩/벡터스토어 구축
│  ├─ retrieval/            # BM25/Dense/Hybrid 검색기
│  ├─ generation/           # 프롬프트/답변 생성 파이프라인
│  ├─ evaluation/           # 평가 파이프라인 (RAGAS 포함)
│  └─ common/               # 공통 설정/스키마/IO
├─ chroma_clova/            # Chroma DB (clova)
├─ chroma_openai/           # Chroma DB (openai)
├─ chroma_local/            # Chroma DB (local)
├─ requirements.txt
└─ README.md
```

## 8) RAGAS 기반 Generation 평가 실행

RAGAS 평가 파이프라인 실행:

```bash
python -m src.evaluation --retrieval-mode hybrid
```

## 9) API 요청/응답 예시

`POST /chat`

요청 예시:

```json
{
  "question": "가산금리란 무엇인가요?",
  "mode": "hybrid",
  "k": 5,
  "language": "ko"
}
```

응답 예시:

```json
{
  "question": "가산금리란 무엇인가요?",
  "answer": "가산금리는 기준금리에 신용위험 등을 반영해 추가로 붙는 금리입니다.",
  "retrieved_ids": ["econ_0009", "econ_0123", "econ_0311"],
  "sources": [
    {
      "chunk_id": "econ_0009",
      "source": "한국은행 2020_경제금융용어 700선.pdf",
      "text": "가산금리: ... (문서 본문 일부)"
    },
    {
      "chunk_id": "econ_0123",
      "source": "한국은행 2020_경제금융용어 700선.pdf",
      "text": "기준금리와 스프레드 관련 설명 ... (문서 본문 일부)"
    }
  ]
}
