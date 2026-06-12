#!/usr/bin/env bash
# Replace web/nginx/celery without compose graceful stop (broken on some VPS hosts).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
COMPOSE=("$SCRIPT_DIR/compose.sh")
APP_SERVICES=(web nginx celery-worker celery-beat)

cd "$DEPLOY_DIR"

force_rm_id() {
  local id="$1"
  [[ -z "$id" ]] && return 0
  docker kill "$id" 2>/dev/null || sudo docker kill "$id" 2>/dev/null || true
  docker rm -f "$id" 2>/dev/null || sudo docker rm -f "$id" 2>/dev/null || true
}

echo "==> Remove failed recreate orphans"
while IFS= read -r name; do
  [[ -z "$name" ]] && continue
  echo "  rm $name"
  docker rm -f "$name" 2>/dev/null || sudo docker rm -f "$name" 2>/dev/null || true
done < <(docker ps -a --format '{{.Names}}' | grep -E '_deploy_|-deploy-' || true)

echo "==> Force-remove app containers (skip compose stop — permission denied on some hosts)"
for svc in "${APP_SERVICES[@]}"; do
  while IFS= read -r id; do
    [[ -z "$id" ]] && continue
    echo "  rm $svc ($id)"
    force_rm_id "$id"
  done < <("${COMPOSE[@]}" -f "$COMPOSE_FILE" ps -aq "$svc" 2>/dev/null || true)
done

echo "==> Build app images"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" build "${APP_SERVICES[@]}"

echo "==> Start data stores (no recreate)"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" up -d --no-recreate postgres redis

echo "==> Start app containers"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" up -d "${APP_SERVICES[@]}"
