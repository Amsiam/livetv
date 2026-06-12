#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
COMPOSE=("$SCRIPT_DIR/compose.sh")
API_URL="${1:-http://localhost:8134/v1/health/}"

cd "$DEPLOY_DIR"

# Local curls send Host: localhost — Django needs the public host unless localhost
# is in DJANGO_ALLOWED_HOSTS. Prefer Host from PUBLIC_API_URL in deploy/.env.
CURL_OPTS=()
if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a && source .env && set +a
fi
if [[ "$API_URL" == *"localhost"* || "$API_URL" == *"127.0.0.1"* ]]; then
  HEALTH_HOST="${HEALTH_HOST:-}"
  if [[ -z "$HEALTH_HOST" && -n "${PUBLIC_API_URL:-}" ]]; then
    HEALTH_HOST="${PUBLIC_API_URL#https://}"
    HEALTH_HOST="${HEALTH_HOST#http://}"
    HEALTH_HOST="${HEALTH_HOST%%/*}"
  fi
  if [[ -n "$HEALTH_HOST" ]]; then
    CURL_OPTS+=(-H "Host: $HEALTH_HOST")
  fi
fi

echo "Checking API: $API_URL${HEALTH_HOST:+ (Host: $HEALTH_HOST)}"
curl -fsS "${CURL_OPTS[@]}" "$API_URL" | python3 -m json.tool

echo "Checking containers"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" ps web nginx celery-worker celery-beat redis postgres

echo "Checking Celery worker"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" exec -T celery-worker \
  uv run celery -A config inspect ping --timeout 10

echo "OK"
