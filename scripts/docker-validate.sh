#!/usr/bin/env sh
set -eu

ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE_FILES="-f docker-compose.yml"

if [ "${TLS_ENABLED:-false}" = "true" ]; then
  COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.tls.yml"
  BASE_URL="${BASE_URL:-https://localhost}"
else
  BASE_URL="${BASE_URL:-http://localhost}"
fi

docker compose $COMPOSE_FILES --env-file "$ENV_FILE" config
docker compose $COMPOSE_FILES --env-file "$ENV_FILE" build backend frontend
docker compose $COMPOSE_FILES --env-file "$ENV_FILE" up -d postgres redis
docker compose $COMPOSE_FILES --env-file "$ENV_FILE" run --rm backend /app/scripts/migrate.sh
docker compose $COMPOSE_FILES --env-file "$ENV_FILE" up -d backend celery_worker scheduler frontend nginx

./scripts/staging-smoke.sh
docker compose $COMPOSE_FILES --env-file "$ENV_FILE" ps
