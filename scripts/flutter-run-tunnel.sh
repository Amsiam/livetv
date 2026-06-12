#!/usr/bin/env bash
# Run Flutter app against a Cloudflare quick-tunnel API URL.
# Usage: ./scripts/flutter-run-tunnel.sh https://your-subdomain.trycloudflare.com
set -euo pipefail

TUNNEL_URL="${1:-}"
if [[ -z "$TUNNEL_URL" ]]; then
  echo "Usage: $0 https://your-subdomain.trycloudflare.com"
  exit 1
fi

# Strip trailing slash; ensure /v1 suffix
TUNNEL_URL="${TUNNEL_URL%/}"
API_BASE="${TUNNEL_URL%/v1}/v1"

echo "API_BASE_URL=$API_BASE"
cd "$(dirname "$0")/../app"
exec flutter run --dart-define="API_BASE_URL=$API_BASE" "${@:2}"
