#!/usr/bin/env bash
# Use Docker Compose v2 plugin when available, else standalone docker-compose.
set -euo pipefail

if docker compose version >/dev/null 2>&1; then
  exec docker compose "$@"
fi

if command -v docker-compose >/dev/null 2>&1; then
  exec docker-compose "$@"
fi

echo "Error: Docker Compose is not installed." >&2
echo "Install the Compose plugin (recommended):" >&2
echo "  sudo apt-get update && sudo apt-get install -y docker-compose-plugin" >&2
echo "Or the standalone binary:" >&2
echo "  sudo apt-get install -y docker-compose" >&2
exit 1
