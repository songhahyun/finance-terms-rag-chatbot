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
GENERATION_PROVIDER=ollama
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="qwen2.5:7b-instruct"
OLLAMA_TIMEOUT=300
```

- `GENERATION_PROVIDER=ollama`: 로컬 개발용 Ollama 생성 모드
- `OLLAMA_MODEL`: 로컬 답변 생성 모델

## 2) 백엔드 실행 (FastAPI)

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

레거시 호환 경로인 `src.serving.app:app`도 유지되지만, 새 엔트리포인트는 `backend.app.main:app`입니다.

기본 API 엔드포인트:
- `GET /health`
- `POST /api/auth/login`
- `POST /api/auth/signup`
- `POST /api/chat`
- `GET /api/monitor/summary`
- `GET /api/monitor/recent?limit=20`

## 3) 프론트엔드 실행 (Vite + React + TypeScript)

```bash
cd frontend-web
cp .env.example .env
npm install
npm run dev
```

기본적으로 `VITE_API_BASE_URL=http://localhost:8000` 백엔드와 연동합니다. 프론트엔드 코드는 API 요청에 `/api` 경로를 자동으로 붙입니다.

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
- `POST /api/auth/login`: 기존 사용자 로그인 후 bearer token 반환
- `POST /api/auth/signup`: 새 사용자 생성 후 bearer token 반환
- `/api/chat` 및 `/api/chat/stream`: 인증 필요
- `/api/monitor/summary`, `/api/monitor/recent`: 인증 필요, `admin` 역할만 허용

PowerShell에서 로그인 예시:

```powershell
$body = @{
  username = "admin"
  password = "admin123"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/auth/login" `
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
  -Uri "http://localhost:8000/api/auth/signup" `
  -ContentType "application/json" `
  -Body $body
```

주의:
- 현재 사용자 계정은 로컬 DB에 저장되지 않습니다.
- 회원가입한 사용자는 백엔드 프로세스가 실행 중일 때만 메모리에 유지됩니다.
- 백엔드 재시작 후에는 `.env`의 기본 admin 계정만 다시 생성됩니다.

## 5) RAG 질의 처리 흐름

- Stage 1: 원문 질의 기반 Hybrid RAG 검색
- Stage 2: `OLLAMA_MODEL`(`qwen2.5:7b-instruct`)로 답변 생성

## 6) Stage 모니터링 로그 (Admin 계정만 접근 가능)

`/api/chat` 호출 시 stage별 실행 지표가 서버 메모리에 누적됩니다.

- `GET /api/monitor/summary`: stage별 `success_rate`, `avg_elapsed_sec`, `avg_throughput` 확인
- `GET /api/monitor/recent`: 최근 trace의 stage 상세(`success`, `elapsed_sec`, `throughput`, `error`) 확인

## 7) Generation 실험 Weave 로깅

W&B Weave에 generation 실험의 query별 입력, 검색 결과, 생성 답변, latency, retrieval metric을 기록합니다.

```python
from src.evaluation.generation_pipeline import run_generation_experiment

result_df = run_generation_experiment(
    experiment_name="generation_hybrid_clova_bge-m3",
    eval_csv_path="data/eval/testset/golden_testset_v2.csv",
    chunk_json_path="data/processed/final_chunk.json",
    retrieval_mode="hybrid",
    dense_provider="clova",
    dense_model_name="bge-m3",
    dense_collection_name="docs_clova",
    use_weave=True,
    weave_project="finance-terms-rag-generation",
    weave_experiment_group="generation_v2_2026-05-11",
    weave_log_prompt=True,
    weave_print_call_link=False,
)
```

## 8) 배포 가이드

배포 아키텍처:

```text
Frontend: Vercel
Backend API: Render Docker
Chroma DB: independent container/service
Generation: OpenAI API
Local mode: Ollama
Retrieval: backend uses Chroma HTTP client plus Clova embeddings
```

로컬 개발 모드는 Ollama를 사용합니다.

```env
GENERATION_PROVIDER=ollama
```

배포 모드는 OpenAI API를 사용합니다.

```env
GENERATION_PROVIDER=openai
OPENAI_API_KEY=replace-with-openai-key
OPENAI_GENERATION_MODEL=gpt-4o-mini
```

백엔드 Docker 배포:

1. GitHub Actions CI가 `Dockerfile.backend`로 백엔드 이미지를 빌드합니다.
2. `dev` 또는 `main` 브랜치 push 시 GHCR에 이미지를 게시합니다.
3. 이미지 태그는 `ghcr.io/<owner>/<repo>/backend:latest`와 `ghcr.io/<owner>/<repo>/backend:<commit-sha>`입니다.
4. Render는 GitHub 저장소에서 직접 빌드하지 않고 GHCR의 prebuilt image를 pull하도록 설정합니다.
5. GHCR package가 private이면 Render registry credentials를 설정하거나 Render가 접근 가능하도록 package visibility를 조정합니다.

Chroma 서비스:

1. Chroma는 백엔드 컨테이너와 분리된 독립 컨테이너/서비스로 실행합니다.
2. 백엔드는 `CHROMA_CLIENT_MODE=http`로 `CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_SSL`, `CHROMA_COLLECTION_NAME` 값을 사용해 Chroma HTTP 서비스에 연결합니다.
3. `chroma_clova` 데이터는 백엔드 이미지에 포함하지 않고 Chroma 서비스의 persisted data 또는 seed input으로 사용합니다.
4. 로컬 배포 구조 테스트는 `.env.deploy`를 만든 뒤 `docker compose --env-file .env.deploy up --build`로 실행할 수 있습니다.

Vercel 프론트엔드 설정:

- Framework Preset: Vite
- Root Directory: `frontend-web`
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment Variable: `VITE_API_BASE_URL=https://your-backend-url`

`VITE_API_BASE_URL`에는 백엔드 origin만 넣습니다. 프론트엔드 코드는 `/api` 경로를 자동으로 붙입니다.

필수 배포 환경변수:

```env
GENERATION_PROVIDER=openai
OPENAI_API_KEY=replace-with-openai-key
OPENAI_GENERATION_MODEL=gpt-4o-mini
GENERATION_TEMPERATURE=0.1
GENERATION_MAX_TOKENS=800

API_AUTH_REQUIRED=true
API_JWT_SECRET=replace-with-long-random-secret
API_ADMIN_USERNAME=admin
API_ADMIN_PASSWORD=replace-with-strong-password
API_ADMIN_ROLE=admin

CLOVASTUDIO_API_KEY=replace-with-clovastudio-key
NCP_APIGW_API_KEY=replace-with-ncp-apigw-key
CLOVA_EMBEDDING_MODEL=bge-m3

CHROMA_CLIENT_MODE=http
CHROMA_HOST=chroma
CHROMA_PORT=8000
CHROMA_SSL=false
CHROMA_COLLECTION_NAME=finance_clova

CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://your-vercel-app.vercel.app
MONITOR_STAGE3_TIMEOUT_SEC=120
```

배포 smoke test:

```bash
curl https://your-backend-url/health
curl https://your-backend-url/api/chat
```

`/api/chat`는 인증이 필요하므로 실제 질의 smoke test에는 로그인으로 받은 bearer token을 함께 전달합니다.

평가 결과를 보고할 때는 생성 모델을 분리해서 표기합니다.

```text
- Local baseline: Ollama llama3.2:3b
- Deployed generation model: OpenAI API
```

## 9) 프로젝트 디렉토리 구조

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
│  ├─ evaluation/           # retrieval/generation/RAGAS 평가 파이프라인
│  └─ common/               # 공통 설정/스키마/IO
├─ chroma_clova/            # Chroma DB (clova)
├─ chroma_openai/           # Chroma DB (openai)
├─ chroma_local/            # Chroma DB (local)
├─ requirements.txt
└─ README.md
```

## 10) RAGAS 기반 Generation 평가 실행

RAGAS 평가 파이프라인 실행:

```bash
python -m src.evaluation --generated-csv data/eval/outputs/generation_001_baseline/dense_clova_bge-m3.csv
```

## 11) API 요청/응답 예시

`POST /api/chat`

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
