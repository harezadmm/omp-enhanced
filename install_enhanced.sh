#!/bin/bash
# Quick installer untuk OMP Enhanced Client

echo "================================================"
echo "  OMP Enhanced Client - Installer"
echo "================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Install it first."
    exit 1
fi

echo "✅ Python3 found: $(python3 --version)"

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Install it first."
    exit 1
fi

echo "✅ pip3 found"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip3 install openai --quiet

if [ $? -eq 0 ]; then
    echo "✅ openai library installed"
else
    echo "❌ Failed to install openai"
    exit 1
fi

# Make scripts executable
chmod +x omp_client_enhanced.py
chmod +x test_enhanced_features.py

echo ""
echo "✅ Scripts made executable"

# Create cache directory
mkdir -p /tmp/omp_cache
echo "✅ Cache directory created: /tmp/omp_cache"

# Check API keys
echo ""
echo "🔑 Checking API keys..."

KEYS_FOUND=0

if [ ! -z "$DEEPINFRA_API_KEY" ]; then
    echo "  ✅ DEEPINFRA_API_KEY found"
    KEYS_FOUND=$((KEYS_FOUND+1))
fi

if [ ! -z "$GROQ_API_KEY" ]; then
    echo "  ✅ GROQ_API_KEY found"
    KEYS_FOUND=$((KEYS_FOUND+1))
fi

if [ ! -z "$OPENROUTER_API_KEY" ]; then
    echo "  ✅ OPENROUTER_API_KEY found"
    KEYS_FOUND=$((KEYS_FOUND+1))
fi

if command -v ollama &> /dev/null; then
    echo "  ✅ Ollama found (local model)"
    KEYS_FOUND=$((KEYS_FOUND+1))
fi

if [ $KEYS_FOUND -eq 0 ]; then
    echo ""
    echo "⚠️  WARNING: No API keys found!"
    echo ""
    echo "Set at least one:"
    echo "  export DEEPINFRA_API_KEY='your_key'"
    echo "  export GROQ_API_KEY='your_key'"
    echo "  export OPENROUTER_API_KEY='your_key'"
    echo "  Or install Ollama for local inference"
    echo ""
else
    echo ""
    echo "✅ Found $KEYS_FOUND provider(s)"
fi

# Test installation
echo ""
echo "🧪 Testing installation..."
python3 -c "from omp_client_enhanced import OMPClientEnhanced; print('✅ Import successful')"

if [ $? -eq 0 ]; then
    echo ""
    echo "================================================"
    echo "  ✅ Installation Complete!"
    echo "================================================"
    echo ""
    echo "Quick start:"
    echo "  python3 omp_client_enhanced.py 'Write hello world' code"
    echo ""
    echo "Run tests:"
    echo "  python3 test_enhanced_features.py --quick"
    echo ""
    echo "Read docs:"
    echo "  cat ENHANCED_FEATURES.md"
    echo ""
else
    echo "❌ Installation test failed"
    exit 1
fi
