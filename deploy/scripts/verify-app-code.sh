#!/usr/bin/env bash
# Confirm the running web container has expected backend code (not a stale image).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
COMPOSE=("$SCRIPT_DIR/compose.sh")
MARKER="${1:-AppReleaseAdminForm}"

cd "$DEPLOY_DIR"

echo "==> Host git commit"
git -C "$DEPLOY_DIR/.." log -1 --oneline

echo "==> Web container file check: releases/forms.py contains '${MARKER}'"
if ! "${COMPOSE[@]}" -f "$COMPOSE_FILE" exec -T web \
  grep -q "$MARKER" /app/releases/forms.py; then
  echo "ERROR: Running web container does not include the latest backend code." >&2
  echo "Run: cd $DEPLOY_DIR && FORCE_BUILD=1 ./scripts/deploy.sh" >&2
  exit 1
fi

echo "OK: livetv_web is running the expected backend code."
