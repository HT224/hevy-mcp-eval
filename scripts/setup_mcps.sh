#!/usr/bin/env bash
# Idempotent setup for third-party MCP servers vendored under ./vendor/.
# chrisdoc/hevy-mcp uses `npx -y hevy-mcp` so doesn't need to be cloned.
# tomtorggler is deferred to v0.2 (Cloudflare HTTP-only, different lifecycle).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR_DIR="$REPO_ROOT/vendor"
mkdir -p "$VENDOR_DIR"

clone_and_build() {
    local repo_url=$1
    local target_dir=$2
    local build_cmd=$3

    if [ -d "$VENDOR_DIR/$target_dir/.git" ]; then
        echo "✓ $target_dir already cloned; pulling latest"
        (cd "$VENDOR_DIR/$target_dir" && git pull --ff-only)
    else
        echo "→ cloning $repo_url"
        git clone --depth 1 "$repo_url" "$VENDOR_DIR/$target_dir"
    fi

    echo "→ npm install ($target_dir)"
    (cd "$VENDOR_DIR/$target_dir" && npm install --silent)

    if [ -n "$build_cmd" ]; then
        echo "→ $build_cmd ($target_dir)"
        (cd "$VENDOR_DIR/$target_dir" && eval "$build_cmd")
    fi
}

clone_and_build \
    https://github.com/meimakes/hevy-mcp-server \
    meimakes-hevy-mcp-server \
    "npm run build"

echo
echo "✓ Setup complete. Systems available:"
echo "  chrisdoc       → npx -y hevy-mcp"
echo "  meimakes       → node $VENDOR_DIR/meimakes-hevy-mcp-server/dist/index.js"
echo "  thin (control) → python -m systems.hevy_mcp_thin"
