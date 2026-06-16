#!/usr/bin/env sh
set -eu

ENV_FILE="${ENV_FILE:-.env.production}"
BACKUP_DIR="${BACKUP_DIR:-backups/redis}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_FILE="${OUTPUT_FILE:-$BACKUP_DIR/dump_${TIMESTAMP}.rdb}"
REDIS_CONTAINER="${REDIS_CONTAINER:-trading-ai-redis}"

mkdir -p "$BACKUP_DIR"
docker compose --env-file "$ENV_FILE" exec -T redis redis-cli SAVE
docker cp "$REDIS_CONTAINER:/data/dump.rdb" "$OUTPUT_FILE"

printf '%s\n' "Redis backup written to $OUTPUT_FILE"
