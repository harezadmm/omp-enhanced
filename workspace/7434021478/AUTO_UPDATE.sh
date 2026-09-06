#!/bin/bash
# Auto-update script untuk refresh predictions setiap jam

echo "🔄 AUTO-UPDATE SPACEMAN PREDICTIONS"
echo "===================================="
echo ""
echo "Script ini akan auto-refresh predictions setiap 1 jam"
echo ""

while true; do
    echo "⏰ $(date '+%Y-%m-%d %H:%M:%S') - Updating predictions..."
    python3 pragmatic_scraper.py
    echo ""
    echo "✅ Update complete! Next update in 1 hour..."
    echo ""
    sleep 3600  # Wait 1 hour
done
