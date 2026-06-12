#!/usr/bin/env bash
# Expose local Django API via a temporary HTTPS URL (no port forwarding).
# Requires: cloudflared, Django runserver on port 8000
set -euo pipefail

API_PORT="${API_PORT:-8000}"
API_HOST="${API_HOST:-127.0.0.1}"

echo "==> Live TV — Cloudflare quick tunnel"
echo "    Origin: http://${API_HOST}:${API_PORT}"
echo ""
echo "When cloudflared prints a URL like https://xxxx.trycloudflare.com:"
echo "  1. backend/.env should include:"
echo "       DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,.trycloudflare.com"
echo "     (restart runserver — CSRF for *.trycloudflare.com is auto-trusted in DEBUG)"
echo "  2. Run Flutter (phone or any network):"
echo "       flutter run --dart-define=API_BASE_URL=https://xxxx.trycloudflare.com/v1"
echo ""
echo "Press Ctrl+C to stop the tunnel."
echo ""

exec cloudflared tunnel --url "http://${API_HOST}:${API_PORT}"
