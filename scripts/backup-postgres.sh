#!/usr/bin/env sh
set -eu

ENV_FILE="${ENV_FILE:-.env.production}"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

BACKUP_DIR="${BACKUP_DIR:-backups/postgres}"
POSTGRES_USER="${POSTGRES_USER:-trading}"
POSTGRES_DB="${POSTGRES_DB:-trading}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_FILE="${OUTPUT_FILE:-$BACKUP_DIR/trading_${TIMESTAMP}.dump}"

mkdir -p "$BACKUP_DIR"
APP_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$OUTPUT_FILE"

printf '%s\n' "Postgres backup written to $OUTPUT_FILE"
