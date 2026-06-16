#!/usr/bin/env sh
set -eu

BASE_URL="${BASE_URL:-http://localhost}"
SMOKE_EMAIL="${SMOKE_EMAIL:-smoke-admin@example.com}"
SMOKE_PASSWORD="${SMOKE_PASSWORD:-strong-smoke-password}"
API_KEY="${API_KEY:-}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

api_header_args() {
  if [ -n "$API_KEY" ]; then
    printf '%s\n' "-H" "X-API-Key: $API_KEY"
  fi
}

curl_json() {
  curl -fsS "$@"
}

curl_json "$BASE_URL/api/health" > "$TMP_DIR/health.json"

curl_json \
  $(api_header_args) \
  -H "Content-Type: application/json" \
  -X POST "$BASE_URL/api/auth/register" \
  -d "{\"email\":\"$SMOKE_EMAIL\",\"full_name\":\"Smoke Admin\",\"password\":\"$SMOKE_PASSWORD\",\"role\":\"admin\"}" \
  > "$TMP_DIR/register.json" || true

curl_json \
  $(api_header_args) \
  -H "Content-Type: application/json" \
  -X POST "$BASE_URL/api/auth/login" \
  -d "{\"email\":\"$SMOKE_EMAIL\",\"password\":\"$SMOKE_PASSWORD\"}" \
  > "$TMP_DIR/login.json"

TOKEN="$(python -c "import json,sys; print(json.load(open(sys.argv[1]))['access_token'])" "$TMP_DIR/login.json")"

curl_json \
  $(api_header_args) \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/me" \
  > "$TMP_DIR/me.json"

curl_json \
  $(api_header_args) \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -X POST "$BASE_URL/api/risk/validate-trade" \
  -d '{"symbol":"BTCUSDT","side":"buy","price":65000,"quantity":0.001,"stop_loss":64900,"take_profit":67000,"execution_mode":"paper"}' \
  > "$TMP_DIR/risk.json"

python -c "import json,sys; data=json.load(open(sys.argv[1])); assert data.get('approved') is True, data" "$TMP_DIR/risk.json"

printf '%s\n' "Staging smoke checks passed for $BASE_URL"
