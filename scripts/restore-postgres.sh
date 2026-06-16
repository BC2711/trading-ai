#!/usr/bin/env sh
set -eu

ENV_FILE="${ENV_FILE:-.env.production}"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-trading}"
POSTGRES_DB="${POSTGRES_DB:-trading}"

if [ -z "${BACKUP_FILE:-}" ]; then
  printf '%s\n' "BACKUP_FILE is required, for example BACKUP_FILE=backups/postgres/trading.dump $0" >&2
  exit 2
fi

if [ ! -f "$BACKUP_FILE" ]; then
  printf '%s\n' "Backup file not found: $BACKUP_FILE" >&2
  exit 2
fi

if [ "${CONFIRM_RESTORE:-}" != "yes" ]; then
  printf '%s\n' "Refusing to restore without CONFIRM_RESTORE=yes. This will replace database objects in $POSTGRES_DB." >&2
  exit 2
fi

cat "$BACKUP_FILE" | APP_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner

printf '%s\n' "Postgres restore completed from $BACKUP_FILE"
