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
done < <(docker ps -a --format '{{.Names}}' | grep -E '_deploy_|-deploy-|^deploy-' || true)

echo "==> Force-remove app containers by name"
for name in livetv_web livetv_nginx livetv_celery_worker livetv_celery_beat \
  deploy_web_1 deploy_nginx_1 deploy_celery-worker_1 deploy_celery-beat_1 \
  deploy-celery-worker-1 deploy-celery-beat-1; do
  docker rm -f "$name" 2>/dev/null || sudo docker rm -f "$name" 2>/dev/null || true
done

echo "==> Force-remove app containers by compose label (skip graceful stop)"
for svc in "${APP_SERVICES[@]}"; do
  while IFS= read -r id; do
    [[ -z "$id" ]] && continue
    echo "  rm $svc ($id)"
    force_rm_id "$id"
  done < <("${COMPOSE[@]}" -f "$COMPOSE_FILE" ps -aq "$svc" 2>/dev/null || true)
done

echo "==> Git commit on disk"
git -C "$(cd "$DEPLOY_DIR/.." && pwd)" log -1 --oneline

echo "==> Build app images (Python code is copied into the image — pull alone is not enough)"
if [[ "${FORCE_BUILD:-}" == "1" ]]; then
  "${COMPOSE[@]}" -f "$COMPOSE_FILE" build --no-cache "${APP_SERVICES[@]}"
else
  "${COMPOSE[@]}" -f "$COMPOSE_FILE" build "${APP_SERVICES[@]}"
fi

echo "==> Start data stores (no recreate)"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" up -d --no-recreate postgres redis

echo "==> Start app containers (force new containers from fresh images)"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" up -d --force-recreate "${APP_SERVICES[@]}"

echo "==> Running web image"
docker inspect livetv_web --format 'image={{.Image}} started={{.State.StartedAt}}' 2>/dev/null \
  || sudo docker inspect livetv_web --format 'image={{.Image}} started={{.State.StartedAt}}'
