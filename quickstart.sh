#!/bin/bash
# ============================================================================
# Quick Start Script - Automated Security Bot Setup
# Usage: bash quickstart.sh
# ============================================================================

set -e  # Exit on error

echo "🔐 UmiAgent Security Bot - Automated Setup"
echo "=========================================="
echo ""

# ============================================================================
# STEP 1: System Update
# ============================================================================

echo "📦 Step 1: Updating system..."
sudo apt update && sudo apt upgrade -y

echo "✅ System updated"
echo ""

# ============================================================================
# STEP 2: Install Dependencies
# ============================================================================

echo "📦 Step 2: Installing dependencies..."

# Python 3 and pip
sudo apt install -y python3 python3-pip python3-venv

# Java for APK tools
sudo apt install -y openjdk-17-jre-headless

# Other utilities
sudo apt install -y wget curl git screen

echo "✅ Dependencies installed"
echo ""

# ============================================================================
# STEP 3: Create Project Directory
# ============================================================================

echo "📁 Step 3: Creating project directory..."

PROJECT_DIR="/root/security_bot"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

echo "✅ Project directory created: $PROJECT_DIR"
echo ""

# ============================================================================
# STEP 4: Setup Python Virtual Environment
# ============================================================================

echo "🐍 Step 4: Setting up Python virtual environment..."

python3 -m venv venv
source venv/bin/activate

echo "✅ Virtual environment created"
echo ""

# ============================================================================
# STEP 5: Install Python Packages
# ============================================================================

echo "📦 Step 5: Installing Python packages..."

pip install --upgrade pip
pip install python-telegram-bot==20.7
pip install aiohttp
pip install cloudscraper
pip install paramiko
pip install requests
pip install frida-tools
pip install objection

echo "✅ Python packages installed"
echo ""

# ============================================================================
# STEP 6: Install APK Tools
# ============================================================================

echo "🔧 Step 6: Installing APK tools..."

# APKTool
echo "  Installing APKTool..."
wget -q https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool -O /usr/local/bin/apktool
chmod +x /usr/local/bin/apktool
wget -q https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar -O /usr/local/bin/apktool.jar

# Uber APK Signer
echo "  Installing Uber APK Signer..."
wget -q https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar -O /usr/local/bin/uber-apk-signer.jar

# Verify installations
if apktool --version &>/dev/null; then
    echo "  ✅ APKTool installed"
else
    echo "  ❌ APKTool installation failed"
fi

if java -jar /usr/local/bin/uber-apk-signer.jar --version &>/dev/null; then
    echo "  ✅ Uber APK Signer installed"
else
    echo "  ❌ Uber APK Signer installation failed"
fi

echo ""

# ============================================================================
# STEP 7: Download Bot Files
# ============================================================================

echo "📥 Step 7: Setting up bot files..."

# Check if files already exist
if [ ! -f "$PROJECT_DIR/telegram_bot_integration.py" ]; then
    echo "⚠️  Bot files not found in $PROJECT_DIR"
    echo "Please copy the following files to $PROJECT_DIR:"
    echo "  - telegram_bot_integration.py"
    echo "  - bot_advanced_modules.py"
    echo ""
    echo "After copying files, run this script again or continue manually."
    exit 1
fi

echo "✅ Bot files found"
echo ""

# ============================================================================
# STEP 8: Configuration
# ============================================================================

echo "⚙️  Step 8: Configuration"
echo ""
echo "Please provide the following information:"
echo ""

# Get bot token
read -p "Enter your Bot Token (from @BotFather): " BOT_TOKEN

# Get user ID
read -p "Enter your Telegram User ID (from @userinfobot): " USER_ID

# Validate inputs
if [ -z "$BOT_TOKEN" ] || [ -z "$USER_ID" ]; then
    echo "❌ Bot token and user ID are required!"
    exit 1
fi

# Update configuration in bot file
echo "Updating configuration..."

# Backup original file
cp telegram_bot_integration.py telegram_bot_integration.py.bak

# Replace token and user ID
sed -i "s/BOT_TOKEN = \".*\"/BOT_TOKEN = \"$BOT_TOKEN\"/" telegram_bot_integration.py
sed -i "s/7570665912/$USER_ID/" telegram_bot_integration.py

echo "✅ Configuration updated"
echo ""

# ============================================================================
# STEP 9: Test Run
# ============================================================================

echo "🧪 Step 9: Testing bot..."
echo ""
echo "Starting bot in test mode (will run for 10 seconds)..."
echo "Check your Telegram and send /start to your bot"
echo ""

timeout 10 python3 telegram_bot_integration.py || true

echo ""
echo "Test completed. If you received a response, bot is working! ✅"
echo ""

# ============================================================================
# STEP 10: Setup Systemd Service
# ============================================================================

echo "🔧 Step 10: Setting up systemd service..."

# Create service file
cat > /tmp/security-bot.service << EOF
[Unit]
Description=UmiAgent Security Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/telegram_bot_integration.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Install service
sudo mv /tmp/security-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable security-bot

echo "✅ Systemd service configured"
echo ""

# ============================================================================
# STEP 11: Start Service
# ============================================================================

echo "🚀 Step 11: Starting bot service..."

sudo systemctl start security-bot
sleep 2

# Check status
if sudo systemctl is-active --quiet security-bot; then
    echo "✅ Bot is running!"
else
    echo "❌ Bot failed to start. Check logs:"
    echo "    sudo journalctl -u security-bot -n 50"
    exit 1
fi

echo ""

# ============================================================================
# STEP 12: Final Summary
# ============================================================================

echo "=============================================="
echo "🎉 INSTALLATION COMPLETE!"
echo "=============================================="
echo ""
echo "📋 Summary:"
echo "  • Project directory: $PROJECT_DIR"
echo "  • Bot token: ${BOT_TOKEN:0:20}..."
echo "  • Authorized user: $USER_ID"
echo "  • Service status: $(systemctl is-active security-bot)"
echo ""
echo "🔧 Useful Commands:"
echo "  • Check status:    sudo systemctl status security-bot"
echo "  • View logs:       sudo journalctl -u security-bot -f"
echo "  • Restart bot:     sudo systemctl restart security-bot"
echo "  • Stop bot:        sudo systemctl stop security-bot"
echo ""
echo "📱 Next Steps:"
echo "  1. Open Telegram"
echo "  2. Search for your bot"
echo "  3. Send /start"
echo "  4. Send /help to see all commands"
echo "  5. Send /menu for interactive menu"
echo ""
echo "🔐 Security Bot Features:"
echo "  • SSL Pinning Bypass"
echo "  • Root Detection Bypass"
echo "  • SQL Injection Payloads"
echo "  • XSS Payloads"
echo "  • Web Shell Generators"
echo "  • Reverse Shell Generators"
echo "  • Port Scanner"
echo "  • Web Vulnerability Scanner"
echo "  • APK Modding Tools"
echo "  • Device Fingerprint Spoofing"
echo ""
echo "⚠️  Legal Warning:"
echo "  This bot is for authorized security testing only."
echo "  Unauthorized hacking is illegal. Use responsibly."
echo ""
echo "✅ Setup complete! Happy hacking! 🔐"
echo ""
