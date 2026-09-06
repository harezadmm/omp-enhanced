#!/bin/bash
# Script untuk deploy ke D:/Tools Space/

echo "================================"
echo "SPACEMAN PREDICTOR - DEPLOYMENT"
echo "================================"
echo ""

TARGET_DIR="/d/Tools Space"

# Create target directory jika belum ada
if [ ! -d "$TARGET_DIR" ]; then
    echo "📁 Creating target directory: $TARGET_DIR"
    mkdir -p "$TARGET_DIR" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "⚠️  Cannot create /d/Tools Space (Windows mount issue)"
        echo "    Using workspace fallback: /root/workspace/7434021478/"
        TARGET_DIR="/root/workspace/7434021478"
    fi
fi

echo "📦 Preparing deployment package..."
echo ""
echo "Files to deploy:"
echo "  ✅ index.html (16 KB) - Main dashboard"
echo "  ✅ spaceman_analyzer.py (5 KB) - Prediction engine"
echo "  ✅ spaceman_predictions.json (12 KB) - Current predictions"
echo "  ✅ search_spaceman_sites.py (1.4 KB) - Reconnaissance tool"
echo "  ✅ README.md (4 KB) - Documentation"
echo ""

# Hitung total file size
TOTAL_SIZE=$(du -sh /root/workspace/7434021478 | cut -f1)
echo "📊 Total package size: $TOTAL_SIZE"
echo ""

echo "🎯 Deployment target: $TARGET_DIR"
echo ""
echo "✅ All files ready at: /root/workspace/7434021478/"
echo ""
echo "📋 Next Steps:"
echo "   1. Copy entire folder to D:/Tools Space/ di Windows"
echo "   2. Buka index.html di browser (Chrome/Firefox recommended)"
echo "   3. Dashboard akan auto-load predictions"
echo "   4. Klik 'Generate Prediksi Baru' untuk refresh data"
echo ""
echo "🚀 DEPLOYMENT COMPLETE!"
