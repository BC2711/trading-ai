#!/usr/bin/env sh
set -eu

ENV_FILE="${ENV_FILE:-.env.production}"

APP_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" up -d --build postgres redis
APP_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" run --rm backend /app/scripts/migrate.sh
APP_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" up -d --build backend celery_worker scheduler frontend nginx
APP_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" ps
