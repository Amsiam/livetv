#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$ROOT/deploy"
COMPOSE_FILE="docker-compose.prod.yml"
COMPOSE=("$SCRIPT_DIR/compose.sh")

cd "$DEPLOY_DIR"

if [[ ! -f .env ]]; then
  echo "Missing deploy/.env — copy env.production.example to .env and edit it."
  exit 1
fi

echo "==> Pull latest code"
git -C "$ROOT" pull --ff-only

echo "==> Roll application containers"
"$SCRIPT_DIR/roll-app-tier.sh"

echo "==> Verify web container picked up latest code"
"$SCRIPT_DIR/verify-app-code.sh"

echo "==> Run migrations"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" exec -T web uv run python manage.py migrate --noinput

echo "==> Collect static files"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" exec -T web uv run python manage.py collectstatic --noinput

echo "==> Service status"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" ps

echo "==> Celery worker ping"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" exec -T celery-worker \
  uv run celery -A config inspect ping --timeout 10

echo "==> Deployment complete"
