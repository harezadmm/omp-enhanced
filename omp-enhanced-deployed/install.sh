#!/bin/bash
set -e

echo "Installing OMP-Enhanced..."

# Detect OS
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    OS="windows"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="darwin"
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi

# Download binary
REPO="harezadmm/omp-enhanced"
VERSION="latest"
INSTALL_DIR="$HOME/.omp-enhanced"

mkdir -p "$INSTALL_DIR"

if [ "$OS" == "windows" ]; then
    BINARY="omp-enhanced.exe"
else
    BINARY="omp-enhanced"
fi

echo "Downloading $BINARY for $OS..."
curl -fsSL "https://github.com/$REPO/releases/latest/download/$BINARY" -o "$INSTALL_DIR/$BINARY"
chmod +x "$INSTALL_DIR/$BINARY"

# Add to PATH
if [ "$OS" == "windows" ]; then
    echo "Add to PATH manually: $INSTALL_DIR"
else
    echo "export PATH=\"\$PATH:$INSTALL_DIR\"" >> "$HOME/.bashrc"
    echo "export PATH=\"\$PATH:$INSTALL_DIR\"" >> "$HOME/.zshrc" 2>/dev/null || true
fi

echo ""
echo "✓ OMP-Enhanced installed to $INSTALL_DIR"
echo "Run: omp-enhanced --help"
