# Trading AI

Starter monorepo for a FastAPI backend and React TypeScript frontend.

## Structure

```text
backend/     FastAPI, SQLAlchemy, Alembic, Celery, APScheduler, ML/TA stack
frontend/    Vite, React, TypeScript, Tailwind, Query, Zustand, Recharts
nginx/       Reverse proxy config
monitoring/  Prometheus and Grafana provisioning
```

## Production Deployment

The repository includes a production Docker Compose stack with:

- `frontend`: static Vite build served by Nginx
- `backend`: FastAPI application
- `postgres`: PostgreSQL database
- `redis`: Celery broker/cache backend
- `celery_worker`: asynchronous task worker
- `celery_beat`: scheduled task runner
- `nginx`: public reverse proxy for frontend, API, metrics, and websockets

Do not commit real secrets. Use placeholders in committed files and provide real values only in your deployment environment.

### Environment Variables

Create a production `.env` file from the template:

```bash
cp .env.example .env
```

Set these values before starting production:

```env
ENVIRONMENT=production
DOCS_ENABLED=false
NGINX_HTTP_PORT=80
ALLOWED_HOSTS=["your-domain.example","www.your-domain.example"]
CORS_ORIGINS=["https://your-domain.example"]
API_KEY=replace-with-long-random-api-key
JWT_SECRET=replace-with-long-random-jwt-secret
JWT_REFRESH_SECRET=replace-with-different-long-random-refresh-secret
CREDENTIAL_ENCRYPTION_SECRET=replace-with-long-random-encryption-secret
POSTGRES_USER=trading
POSTGRES_PASSWORD=replace-with-long-random-postgres-password
POSTGRES_DB=trading
VITE_API_BASE_URL=
VITE_API_KEY=replace-with-same-value-as-api-key-if-api-key-auth-is-enabled
```

Important backend variables:

- `DATABASE_URL`: SQLAlchemy URL. In Compose this is set to the internal PostgreSQL service automatically.
- `REDIS_URL`: Redis URL for app-level Redis usage.
- `CELERY_BROKER_URL`: Celery broker URL, usually Redis DB 1.
- `CELERY_RESULT_BACKEND`: Celery result backend URL, usually Redis DB 2.
- `MARKET_SYNC_SYMBOLS`, `MARKET_SYNC_TIMEFRAME`, `MARKET_SYNC_LIMIT`: historical market sync defaults.
- `AI_PROVIDER`: `rules`, `openai`, `ollama`, or `local-llama`.
- `OPENAI_API_KEY`: optional placeholder only; leave empty unless using OpenAI.
- `SENTRY_DSN` and `VITE_SENTRY_DSN`: optional monitoring DSNs.

Important frontend variables:

- `VITE_API_BASE_URL`: leave empty for same-origin API calls through Nginx, or set a public API origin.
- `VITE_API_KEY`: public client API key value only if `API_KEY` auth is enabled.
- `VITE_SENTRY_DSN`: optional frontend Sentry DSN.

### Backend Dockerfile

The backend image is built from [backend/Dockerfile](backend/Dockerfile). It installs Python dependencies, copies the FastAPI app and Alembic migrations, runs as a non-root user, exposes port `8000`, and starts:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
```

### Backend Setup

For production, the backend reads configuration from `.env` through Docker Compose. Required production values include `API_KEY`, `JWT_SECRET`, `JWT_REFRESH_SECRET`, `CREDENTIAL_ENCRYPTION_SECRET`, `ALLOWED_HOSTS`, `CORS_ORIGINS`, PostgreSQL settings, and Redis/Celery URLs.

Build the backend image:

```bash
docker compose --env-file .env build backend
```

Run backend migrations:

```bash
docker compose --env-file .env run --rm backend alembic upgrade head
```

Start only the backend and its dependencies:

```bash
docker compose --env-file .env up -d postgres redis backend
```

### Frontend Dockerfile

The frontend image is built from [frontend/Dockerfile](frontend/Dockerfile). It builds the Vite app with public `VITE_*` build args, then serves the compiled `dist` directory with Nginx on port `80`.

### Frontend Setup

For production behind the included Nginx proxy, leave `VITE_API_BASE_URL` empty so browser requests use the same origin. If API key auth is enabled, set `VITE_API_KEY` to the same placeholder value you replace in `API_KEY`.

Build the frontend image:

```bash
docker compose --env-file .env build frontend
```

Start only the frontend after the backend is healthy:

```bash
docker compose --env-file .env up -d frontend
```

### Nginx

The public reverse proxy is configured in [nginx/nginx.conf](nginx/nginx.conf). It routes:

- `/` to the frontend container
- `/api/` to the backend container
- `/api/ws/` and `/ws/` to backend websocket routes
- `/metrics` to backend metrics
- `/health` to an Nginx health response

### Database Migrations

Run migrations after building images and before accepting production traffic:

```bash
docker compose run --rm backend alembic upgrade head
```

To inspect migration state:

```bash
docker compose run --rm backend alembic current
docker compose run --rm backend alembic history
```

### Celery Commands

Production Compose starts these automatically:

```bash
docker compose up -d celery_worker celery_beat
```

Manual worker command:

```bash
docker compose run --rm backend celery -A app.core.celery_app.celery_app worker --loglevel=info
```

Manual beat command:

```bash
docker compose run --rm backend celery -A app.core.celery_app.celery_app beat --loglevel=info
```

### Production Run Commands

Build and start the full production stack:

```bash
docker compose --env-file .env up -d --build
```

Run migrations:

```bash
docker compose --env-file .env run --rm backend alembic upgrade head
```

View logs:

```bash
docker compose logs -f backend
docker compose logs -f celery_worker
docker compose logs -f nginx
```

Stop the stack:

```bash
docker compose down
```

Stop and remove persistent database/cache volumes only when intentionally resetting all data:

```bash
docker compose down -v
```

Production URLs:

- Nginx and frontend: `http://localhost` or your configured domain
- Backend API through proxy: `http://localhost/api`
- Health: `http://localhost/health`

API docs are disabled when `ENVIRONMENT=production`.

### Local Development Commands

Run backend locally:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run frontend locally:

```bash
cd frontend
npm install
npm run dev
```

Run local tests and builds:

```bash
cd backend
pip install -r requirements-dev.txt
pytest
alembic upgrade head

cd ../frontend
npm ci
npm run build
```

Run Celery locally after Redis is available:

```bash
cd backend
celery -A app.core.celery_app.celery_app worker --loglevel=info
celery -A app.core.celery_app.celery_app beat --loglevel=info
```

For local Docker experimentation, copy `.env.example` to `.env`, replace placeholders, and run the same Compose commands. For pure local frontend development, `frontend/.env.example` defaults to `http://localhost:8000`.

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

## Market Data Engine

The backend includes a multi-asset market data layer for crypto, forex, stocks, commodities, and indices. Binance REST sync is available for crypto candles; other asset classes can be loaded through the historical import API.

Stored data:

- OHLCV candles with spread
- Tick data with bid, ask, last price, volume, and spread
- Trade prints
- Order book snapshots

Core endpoints:

- `POST /api/market-data/import` imports candles, ticks, trades, and order books.
- `GET /api/market-data/validate` checks OHLC integrity, negative values, spread validity, and missing candles.
- `POST /api/market-data/repair` repairs missing crypto candles through the configured Binance source.
- `GET /api/market-data/ticks`
- `GET /api/market-data/trades`
- `GET /api/market-data/order-books`
- `POST /api/market-data/stream` ingests live candle/tick/trade/order-book events.
- `WS /api/ws/market-data?channels=candles,ticks,order_books,trades&token=<access-token>` streams live events to subscribed clients.

Implementation modules:

- `MarketDataService`: import, validation, repair, and stream ingestion orchestration.
- `MarketDataRepository`: persistence, upserts, latest reads, symbol normalization, and missing candle detection.
- `MarketDataScheduler`: scheduled update/repair facade.
- `MarketDataWebsocket`: channel-based realtime fanout.

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

## AI Training Pipeline

The backend includes a feature-engineering and model-management pipeline for directional prediction on candle history.

Feature generation includes RSI, MACD, EMA, SMA, ATR, ADX, Bollinger Bands, candle returns/ranges, spread, volume ratio, volume moving average, and OBV.

Supported model types:

- `random_forest`
- `xgboost`
- `lightgbm`
- `lstm`
- `gru`
- `transformer`

`xgboost` uses XGBoost, `lightgbm` uses native LightGBM, and `lstm`, `gru`, and `transformer` use native PyTorch sequence classifiers when the installed backend requirements are present. TensorFlow is included in the backend ML dependency set for future TensorFlow/Keras model adapters. If a heavyweight runtime is not installed in a local development environment, the service degrades to sklearn-compatible fallback models instead of preventing the API from starting.

Core endpoints:

- `POST /api/ai/models/train`
- `POST /api/ai/models/{model_id}/retrain`
- `POST /api/ai/models/{model_id}/deploy`
- `POST /api/ai/models/{model_id}/disable`
- `POST /api/ai/models/compare`
- `POST /api/ai/models/{model_id}/predict`

Implementation modules:

- `FeatureService`: feature engineering and supervised dataset creation.
- `ModelService`: model factory and artifact persistence.
- `ModelEvaluationService`: accuracy, precision, recall, F1, ROC AUC, and confidence metrics.
- `TrainingService`: train, retrain, deploy, disable, compare, version, and predict orchestration.

## Stack

Backend: Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery, APScheduler, Pandas, NumPy, Scikit-learn, XGBoost, pandas-ta, Sentry, Prometheus metrics.

Frontend: React, TypeScript, Tailwind CSS, Recharts, Axios, TanStack Query, Zustand, Sentry.

Infrastructure: Docker Compose, Nginx, PostgreSQL, Redis, GitHub Actions, Prometheus, Grafana. VPS deployment can use the same Docker Compose stack behind your VPS firewall and DNS.
