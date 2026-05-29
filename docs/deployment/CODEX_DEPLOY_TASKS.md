# CODEX_DEPLOY_TASKS.md

## Goal

Prepare this repository for portfolio-grade deployment.

The project is a finance RAG chatbot built with Python/FastAPI backend, Vite/React frontend, Chroma vector DB, and local Ollama-based generation. For deployment, do **not** use Ollama as the answer generation model because the deployment environment has no GPU. Instead, add support for API-based generation using **OpenAI API**, while preserving the existing Ollama local development mode.

Target deployment architecture:

```text
Frontend: Vercel
Backend API: Render using Docker
Chroma DB: independent Docker service/container with persisted chroma_clova data
Generation LLM: OpenAI API
Retrieval: backend connects to Chroma over HTTP and uses Clova embeddings
Local development: Ollama remains supported
```

---

## Deployment Decisions

- Implement only `openai` as the API-based deployment generation provider. Do not implement DeepSeek for this deployment pass.
- Use the official OpenAI Python SDK for `OpenAIGenerator`.
- Deploy the backend to Render and the frontend to Vercel.
- Run Chroma DB as an independent container/service. The backend must not use embedded/persistent local Chroma in deployment mode.
- The backend must connect to Chroma through HTTP only, for example with `chromadb.HttpClient`.
- Keep `chroma_clova` as Chroma server persisted data or seed input, but do not bake it into the backend Docker image.
- Use the Clova embedding API for deployed retrieval. Do not switch deployed retrieval to local or OpenAI embeddings in this pass.
- Keep authentication required in deployment with `API_AUTH_REQUIRED=true`.
- On backend startup, automatically create the default admin user from environment variables. The default local credentials are `admin` / `admin123`; production must override the password.
- The final Vercel frontend domain is not known until after Dockerfile creation, Render service creation, and Vercel project creation. Before starting the CORS/Vercel-domain-specific update, ask the user for the actual Vercel domain.
- Add a global `/api` prefix in `backend/app/main.py` for application API routers, and match frontend API URL handling to that prefix.
- Add `.env.deploy.example`. The user will create the real `.env.deploy` file manually from that example.
- Maintain a separate `requirements.deploy.txt` for backend deployment runtime dependencies. Keep local development, notebook, local embedding, and evaluation-only dependencies in `requirements.txt`.
- Do not include unused UI dependencies such as Streamlit in `requirements.txt` unless the Streamlit app is restored.
- Make Docker image build a required GitHub Actions CI check.
- Use `npm ci` in CI.
- Work and commits stay on the local `dev` branch, while the existing upstream configuration may remain `origin/main`.
- Use the existing `docs/deployment/DEPLOYMENT_NOTES.md` file for deployment notes.
- Group related task changes into fewer commits instead of committing after every individual task.
- Verification should use mock/import/smoke checks only. Do not call real OpenAI APIs during automated checks.

---

## Global Rules

- Work on the `dev` branch.
- Implement tasks sequentially from Task 01 to Task 12.
- Keep existing local Ollama behavior working.
- Do not hard-code API keys, secrets, URLs, or passwords.
- Use environment variables for all deployment-specific configuration.
- Do not remove existing RAG, retriever, monitoring, or auth functionality unless it is clearly dead code.
- Prefer small, explicit changes over large rewrites.
- After each task, run relevant tests or at least import/smoke checks.
- Group related completed tasks into fewer commits. Use the specified commit messages as guidance for commit scope.
- Reference GitHub issue `#11` in every deployment-related commit message, for example: `feat: add configurable generation providers (#11)`.
- Do not push to remote. The user will push manually.

---

## Task 01 — Inspect Current Backend and Generation Flow

### Objective

Understand the current generation pipeline before modifying it.

### Actions

1. Inspect the current backend entrypoint.
2. Inspect the current RAG service and generation classes.
3. Identify where `OllamaGenerator` is instantiated.
4. Identify how settings are currently loaded.
5. Identify which routes call the RAG pipeline.
6. Identify how Chroma is currently instantiated and which local persist directory or collection is used.

### Expected Output

Add a short section to `docs/deployment/DEPLOYMENT_NOTES.md`:

```md
## Current Generation Flow

- Backend entrypoint:
- RAG service:
- Current generator:
- Current settings source:
- Chat endpoint:
- Current Chroma client mode:
- Current Chroma collection/persist path:
```

### Acceptance Criteria

- No application behavior is changed.
- `docs/deployment/DEPLOYMENT_NOTES.md` exists.
- The notes accurately describe the current generation flow.

### Commit Message

```text
chore: document current generation flow
```

---

## Task 02 — Add Provider-Based Generation Interface

### Objective

Add a clean generation provider abstraction so the app can switch between Ollama and OpenAI.

### Actions

1. Create or refactor generation code under an appropriate module, for example:

```text
src/generation/
  __init__.py
  base.py
  ollama.py
  openai_provider.py
  factory.py
```

2. Define a minimal common interface such as:

```python
class BaseGenerator:
    def generate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError
```

3. Preserve the existing `OllamaGenerator` behavior.
4. Add `OpenAIGenerator` using the official OpenAI Python client.
5. Do not implement DeepSeek in this deployment pass.

### Required Environment Variables

```env
GENERATION_PROVIDER=ollama|openai
OPENAI_API_KEY=
OPENAI_GENERATION_MODEL=gpt-4o-mini
GENERATION_TEMPERATURE=0.1
GENERATION_MAX_TOKENS=800
```

### Acceptance Criteria

- `ollama` and `openai` providers can be selected by env var.
- Missing API keys produce clear errors.
- Existing local Ollama mode still works.
- No API key is committed.
- DeepSeek is not required or implemented.

### Commit Message

```text
feat: add configurable generation providers
```

---

## Task 03 — Refactor RAG Service to Use Generation Factory

### Objective

Remove direct coupling between the RAG service and `OllamaGenerator`.

### Actions

1. Replace direct `OllamaGenerator(...)` instantiation in the RAG service with a provider factory, for example:

```python
from src.generation.factory import build_generator

generator = build_generator(settings)
```

2. Ensure the selected generator is used for answer generation.
3. Keep existing prompt construction, retrieval flow, and response schema unchanged unless a change is required for compatibility.

### Acceptance Criteria

- RAG service does not directly instantiate `OllamaGenerator`.
- `GENERATION_PROVIDER=ollama` works locally.
- `GENERATION_PROVIDER=openai` works when `OPENAI_API_KEY` is set.
- DeepSeek provider support is out of scope for this deployment pass.

### Commit Message

```text
refactor: decouple rag service from ollama generator
```

---

## Task 04 — Update Configuration and Environment Templates

### Objective

Make deployment configuration explicit and reproducible.

### Actions

1. Update backend config/settings to include generation provider settings.
2. Update backend config/settings to include Chroma HTTP client settings.
3. Add or update `.env.example`.
4. Add `.env.deploy.example` for deployment-specific configuration.
5. Add `requirements.deploy.txt` for deployment runtime dependencies.
6. Keep evaluation-only and local embedding dependencies such as `ragas`, `bert-score`, `datasets`, `sentence-transformers`, and `langchain-huggingface` out of `requirements.deploy.txt`.
7. Ensure `.env`, API keys, local DB files, logs, and secrets are ignored by git.

### Required `.env.deploy.example` Content

```env
# Generation provider
GENERATION_PROVIDER=openai
OPENAI_API_KEY=replace-with-openai-key
OPENAI_GENERATION_MODEL=gpt-4o-mini

# Generation parameters
GENERATION_TEMPERATURE=0.1
GENERATION_MAX_TOKENS=800

# Backend auth
API_AUTH_REQUIRED=true
API_JWT_SECRET=replace-with-long-random-secret
API_ADMIN_USERNAME=admin
API_ADMIN_PASSWORD=replace-with-strong-password
API_ADMIN_ROLE=admin

# Retrieval embeddings
CLOVASTUDIO_API_KEY=replace-with-clovastudio-key
NCP_APIGW_API_KEY=replace-with-ncp-apigw-key
CLOVA_EMBEDDING_MODEL=bge-m3

# Chroma HTTP service
CHROMA_CLIENT_MODE=http
CHROMA_HOST=chroma
CHROMA_PORT=8000
CHROMA_SSL=false
CHROMA_COLLECTION_NAME=finance_clova

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://your-vercel-app.vercel.app

# Monitoring / timeout
MONITOR_STAGE3_TIMEOUT_SEC=120
```

### Acceptance Criteria

- Environment variable names are documented.
- Backend settings expose Chroma HTTP connection values.
- Deployment runtime dependencies are documented in `requirements.deploy.txt`.
- Secrets are not committed.
- `.gitignore` protects local secrets and generated artifacts.

### Commit Message

```text
chore: add deployment environment templates
```

---

## Task 05 — Make CORS Deployment-Ready

### Objective

Allow the deployed Vercel frontend to call the deployed backend safely.

### Actions

1. Replace hard-coded local-only CORS origins with env-based origins.
2. Parse `CORS_ALLOWED_ORIGINS` as a comma-separated list.
3. Keep localhost origins available for local development.
4. Avoid using `allow_origins=["*"]` when credentials/auth are enabled.

### Example Behavior

```env
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://your-project.vercel.app
```

### Acceptance Criteria

- CORS works locally.
- CORS can be configured for Vercel via env var.
- Authenticated requests remain supported.

### Commit Message

```text
fix: configure cors origins via environment
```

---

## Task 06 — Add Global API Router Prefix

### Objective

Namespace backend application routes under `/api` so the deployed frontend and backend have a clear API boundary.

### Actions

1. Update `backend/app/main.py` so application API routers are registered with a global `/api` prefix.
2. Keep the health endpoint available at `/health` for Render/Docker health checks.
3. Ensure existing route-specific prefixes remain unchanged under the global prefix.
4. Update frontend API calls or base URL handling so requests target the new `/api` routes consistently.

### Expected Route Behavior

```text
GET  /health
POST /api/auth/login
POST /api/chat
POST /api/chat/stream
GET  /api/knowledge-documents
GET  /api/monitor/summary
```

### Acceptance Criteria

- `/health` still responds without the `/api` prefix.
- Chat, auth, knowledge document, and monitor routes are available under `/api`.
- Frontend requests use the `/api` route namespace without requiring users to put `/api` into `VITE_API_BASE_URL`.
- Route changes are reflected in deployment notes and README deployment docs.

### Commit Message

```text
refactor: add api route namespace
```

---

## Task 07 — Split Chroma into an HTTP Service

### Objective

Change retrieval architecture so the FastAPI backend never opens a local embedded Chroma store in deployment. Chroma must run as an independent service, and the backend must use an HTTP client only.

### Actions

1. Inspect the current dense retriever and embedding builder modules:

```text
src/retrieval/dense.py
src/embedding/chroma_builder.py
src/common/config.py
```

2. Add Chroma client mode/configuration with a deployment default of HTTP:

```env
CHROMA_CLIENT_MODE=http
CHROMA_HOST=chroma
CHROMA_PORT=8000
CHROMA_SSL=false
CHROMA_COLLECTION_NAME=finance_clova
```

3. Refactor retrieval code so deployed backend retrieval creates a `chromadb.HttpClient` and passes it to LangChain Chroma, or uses the equivalent supported HTTP client path.
4. Keep local embedded/persisted Chroma support only for local development if needed, guarded by explicit config such as `CHROMA_CLIENT_MODE=persistent`.
5. Remove any deployment dependency on `persist_directory` inside the backend container.
6. Ensure collection name, host, port, and SSL are environment-driven.
7. Add an import/smoke check that verifies the HTTP client path can be constructed without calling external embedding or generation APIs.
8. Document in `docs/deployment/DEPLOYMENT_NOTES.md` that Chroma is a separate HTTP service.

### Acceptance Criteria

- Backend deployment code path uses `chromadb.HttpClient` or equivalent HTTP-only Chroma client.
- Backend deployment does not instantiate embedded/persistent Chroma.
- Retrieval still uses Clova embeddings for query embedding.
- Local development can still use the existing local Chroma artifact when explicitly configured.
- Chroma connection settings are documented in `.env.deploy.example`.

### Commit Message

```text
refactor: use chroma http client for retrieval
```

---

## Task 08 — Add Backend Dockerfile and Docker Ignore

### Objective

Make the FastAPI backend deployable on Docker-compatible platforms.

### Actions

1. Add `Dockerfile.backend` at repository root.
2. Add or update `.dockerignore`.
3. Ensure the backend runs with:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

4. Set `PYTHONPATH=/app` inside the container.
5. Avoid copying local `.env`, logs, virtualenvs, caches, and unnecessary Chroma artifacts unless explicitly required.
6. Do not copy `chroma_clova`, `chroma_openai`, `chroma_local`, or other Chroma data directories into the backend image.
7. Install Python packages from `requirements.deploy.txt`, not the local development `requirements.txt`.
8. Ensure the backend image contains only application code and runtime dependencies needed to connect to Chroma over HTTP.

### Suggested Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.deploy.txt .
RUN pip install --no-cache-dir -r requirements.deploy.txt

COPY . .

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Acceptance Criteria

- Docker image builds successfully.
- Backend container starts successfully.
- `/health` endpoint responds.
- Backend image does not contain local Chroma DB artifacts.
- Backend image does not install local-only or evaluation-only packages such as `sentence-transformers`, `langchain-huggingface`, `ragas`, `bert-score`, `datasets`, `streamlit`, or `weave`.

### Commit Message

```text
build: add backend dockerfile
```

---

## Task 09 — Add Local Docker Compose for Backend and Chroma Testing

### Objective

Allow local Docker-based testing of the deployment architecture without requiring Ollama.

### Actions

1. Add `docker-compose.yml` for local backend testing.
2. Add `.env.deploy.example` as a reference. Do not commit the real `.env.deploy` file.
3. Configure compose to load `.env.deploy` when the user creates it locally.
4. Add a `chroma` service using a Chroma server image.
5. Mount `chroma_clova` or a named volume containing its copied data into the Chroma service, not into the backend service.
6. Configure the backend service with `CHROMA_HOST=chroma` and `CHROMA_PORT=8000`.
7. Add `depends_on` so the backend starts after the Chroma service is requested.
8. Do not include an Ollama service as the default deployment path.
9. Optionally add a commented local Ollama service for development only.

### Expected Services

```text
backend
chroma
```

Optional commented service:

```text
ollama-local-dev-only
```

### Acceptance Criteria

- `docker compose up --build` starts the backend.
- `docker compose up --build` starts an independent Chroma service.
- Backend reaches Chroma through the compose service name, not a local filesystem path.
- The backend can use OpenAI when `OPENAI_API_KEY` is provided.
- Ollama is not required for deployment mode.

### Commit Message

```text
build: add docker compose for deployment testing
```

---

## Task 10 — Prepare Vercel Frontend Configuration

### Objective

Make the Vite/React frontend deployable to Vercel and configurable via backend URL.

### Actions

1. Inspect `frontend-web` environment variable usage.
2. Ensure frontend API base URL comes from:

```env
VITE_API_BASE_URL=https://your-backend-url
```

3. Add `frontend-web/.env.example` if missing.
4. Add Vercel deployment notes to `docs/deployment/DEPLOYMENT_NOTES.md`.
5. Do not hard-code Render URLs.
6. Before setting the production Vercel origin in backend CORS docs/config, ask the user for the actual Vercel domain.
7. Ensure `VITE_API_BASE_URL` contains only the deployed backend base origin, while frontend requests append the `/api` route namespace in code.

### Vercel Settings to Document

```text
Framework Preset: Vite
Root Directory: frontend-web
Build Command: npm run build
Output Directory: dist
Environment Variable: VITE_API_BASE_URL
```

### Acceptance Criteria

- Frontend still works locally with local backend.
- Frontend can target deployed backend via `VITE_API_BASE_URL`.
- Deployment notes include exact Vercel settings.

### Commit Message

```text
docs: add vercel frontend deployment config
```

---

## Task 11 — Add GitHub Actions CI

### Objective

Add basic CI to catch broken backend/frontend changes before deployment.

### Actions

Create `.github/workflows/ci.yml` with jobs for:

1. Backend Python checks:
   - install deployment dependencies from `requirements.deploy.txt`
   - run import check or tests if available
   - run `python -m compileall backend src`

2. Frontend checks:
   - install npm dependencies in `frontend-web` with `npm ci`
   - run build

3. Required Docker check:
   - build backend Docker image

### Acceptance Criteria

- CI runs on pull requests and pushes to `dev` and `main`.
- CI does not require real API keys.
- CI does not call paid LLM APIs.
- CI does not require Ollama.
- CI includes backend Docker image build.
- CI verifies the backend image can be built without bundled Chroma DB artifacts.
- CI verifies the deployment dependency set, not the full local/evaluation dependency set.

### Commit Message

```text
ci: add backend and frontend checks
```

---

## Task 12 — Update README with Deployment Guide

### Objective

Document the final deployment flow for portfolio reviewers and future maintainers.

### Actions

Update `README.md` with a deployment section covering:

1. Architecture:

```text
Frontend: Vercel
Backend API: Render Docker
Chroma DB: independent container/service
Generation: OpenAI API
Local mode: Ollama
Retrieval: backend uses Chroma HTTP client plus Clova embeddings
```

2. Local development mode:

```env
GENERATION_PROVIDER=ollama
```

3. Deployment mode:

```env
GENERATION_PROVIDER=openai
```

4. Backend Docker deployment steps.
5. Chroma service deployment or local compose steps.
6. Vercel frontend deployment steps.
7. Required environment variables.
8. Smoke test commands:

```bash
curl https://your-backend-url/health
curl https://your-backend-url/api/chat
```

9. Notes explaining that evaluation can report:

```text
- Local baseline: Ollama llama3.2:3b
- Deployed generation model: OpenAI API
```

### Acceptance Criteria

- README clearly distinguishes local Ollama mode from deployed API mode.
- README explains that Chroma runs separately from the backend and is accessed over HTTP.
- A reviewer can understand how the project is deployed.
- No secrets are included.

### Commit Message

```text
docs: add deployment guide
```

---

## Final Verification Checklist

After Task 12, run the following checks where possible:

```bash
python -m compileall backend src
```

```bash
cd frontend-web
npm ci
npm run build
```

```bash
docker build -f Dockerfile.backend -t finance-rag-backend .
```

```bash
docker compose --env-file .env.deploy up --build
```

Then verify:

```bash
curl http://localhost:8000/health
```

Also verify from backend logs or a smoke endpoint that the backend connects to Chroma through the configured HTTP host/port and does not open a local Chroma persist directory.

Do not call real OpenAI APIs during automated CI unless explicitly instructed by the user. Prefer mock, import, and smoke checks.

---

## Human-Only Follow-Up Tasks

Do not attempt these inside Codex. The user will do them manually.

```text
1. Create OpenAI API key
2. Create Clova embedding API credentials if they are not already available
3. Create or provision the production Chroma service/container
4. Load or mount the `chroma_clova` data into the Chroma service
5. Create Render backend service
6. Add production environment variables in Render UI, including Chroma host/port
7. Create Vercel project
8. Share the actual Vercel domain when asked so CORS can be finalized
9. Add VITE_API_BASE_URL in Vercel UI
10. Deploy Chroma service
11. Deploy backend
12. Deploy frontend
13. Run production smoke tests
14. Check latency and API cost
15. Push final commits manually
```
