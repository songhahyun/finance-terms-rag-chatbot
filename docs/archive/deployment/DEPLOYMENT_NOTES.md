## Current Generation Flow

- Backend entrypoint: `backend/app/main.py` creates the FastAPI app, registers CORS and request logging middleware, and includes the health, auth, chat, knowledge document, and monitor routers.
- RAG service: `src/serving/rag_service.py` owns the shared `RAGService`, builds retrievers with `src.retrieval.factory.build_retriever`, and wraps them in `src.generation.rag_pipeline.RAGPipeline`.
- Current generator: `src.generation.llm.OllamaGenerator` is instantiated directly in `RAGService._build_pipeline()` with Ollama settings.
- Current settings source: `src.common.config.get_settings()` loads project settings from environment variables and the root `.env`; `backend.app.config.get_backend_settings()` separately loads auth/JWT settings for the FastAPI layer.
- Chat endpoint: `backend/app/routers/chat.py` exposes `POST /chat` and `POST /chat/stream`, both protected by `get_current_user`, and calls `answer_query()` or `stream_answer()` from `src.serving.rag_service`.

## API Route Namespace

- Health checks remain available at `GET /health`.
- Application API routers are mounted under `/api`, including `POST /api/auth/login`, `POST /api/chat`, `POST /api/chat/stream`, `GET /api/knowledge-documents`, and `GET /api/monitor/summary`.
- Frontend `VITE_API_BASE_URL` should contain only the backend origin, for example `http://localhost:8000`; `frontend-web/src/lib/api.ts` appends `/api` in code.

## Chroma HTTP Service

- Deployment retrieval uses `CHROMA_CLIENT_MODE=http`, which constructs a `chromadb.HttpClient` for LangChain Chroma instead of opening a local persisted Chroma directory in the backend container.
- Configure the Chroma service with `CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_SSL`, and `CHROMA_COLLECTION_NAME`; the deployment example uses `chroma:8000` and collection `finance_clova`.
- Local persisted Chroma remains available only when explicitly configured with `CHROMA_CLIENT_MODE=persistent`, typically with the existing local `chroma_clova` artifact and local collection name.

## Vercel Frontend Deployment

- Framework Preset: Vite
- Root Directory: `frontend-web`
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment Variable: `VITE_API_BASE_URL`
- `VITE_API_BASE_URL` must contain only the deployed backend origin, for example `https://your-backend-url`; frontend code appends the `/api` namespace automatically.
- Do not hard-code Render backend URLs in frontend source. Configure the backend origin in the Vercel project environment variables.

## CI and Backend Image Publishing

- GitHub Actions runs backend deployment dependency checks, frontend `npm ci` build, and a required backend Docker image build on pull requests and pushes to `dev` or `main`.
- Pushes to `dev` or `main` publish the backend image to GHCR as `ghcr.io/<owner>/<repo>/backend:latest` and `ghcr.io/<owner>/<repo>/backend:<commit-sha>`.
- Render should deploy the backend from the prebuilt GHCR image instead of building from the GitHub repository. If the GHCR package is private, configure Render registry credentials or make the package accessible to Render.
- Render environment variables remain configured in the Render UI; secrets are not stored in the image or workflow.
