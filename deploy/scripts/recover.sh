#!/usr/bin/env bash
# Recover from a failed compose recreate (orphans, exited web, nginx restart loop).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Restart Docker if containers cannot be removed"
if ! docker info >/dev/null 2>&1; then
  sudo systemctl restart docker
  sleep 3
fi

"$SCRIPT_DIR/roll-app-tier.sh"

echo ""
echo "==> Status"
"$SCRIPT_DIR/compose.sh" -f docker-compose.prod.yml ps
echo ""
echo "Run ./scripts/health-check.sh when all services show Up."
