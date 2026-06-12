#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
COMPOSE=("$SCRIPT_DIR/compose.sh")
API_URL="${1:-http://localhost:8134/v1/health/}"

cd "$DEPLOY_DIR"

echo "Checking API: $API_URL"
curl -fsS "$API_URL" | python3 -m json.tool

echo "Checking containers"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" ps web nginx celery-worker celery-beat redis postgres

echo "Checking Celery worker"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" exec -T celery-worker \
  uv run celery -A config inspect ping --timeout 10

echo "OK"
