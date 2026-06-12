#!/usr/bin/env bash
# Run Django manage.py inside the web container.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

cd "$DEPLOY_DIR"
exec "$SCRIPT_DIR/compose.sh" -f "$COMPOSE_FILE" exec web uv run python manage.py "$@"
