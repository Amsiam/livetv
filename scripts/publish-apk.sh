#!/usr/bin/env bash
# Build release APK and publish to the API server (media + App release row).
#
# Local backend (runserver / dev):
#   ./scripts/publish-apk.sh https://api.yourdomain.com
#
# Production Docker on a remote VPS:
#   ./scripts/publish-apk.sh https://api.yourdomain.com --remote deploy@your-vps
#
# Optional: pass extra args to flutter build (after API URL).
set -euo pipefail

API_URL="${1:?Usage: $0 <API_BASE_URL> [--remote user@host] [flutter build args...]}"
shift

REMOTE=""
BUILD_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)
      REMOTE="${2:?--remote requires user@host}"
      shift 2
      ;;
    *)
      BUILD_ARGS+=("$1")
      shift
      ;;
  esac
done

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUBSPEC="$ROOT/app/pubspec.yaml"
APK="$ROOT/app/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk"

PUBLIC_API_URL="${API_URL%/}"
PUBLIC_API_URL="${PUBLIC_API_URL%/v1}"

VERSION_LINE="$(grep '^version:' "$PUBSPEC" | awk '{print $2}')"
VERSION_NAME="${VERSION_LINE%%+*}"
BUILD_NUMBER="${VERSION_LINE##*+}"

echo "==> Building APK (API_BASE_URL=${PUBLIC_API_URL}/v1)"
"$ROOT/scripts/flutter-build-apk.sh" "$PUBLIC_API_URL" "${BUILD_ARGS[@]}"

if [[ ! -f "$APK" ]]; then
  echo "APK not found: $APK" >&2
  exit 1
fi

publish_local() {
  echo "==> Publishing to local backend media/"
  (
    cd "$ROOT/backend"
    export PUBLIC_API_URL
    uv run python manage.py publish_app_release \
      --apk "$APK" \
      --version-name "$VERSION_NAME" \
      --build-number "$BUILD_NUMBER" \
      "$@"
  )
}

publish_remote() {
  local remote_apk="/tmp/livetv-publish-b${BUILD_NUMBER}.apk"
  echo "==> Copying APK to $REMOTE"
  scp "$APK" "$REMOTE:$remote_apk"

  echo "==> Registering release in Docker (PUBLIC_API_URL=$PUBLIC_API_URL)"
  ssh "$REMOTE" bash -s <<EOF
set -euo pipefail
cd /opt/live-tv/deploy
CONTAINER=\$(docker compose -f docker-compose.prod.yml ps -q web)
docker cp "$remote_apk" "\$CONTAINER:/tmp/publish.apk"
docker compose -f docker-compose.prod.yml exec -T \
  -e PUBLIC_API_URL="$PUBLIC_API_URL" \
  web uv run python manage.py publish_app_release \
  --apk /tmp/publish.apk \
  --version-name "$VERSION_NAME" \
  --build-number "$BUILD_NUMBER" \
  $*
rm -f "$remote_apk"
EOF
}

if [[ -n "$REMOTE" ]]; then
  publish_remote
else
  publish_local
fi

echo "Done. Users on build < $BUILD_NUMBER will be offered update $VERSION_NAME."
