#!/usr/bin/env bash
# Katana Installer — projectdiscovery/katana next-gen crawler
# For LTX-Quasar Enterprise — installed to /root/.local/bin/
set -euo pipefail

KATANA_VERSION="${1:-latest}"
INSTALL_DIR="${HOME}/.local/bin"

echo "[katana] Installing projectdiscovery/katana (${KATANA_VERSION})..."

# Check Go
if ! command -v go &>/dev/null; then
    echo "[katana] Go not found. Installing..."
    if command -v snap &>/dev/null; then
        sudo snap install go --classic
    else
        echo "[katana] Install Go manually: https://go.dev/dl/"
        exit 1
    fi
fi

# Pre-built binary (fastest)
KATANA_URL="https://github.com/projectdiscovery/katana/releases/latest/download/katana_linux_amd64.zip"
if curl -fsSL "$KATANA_URL" -o /tmp/katana.zip 2>/dev/null; then
    unzip -o /tmp/katana.zip -d "$INSTALL_DIR/" katana 2>/dev/null && \
        chmod +x "$INSTALL_DIR/katana" && \
        echo "[katana] Installed from pre-built binary: $INSTALL_DIR/katana" || \
        echo "[katana] Binary install failed, trying go install..."
else
    # Fallback: go install
    CGO_ENABLED=1 go install github.com/projectdiscovery/katana/cmd/katana@latest 2>/dev/null && \
        echo "[katana] Installed via go install" || \
        echo "[katana] Both methods failed. Check Go version (needs 1.21+)"
fi

# Verify
if command -v katana &>/dev/null || [[ -x "$INSTALL_DIR/katana" ]]; then
    echo "[katana] Version: $($INSTALL_DIR/katana -version 2>&1)"
    echo "[katana] Done."
else
    echo "[katana] Install failed."
fi
