# Trading AI

Starter monorepo for a FastAPI backend and React TypeScript frontend.

## Structure

```text
backend/     FastAPI, SQLAlchemy, Alembic, Celery, APScheduler, ML/TA stack
frontend/    Vite, React, TypeScript, Tailwind, Query, Zustand, Recharts
nginx/       Reverse proxy config
monitoring/  Prometheus and Grafana provisioning
```

## Run With Docker

```bash
docker compose up --build
```

Backend: http://localhost:8000

Frontend: http://localhost:5173

API docs: http://localhost:8000/docs

Nginx proxy: http://localhost

Prometheus: http://localhost:9090

Grafana: http://localhost:3000

Default Grafana login: `admin` / `admin`

## Local Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Local Frontend

```bash
cd frontend
npm install
npm run dev
```

## Production Baseline

Before running with `ENVIRONMENT=production`, set these values explicitly:

```env
ENVIRONMENT=production
API_KEY=replace-with-a-long-random-secret
JWT_SECRET=replace-with-a-long-random-jwt-secret
JWT_REFRESH_SECRET=replace-with-a-different-long-random-refresh-secret
CREDENTIAL_ENCRYPTION_SECRET=replace-with-a-long-random-encryption-secret
ALLOWED_HOSTS=["your-domain.com","api.your-domain.com"]
CORS_ORIGINS=["https://your-domain.com"]
DATABASE_URL=postgresql+psycopg://user:password@db-host:5432/trading
REDIS_URL=redis://redis-host:6379/0
CELERY_BROKER_URL=redis://redis-host:6379/1
CELERY_RESULT_BACKEND=redis://redis-host:6379/2
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
```

Production mode fails fast if `API_KEY`, JWT secrets, credential encryption secret, or host/origin allowlists are unsafe. API routes under `/api/*` require the `X-API-Key` header when configured, except `/api/health` and auth endpoints. Trading and administration routes also require a bearer token with the required permission. The first registered user is promoted to admin; later public registrations are traders until an admin changes their role.

Run database migrations before deploying new backend code:

```bash
cd backend
alembic upgrade head
```

Recommended pre-deploy checks:

```bash
cd backend
pip install -r requirements-dev.txt
pytest
alembic upgrade head

cd ../frontend
npm ci
npm run build
npm audit --audit-level=moderate
```

Docker Compose includes service health checks, but Docker Desktop or Docker Engine must be installed on the host. This environment did not have Docker available, so Compose validation must be run on the deployment machine.

## Initial API

- `GET /api/health`
- `GET /api/signals`
- `GET /api/indicators/preview`
- `GET /metrics`
- `POST /api/ai/analyze-signal`
- `GET /api/ai/analyses`
- `GET /api/ai/analyses/{analysis_id}`

## AI Provider

The backend supports a rule-based AI provider by default. Set `AI_PROVIDER=openai` and provide `OPENAI_API_KEY` to enable OpenAI-based analysis.

### Local LLM (llama-cpp)

You can run a local LLM using `llama-cpp-python` and a GGUF/ggml model file. Steps:

1. Install `llama-cpp-python` in the backend environment:

```bash
pip install llama-cpp-python
```

2. Download a compatible GGUF/ggml model and place it on the host, for example `/models/llama2.gguf`.

3. Configure the backend to point at the model by setting `LOCAL_MODEL_PATH` in your `.env` or Docker configuration:

```
LOCAL_MODEL_PATH=/models/llama2.gguf
AI_PROVIDER=local-llama
```

4. Restart the backend (or Docker compose) and the `/api/ai/analyze-signal` endpoint will attempt to use the local model. If the model or library is missing the service will fall back to the rule-based provider.

Notes:
- Running local LLMs requires significant CPU/RAM; consider GPU or quantized models for performance.
- For Ollama users, configure `OLLAMA_BASE_URL` and `OLLAMA_MODEL` and set `AI_PROVIDER=ollama`.

## Stack

Backend: Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery, APScheduler, Pandas, NumPy, Scikit-learn, XGBoost, pandas-ta, Sentry, Prometheus metrics.

Frontend: React, TypeScript, Tailwind CSS, Recharts, Axios, TanStack Query, Zustand, Sentry.

Infrastructure: Docker Compose, Nginx, PostgreSQL, Redis, GitHub Actions, Prometheus, Grafana. VPS deployment can use the same Docker Compose stack behind your VPS firewall and DNS.
