#!/bin/bash
# OMP Enhanced v2.0.0 - One-Line Installer
# Usage: curl -sSL https://your-url/quick_install.sh | bash

set -e

echo "🔥 OMP Enhanced v2.0.0 - Quick Installer"
echo "========================================="
echo ""

# Download package
PACKAGE_URL="${OMP_PACKAGE_URL:-/root/workspace/6432319873/omp_enhanced_v2.0.0.tar.gz}"
INSTALL_DIR="${OMP_INSTALL_DIR:-$HOME/omp_enhanced}"

echo "📦 Installing to: $INSTALL_DIR"

# Create install directory
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Extract package
if [ -f "$PACKAGE_URL" ]; then
    echo "📂 Extracting local package..."
    tar -xzf "$PACKAGE_URL"
else
    echo "🌐 Downloading package..."
    curl -sSL "$PACKAGE_URL" | tar -xz
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 required but not found"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -q openai 2>/dev/null || pip install -q openai

# Make scripts executable
chmod +x install_enhanced.sh verify_enhanced.py examples_enhanced.py

echo ""
echo "✅ Installation complete!"
echo ""
echo "📍 Location: $INSTALL_DIR"
echo ""
echo "🚀 Quick Start:"
echo "   cd $INSTALL_DIR"
echo "   export DEEPINFRA_API_KEY='your_key'"
echo "   python3 verify_enhanced.py"
echo "   python3 omp_client_enhanced.py 'Write hello world' code"
echo ""
echo "📚 Documentation:"
echo "   cat README_ENHANCED.md"
echo "   cat FINAL_DELIVERY.md"
echo ""
echo "🎯 Examples:"
echo "   python3 examples_enhanced.py"
echo ""
