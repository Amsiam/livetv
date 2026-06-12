#!/usr/bin/env bash
# Flutter web on a fixed localhost port (for stable CORS + bookmarks).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$ROOT/app"
WEB_PORT="${WEB_PORT:-37233}"
WEB_HOST="${WEB_HOST:-localhost}"
API_URL="${1:-https://tv.test71.xyz}"

API_BASE="${API_URL%/}"
if [[ "$API_BASE" != */v1 ]]; then
  API_BASE="${API_BASE}/v1"
fi

cd "$APP_DIR"

echo "==> Flutter web: http://${WEB_HOST}:${WEB_PORT}"
echo "==> API_BASE_URL=${API_BASE}"
echo ""
echo "Production API: add to deploy/.env CORS_ALLOWED_ORIGINS:"
echo "  https://tv.test71.xyz,http://localhost:${WEB_PORT}"
echo ""
echo "Tip: use R (hot restart), not r, after opening the video player."
echo ""

WASM_ARGS=()
if [[ "${USE_WASM:-1}" != "0" ]]; then
  WASM_ARGS=(--wasm)
  echo "==> Renderer: SkWasm (--wasm avoids CanvasKit webglcontextlost crashes)"
fi

exec flutter run -d chrome \
  "${WASM_ARGS[@]}" \
  --web-port="$WEB_PORT" \
  --web-hostname="$WEB_HOST" \
  --dart-define="API_BASE_URL=${API_BASE}" \
  "${@:2}"
