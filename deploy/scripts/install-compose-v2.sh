#!/usr/bin/env bash
# Install Docker Compose v2 (plugin). Use when apt has no docker-compose-plugin package.
set -euo pipefail

if docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 already installed:"
  docker compose version
  exit 0
fi

echo "==> Installing Docker Compose v2 plugin (manual binary)"

arch="$(uname -m)"
case "$arch" in
  x86_64) compose_arch="x86_64" ;;
  aarch64 | arm64) compose_arch="aarch64" ;;
  *)
    echo "Unsupported CPU architecture: $arch" >&2
    exit 1
    ;;
esac

version="${DOCKER_COMPOSE_VERSION:-v2.32.4}"
plugin_dir="/usr/local/lib/docker/cli-plugins"
plugin_path="$plugin_dir/docker-compose"
url="https://github.com/docker/compose/releases/download/${version}/docker-compose-linux-${compose_arch}"

sudo mkdir -p "$plugin_dir"
sudo curl -fsSL "$url" -o "$plugin_path"
sudo chmod +x "$plugin_path"

echo "==> Installed to $plugin_path"
docker compose version

echo ""
echo "Optional: remove broken compose v1"
echo "  sudo apt-get remove -y docker-compose"
