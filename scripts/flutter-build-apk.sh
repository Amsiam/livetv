#!/usr/bin/env bash
# Build release APK with API URL baked in (required for real phones).
#
# Default: arm64 split APK (~32 MB), like Play Store per-device downloads.
# Use --universal for a single fat APK (~97 MB, all ABIs).
#
# Usage:
#   ./scripts/flutter-build-apk.sh https://your-api.example.com
#   ./scripts/flutter-build-apk.sh https://your-api.example.com --universal
#   ./scripts/flutter-build-apk.sh http://192.168.1.10:8000
set -euo pipefail

API_URL="${1:-}"
if [[ -z "$API_URL" ]]; then
  echo "Usage: $0 <API_BASE_URL> [--universal] [extra flutter build args...]"
  echo ""
  echo "Examples:"
  echo "  $0 https://api.yourdomain.com"
  echo "  $0 https://xxxx.trycloudflare.com"
  echo "  $0 http://192.168.1.10:8000   # phone on same Wi‑Fi as dev machine"
  echo "  $0 https://api.yourdomain.com --universal"
  echo ""
  echo "Note: plain 'flutter build apk' uses http://10.0.2.2:8000/v1"
  echo "      which only works on the Android emulator, not a real device."
  exit 1
fi
shift

UNIVERSAL=false
BUILD_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --universal)
      UNIVERSAL=true
      shift
      ;;
    *)
      BUILD_ARGS+=("$1")
      shift
      ;;
  esac
done

API_URL="${API_URL%/}"
API_BASE="${API_URL%/v1}/v1"

echo "Building APK with API_BASE_URL=$API_BASE"
cd "$(dirname "$0")/../app"

if [[ "$UNIVERSAL" == true ]]; then
  echo "Output: app-release.apk (all ABIs)"
  exec flutter build apk --dart-define="API_BASE_URL=$API_BASE" "${BUILD_ARGS[@]}"
fi

echo "Output: app-arm64-v8a-release.apk (arm64 only, ~32 MB)"
exec flutter build apk \
  --split-per-abi \
  --target-platform android-arm64 \
  --dart-define="API_BASE_URL=$API_BASE" \
  "${BUILD_ARGS[@]}"
