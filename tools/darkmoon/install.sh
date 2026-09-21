#!/usr/bin/env bash
# Dark-Moon Installer — ASCIT31/Dark-Moon autonomous pentest platform
# For LTX-Quasar Enterprise
set -euo pipefail

INSTALL_DIR="${1:-/opt/darkmoon}"

echo "[darkmoon] Installing ASCIT31/Dark-Moon to ${INSTALL_DIR}..."

# Clone repo
if [[ -d "$INSTALL_DIR" ]]; then
    echo "[darkmoon] Directory exists. Pulling latest..."
    git -C "$INSTALL_DIR" pull 2>/dev/null || echo "[darkmoon] Pull failed, continuing..."
else
    git clone https://github.com/ASCIT31/Dark-Moon.git "$INSTALL_DIR"
fi

# Run installer
cd "$INSTALL_DIR"
chmod +x install.sh setup.sh darkmoon.sh

echo "[darkmoon] To configure:"
echo "  cd $INSTALL_DIR && ./install.sh --init"
echo "[darkmoon] To run:"
echo "  $INSTALL_DIR/darkmoon.sh \"TARGET: https://target.com\""
