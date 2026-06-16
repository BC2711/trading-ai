#!/usr/bin/env sh
set -eu

ENV_FILE="${ENV_FILE:-.env.production}"

APP_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" run --rm backend /app/scripts/migrate.sh
