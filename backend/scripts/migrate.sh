#!/usr/bin/env sh
set -eu

echo "Running Alembic migrations..."
alembic upgrade head
