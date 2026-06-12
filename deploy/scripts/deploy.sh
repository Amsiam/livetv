#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEPLOY_DIR="$ROOT/deploy"
COMPOSE_FILE="docker-compose.prod.yml"

cd "$DEPLOY_DIR"

if [[ ! -f .env ]]; then
  echo "Missing deploy/.env — copy env.production.example to .env and edit it."
  exit 1
fi

echo "==> Pull latest code"
git -C "$ROOT" pull --ff-only

echo "==> Build and start containers"
docker compose -f "$COMPOSE_FILE" up -d --build

echo "==> Run migrations"
docker compose -f "$COMPOSE_FILE" exec -T web uv run python manage.py migrate --noinput

echo "==> Collect static files"
docker compose -f "$COMPOSE_FILE" exec -T web uv run python manage.py collectstatic --noinput

echo "==> Service status"
docker compose -f "$COMPOSE_FILE" ps

echo "==> Celery worker ping"
docker compose -f "$COMPOSE_FILE" exec -T celery-worker \
  uv run celery -A config inspect ping --timeout 10

echo "==> Deployment complete"
