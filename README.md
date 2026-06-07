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

## Stack

Backend: Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery, APScheduler, Pandas, NumPy, Scikit-learn, XGBoost, pandas-ta, Sentry, Prometheus metrics.

Frontend: React, TypeScript, Tailwind CSS, Recharts, Axios, TanStack Query, Zustand, Sentry.

Infrastructure: Docker Compose, Nginx, PostgreSQL, Redis, GitHub Actions, Prometheus, Grafana. VPS deployment can use the same Docker Compose stack behind your VPS firewall and DNS.
