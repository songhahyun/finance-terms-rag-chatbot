# Deployment Guide

## 배포 아키텍처

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

## 백엔드 Docker 배포

1. GitHub Actions CI가 `Dockerfile.backend`로 백엔드 이미지를 빌드합니다.
2. `dev` 또는 `main` 브랜치 push 시 GHCR에 이미지를 게시합니다.
3. 이미지 태그는 `ghcr.io/<owner>/<repo>/backend:latest`와 `ghcr.io/<owner>/<repo>/backend:<commit-sha>`입니다.
4. Render는 GitHub 저장소에서 직접 빌드하지 않고 GHCR의 prebuilt image를 pull하도록 설정합니다.
5. GHCR package가 private이면 Render registry credentials를 설정하거나 Render가 접근 가능하도록 package visibility를 조정합니다.

## Chroma 서비스

1. Chroma는 백엔드 컨테이너와 분리된 독립 컨테이너/서비스로 실행합니다.
2. 백엔드는 `CHROMA_CLIENT_MODE=http`로 `CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_SSL`, `CHROMA_COLLECTION_NAME` 값을 사용해 Chroma HTTP 서비스에 연결합니다.
3. `chroma_clova` 데이터는 백엔드 이미지에 포함하지 않고 Chroma 서비스의 persisted data 또는 seed input으로 사용합니다.
4. 로컬 배포 구조 테스트는 `.env.deploy`를 만든 뒤 `docker compose --env-file .env.deploy up --build`로 실행할 수 있습니다.

## Vercel 프론트엔드 설정

- Framework Preset: Vite
- Root Directory: `frontend-web`
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment Variable: `VITE_API_BASE_URL=https://your-backend-url`

`VITE_API_BASE_URL`에는 백엔드 origin만 넣습니다. 프론트엔드 코드는 `/api` 경로를 자동으로 붙입니다.

## 필수 배포 환경변수

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

## 배포 Smoke Test

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
