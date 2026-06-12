#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
API_URL="${1:-http://localhost:8134/v1/health/}"

cd "$DEPLOY_DIR"

echo "Checking API: $API_URL"
curl -fsS "$API_URL" | python3 -m json.tool

echo "Checking containers"
docker compose -f "$COMPOSE_FILE" ps web nginx celery-worker celery-beat redis postgres

echo "Checking Celery worker"
docker compose -f "$COMPOSE_FILE" exec -T celery-worker \
  uv run celery -A config inspect ping --timeout 10

echo "OK"
