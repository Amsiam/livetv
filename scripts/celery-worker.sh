#!/usr/bin/env sh
set -e
cd "$(dirname "$0")/../backend"
exec uv run celery -A config worker -l info
