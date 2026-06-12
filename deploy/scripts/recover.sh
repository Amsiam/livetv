#!/usr/bin/env bash
# Remove orphan containers from a failed compose recreate; restart app tier.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
COMPOSE=("$SCRIPT_DIR/compose.sh")

cd "$DEPLOY_DIR"

echo "==> Remove failed recreate orphans (hash-prefixed names, Created/Exited)"
while IFS= read -r line; do
  name="${line%% *}"
  status="${line#* }"
  case "$name" in
    *_deploy_* | *-deploy-*)
      echo "  rm $name ($status)"
      docker rm -f "$name" 2>/dev/null || sudo docker rm -f "$name"
      ;;
  esac
done < <(docker ps -a --format '{{.Names}} {{.Status}}' | grep -E 'deploy' || true)

echo "==> Keep postgres/redis running; rebuild app tier"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" up -d --no-recreate postgres redis
"${COMPOSE[@]}" -f "$COMPOSE_FILE" up -d --build web nginx celery-worker celery-beat

echo "==> Status"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" ps

echo ""
echo "Run ./scripts/health-check.sh when all services show Up."
