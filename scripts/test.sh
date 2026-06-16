#!/usr/bin/env sh
set -eu

(
  cd backend
  python -m pytest "$@"
)

(
  cd frontend
  npm run test
)
