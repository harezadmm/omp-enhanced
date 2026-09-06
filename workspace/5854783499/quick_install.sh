#!/bin/bash
# Quick installer untuk jailbreak Hermes Agent
# Usage: ./quick_install.sh

echo "=================================================="
echo "🔓 HERMES JAILBREAK - QUICK INSTALLER"
echo "=================================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 tidak ditemukan. Install dulu."
    exit 1
fi

# Run installer
echo ""
echo "Jalankan installer..."
echo ""

python3 jailbreak_installer.py --auto

echo ""
echo "=================================================="
echo "✅ DONE!"
echo "=================================================="
echo ""
echo "Restart Hermes sekarang untuk apply changes."
