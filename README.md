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
- `scheduler`: APScheduler process that queues recurring Celery work
- `nginx`: public reverse proxy for frontend, API, metrics, and websockets

Do not commit real secrets. Use placeholders in committed files and provide real values only in your deployment environment.

### Environment Variables

Create environment files from the templates:

```bash
cp .env.development.example .env.development
cp .env.production.example .env.production
```

For local Docker development, you may also copy the development file to `.env` because Docker Compose automatically reads `.env` for variable interpolation:

```bash
cp .env.development.example .env
```

Set these values before starting production:

```env
ENVIRONMENT=production
DOCS_ENABLED=false
NGINX_HTTP_PORT=80
ALLOWED_HOSTS=["your-domain.example","www.your-domain.example","localhost","127.0.0.1","backend","nginx"]
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
- `BINANCE_BROKER_MODE`: broker execution mode, `testnet` by default. Set to `live` only after enabling live trading risk controls and adding active live credentials.
- `BINANCE_API_BASE_URL`, `BINANCE_TESTNET_API_BASE_URL`, `BINANCE_RECV_WINDOW`: Binance REST endpoints and signed request receive window.
- `MARKET_SYNC_SYMBOLS`, `MARKET_SYNC_TIMEFRAME`, `MARKET_SYNC_LIMIT`: historical market sync defaults.
- `AI_PROVIDER`: `rules`, `openai`, `ollama`, or `local-llama`.
- `OPENAI_API_KEY`: optional placeholder only; leave empty unless using OpenAI.
- `SENTIMENT_PROVIDERS`: enabled sentiment adapters, for example `["newsapi","cryptopanic","reddit","x"]`.
- `NEWS_API_KEY`, `CRYPTOPANIC_API_KEY`, `REDDIT_BEARER_TOKEN`, `X_BEARER_TOKEN`: optional provider credentials. Missing keys skip that provider and the backend falls back to deterministic local sentiment if no provider returns data.
- `NOTIFICATION_EMAIL_*`, `TELEGRAM_*`, `WHATSAPP_*`, `DISCORD_WEBHOOK_URL`: optional notification provider credentials and endpoints. Missing keys mark enabled channels as not configured and are never returned to the frontend.
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

### Frontend Dockerfile

The frontend image is built from [frontend/Dockerfile](frontend/Dockerfile). It builds the Vite app with public `VITE_*` build args, then serves the compiled `dist` directory with Nginx on port `80`.

### Nginx

The public reverse proxy is configured in [nginx/nginx.conf](nginx/nginx.conf). It routes:

- `/` to the frontend container
- `/api/` to the backend container
- `/api/ws/` and `/ws/` to backend websocket routes
- `/metrics` to backend metrics
- `/health` to an Nginx health response

### Deployment Scripts

The repository includes shell scripts for common deployment tasks:

```bash
# Build, migrate, and start the production stack.
ENV_FILE=.env.production ./scripts/start.sh

# Apply Alembic migrations only.
ENV_FILE=.env.production ./scripts/migrate.sh

# Start worker processes and follow their logs.
ENV_FILE=.env.production ./scripts/workers.sh

# Run backend and frontend tests locally.
./scripts/test.sh
```

The backend image also includes container entrypoint scripts under `backend/scripts/`:

- `start.sh`: starts Uvicorn and can optionally run migrations when `RUN_MIGRATIONS_ON_STARTUP=true`.
- `migrate.sh`: runs `alembic upgrade head`.
- `worker.sh`: starts the Celery worker.
- `scheduler.sh`: starts the APScheduler queueing process.
- `test.sh`: runs backend pytest when test dependencies are installed.

### Database Migrations

**Important:** In production environments, `Base.metadata.create_all` and startup schema repair are disabled. All schema changes must be applied via Alembic migrations to ensure auditability and data safety. The backend expects the database to already be migrated before it starts serving traffic.

Run PostgreSQL, apply migrations, then start the application stack:

```bash
docker compose --env-file .env.production up -d postgres redis
docker compose --env-file .env.production run --rm backend /app/scripts/migrate.sh
docker compose --env-file .env.production up -d --build
```

To inspect migration state:

```bash
docker compose --env-file .env.production run --rm backend alembic current
docker compose --env-file .env.production run --rm backend alembic history
```

### Celery Commands

Production Compose starts these automatically:

```bash
docker compose --env-file .env.production up -d celery_worker scheduler
```

Manual worker command:

```bash
docker compose --env-file .env.production run --rm backend /app/scripts/worker.sh
```

Manual scheduler command:

```bash
docker compose --env-file .env.production run --rm backend /app/scripts/scheduler.sh
```

### Production Run Commands

Build and start the full production stack:

```bash
ENV_FILE=.env.production ./scripts/start.sh
```

Run migrations before starting or upgrading backend containers:

```bash
ENV_FILE=.env.production ./scripts/migrate.sh
```

View logs:

```bash
docker compose logs -f backend
docker compose logs -f celery_worker
docker compose logs -f scheduler
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

Local development keeps `DEVELOPMENT_AUTO_CREATE_SCHEMA=true` and `DEVELOPMENT_SCHEMA_REPAIR_ENABLED=true` by default, so a new local SQLite/Postgres database can start without manual migration setup. For production-like local testing, run Alembic explicitly and set both development schema helper flags to `false`.

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
python -m app.workers.scheduler
```

For local Docker experimentation, copy `.env.development.example` to `.env`, replace placeholders if needed, and run the same Compose commands. For pure local frontend development, `frontend/.env.example` defaults to `http://localhost:8000`.

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

- `app.services.market_data`: provider sync, warehouse, validation, and websocket ingestion.
- `app.services.sentiment`: provider-based news and social sentiment ingestion.

## Sentiment Providers

The sentiment service uses provider adapters for News API, CryptoPanic, Reddit, and X/Twitter. Provider records are stored with provider name, source, symbol, related asset, timestamp, confidence, headline, and sentiment score. The API response remains compatible with the frontend sentiment table.

Configure provider credentials through environment variables and run migrations before production startup:

```bash
ENV_FILE=.env.production ./scripts/migrate.sh
```

If provider keys are missing or providers fail, the backend returns fallback sentiment items so local development and dashboards continue to work.
