#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/web"

npm ci
VITE_API_BASE_URL="${VITE_API_BASE_URL:-/v1}" npm run build

echo "Built web app → web/dist/"
