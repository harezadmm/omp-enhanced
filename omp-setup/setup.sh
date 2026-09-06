#!/bin/bash
# OMP Skills Setup - Quick Install Script
# Run: bash setup.sh [profile_name]

PROFILE="${1:-default}"

echo "🚀 OMP Skills Setup"
echo "   Installing 103 Hermes Agent Skills"
echo "   Target Profile: $PROFILE"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found!"
    exit 1
fi

# Check package exists
if [ ! -f "omp_skills/all_skills.json" ]; then
    echo "❌ OMP package not found!"
    echo "   Make sure you're in /root/omp-setup directory"
    exit 1
fi

# Run installer
python3 omp_installer.py "$PROFILE"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. hermes skills list          # Verify installation"
echo "  2. hermes skills search <term> # Search skills"
echo "  3. Start using skills in your agent"
echo ""
echo "Package info:"
echo "  - 103 skills installed"
echo "  - Categories: security, creative, productivity, github, mlops, etc"
echo "  - Size: 5.18 MB"
echo ""
