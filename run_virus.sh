#!/bin/bash
# VIRUS WEBSITE - AUTO RUN SCRIPT
# Jalankan script ini di Termux untuk run server otomatis

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          🔥 VIRUS WEBSITE AUTO LAUNCHER 🔥                    ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "[*] Starting HTTP Server..."
echo "[*] Port: 8080"
echo ""
echo "📍 AKSES:"
echo "   http://localhost:8080/virus_website.html"
echo ""
echo "🔑 PIN untuk unlock: 2010"
echo ""
echo "⚠️  Tekan Ctrl+C untuk stop server"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check Python
if command -v python3 &> /dev/null; then
    python3 -m http.server 8080
elif command -v python &> /dev/null; then
    python -m http.server 8080
else
    echo "[ERROR] Python tidak ditemukan!"
    echo "[*] Install dengan: pkg install python"
    exit 1
fi
