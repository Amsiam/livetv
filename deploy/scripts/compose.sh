#!/usr/bin/env bash
# Docker Compose v2 plugin is required (docker-compose v1 breaks on Engine 29+).
set -euo pipefail

if docker compose version >/dev/null 2>&1; then
  exec docker compose "$@"
fi

if command -v docker-compose >/dev/null 2>&1; then
  v1_version="$(docker-compose version --short 2>/dev/null || true)"
  if [[ -z "$v1_version" || "$v1_version" == 1.* ]]; then
    echo "Error: docker-compose v1 (${v1_version:-unknown}) is installed but incompatible" >&2
    echo "with recent Docker Engine (recreate fails with KeyError: 'ContainerConfig')." >&2
    echo "" >&2
    echo "Install Compose v2:" >&2
    echo "  ./scripts/install-compose-v2.sh" >&2
    echo "Or add Docker apt repo, then: apt install -y docker-compose-plugin" >&2
    echo "Then remove v1: sudo apt-get remove -y docker-compose" >&2
    exit 1
  fi
  exec docker-compose "$@"
fi

echo "Error: Docker Compose v2 plugin is not installed." >&2
echo "  cd deploy && ./scripts/install-compose-v2.sh" >&2
exit 1
