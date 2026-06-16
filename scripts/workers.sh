#!/usr/bin/env sh
set -eu

ENV_FILE="${ENV_FILE:-.env.production}"

APP_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" up -d --build redis backend celery_worker scheduler
APP_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" logs -f celery_worker scheduler
