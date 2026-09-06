#!/bin/bash
# Quick installer for OMP Enhanced v2.0.0

set -e

echo "=========================================="
echo "  OMP Enhanced Skills Library Installer"
echo "  Version: 2.0.0"
echo "=========================================="
echo ""

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    OS="unknown"
fi

echo "Detected OS: $OS"
echo ""

# Check Hermes installation
if ! command -v hermes &> /dev/null; then
    echo "❌ Hermes Agent not found!"
    echo "Install from: https://hermes-agent.nousresearch.com/docs"
    exit 1
fi

echo "✅ Hermes Agent found: $(hermes --version)"
echo ""

# Detect Hermes profile
HERMES_DIR="$HOME/.hermes"
if [ ! -d "$HERMES_DIR" ]; then
    echo "❌ Hermes directory not found at $HERMES_DIR"
    exit 1
fi

# Ask for profile or use default
echo "Available profiles:"
ls -1 "$HERMES_DIR/profiles/" 2>/dev/null || echo "  (default profile)"
echo ""
read -p "Enter profile name (press Enter for default): " PROFILE

if [ -z "$PROFILE" ]; then
    SKILLS_DIR="$HERMES_DIR/skills"
    echo "Using default profile"
else
    SKILLS_DIR="$HERMES_DIR/profiles/$PROFILE/skills"
    echo "Using profile: $PROFILE"
fi

# Create skills directory if not exists
mkdir -p "$SKILLS_DIR"

# Check if repository is cloned
if [ ! -d "skills" ]; then
    echo "❌ skills/ directory not found"
    echo "Run this script from omp-enhanced directory"
    exit 1
fi

# Backup existing skills (optional)
read -p "Backup existing skills? (y/N): " BACKUP
if [[ "$BACKUP" =~ ^[Yy]$ ]]; then
    BACKUP_DIR="$HOME/hermes-skills-backup-$(date +%Y%m%d-%H%M%S)"
    echo "Creating backup at: $BACKUP_DIR"
    cp -r "$SKILLS_DIR" "$BACKUP_DIR"
    echo "✅ Backup created"
fi

# Copy skills
echo ""
echo "Installing skills..."
cp -r skills/* "$SKILLS_DIR/"

# Count installed skills
SKILL_COUNT=$(find "$SKILLS_DIR" -name "SKILL.md" | wc -l)

echo ""
echo "=========================================="
echo "  Installation Complete! 🎉"
echo "=========================================="
echo ""
echo "📊 Stats:"
echo "  - Skills installed: $SKILL_COUNT"
echo "  - Installation path: $SKILLS_DIR"
echo ""
echo "📚 Next steps:"
echo "  1. Read QUICK_START.md for usage guide"
echo "  2. Browse SKILLS_INDEX.md for skill catalog"
echo "  3. Run: hermes chat"
echo "  4. Try: skill_view(name='apk-modding-workflow')"
echo ""
echo "🔗 Documentation:"
echo "  - Quick Start: QUICK_START.md"
echo "  - Skills Index: SKILLS_INDEX.md"
echo "  - Installation: docs/INSTALLATION.md"
echo "  - Contributing: CONTRIBUTING.md"
echo ""
echo "Happy hacking! 🚀"
