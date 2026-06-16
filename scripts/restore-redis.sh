#!/usr/bin/env sh
set -eu

ENV_FILE="${ENV_FILE:-.env.production}"
REDIS_CONTAINER="${REDIS_CONTAINER:-trading-ai-redis}"

if [ -z "${BACKUP_FILE:-}" ]; then
  printf '%s\n' "BACKUP_FILE is required, for example BACKUP_FILE=backups/redis/dump.rdb $0" >&2
  exit 2
fi

if [ ! -f "$BACKUP_FILE" ]; then
  printf '%s\n' "Backup file not found: $BACKUP_FILE" >&2
  exit 2
fi

if [ "${CONFIRM_RESTORE:-}" != "yes" ]; then
  printf '%s\n' "Refusing to restore without CONFIRM_RESTORE=yes. This replaces Redis persistence data." >&2
  exit 2
fi

docker compose --env-file "$ENV_FILE" stop redis
docker cp "$BACKUP_FILE" "$REDIS_CONTAINER:/data/dump.rdb"
docker compose --env-file "$ENV_FILE" start redis

printf '%s\n' "Redis restore completed from $BACKUP_FILE"
