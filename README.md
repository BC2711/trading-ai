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
