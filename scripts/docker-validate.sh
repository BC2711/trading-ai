#!/usr/bin/env sh
set -eu

ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE_FILES="-f docker-compose.yml"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

if [ "${TLS_ENABLED:-false}" = "true" ]; then
  COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.tls.yml"
  BASE_URL="${BASE_URL:-https://localhost}"
else
  BASE_URL="${BASE_URL:-http://localhost}"
fi

APP_ENV_FILE="$ENV_FILE" docker compose $COMPOSE_FILES --env-file "$ENV_FILE" config
APP_ENV_FILE="$ENV_FILE" docker compose $COMPOSE_FILES --env-file "$ENV_FILE" build backend frontend
APP_ENV_FILE="$ENV_FILE" docker compose $COMPOSE_FILES --env-file "$ENV_FILE" up -d postgres redis
APP_ENV_FILE="$ENV_FILE" docker compose $COMPOSE_FILES --env-file "$ENV_FILE" run --rm backend /app/scripts/migrate.sh
APP_ENV_FILE="$ENV_FILE" docker compose $COMPOSE_FILES --env-file "$ENV_FILE" up -d backend celery_worker scheduler frontend nginx

BASE_URL="$BASE_URL" API_KEY="${API_KEY:-}" ./scripts/staging-smoke.sh
APP_ENV_FILE="$ENV_FILE" docker compose $COMPOSE_FILES --env-file "$ENV_FILE" ps
