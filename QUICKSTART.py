"""
Quick Start Guide - Security Bot Setup
Panduan lengkap dari zero hingga bot running
"""

# ============================================================================
# STEP 1: SETUP SERVER/VPS
# ============================================================================

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3 python3-pip python3-venv -y

# Install Java (untuk APK tools)
sudo apt install openjdk-17-jre-headless -y

# Verify installations
python3 --version  # Should be 3.9+
java -version      # Should be Java 17+

# ============================================================================
# STEP 2: INSTALL DEPENDENCIES
# ============================================================================

# Create project directory
mkdir -p /root/security_bot
cd /root/security_bot

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install python-telegram-bot==20.7 aiohttp cloudscraper paramiko requests

# Install Frida tools
pip install frida-tools objection

# ============================================================================
# STEP 3: INSTALL APK TOOLS
# ============================================================================

# APKTool
wget https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool -O /usr/local/bin/apktool
chmod +x /usr/local/bin/apktool

# Download APKTool JAR
wget https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar -O /usr/local/bin/apktool.jar

# Uber APK Signer
wget https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar -O /usr/local/bin/uber-apk-signer.jar

# Verify
apktool --version
java -jar /usr/local/bin/uber-apk-signer.jar --version

# ============================================================================
# STEP 4: SETUP BOT FILES
# ============================================================================

# Download atau copy files
cd /root/security_bot

# Files needed:
# - telegram_bot_integration.py (main bot)
# - bot_advanced_modules.py (modules)

# ============================================================================
# STEP 5: CREATE BOT TOKEN
# ============================================================================

# 1. Open Telegram, search @BotFather
# 2. Send /newbot
# 3. Follow instructions:
#    - Name: UmiAgent Security Bot
#    - Username: your_bot_name_bot
# 4. Copy token: 7123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw

# ============================================================================
# STEP 6: GET YOUR USER ID
# ============================================================================

# 1. Open Telegram, search @userinfobot
# 2. Send /start
# 3. Copy your User ID: 7570665912

# ============================================================================
# STEP 7: CONFIGURE BOT
# ============================================================================

# Edit telegram_bot_integration.py
nano telegram_bot_integration.py

# Scroll to bottom, find:
if __name__ == "__main__":
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # ← Paste token di sini
    AUTHORIZED_USERS = [
        7570665912,  # ← Paste user ID di sini
    ]

# Save: Ctrl+O, Enter, Ctrl+X

# ============================================================================
# STEP 8: TEST RUN BOT
# ============================================================================

# Activate venv if not activated
source /root/security_bot/venv/bin/activate

# Run bot
python3 telegram_bot_integration.py

# You should see:
# 🚀 Security Bot starting...
# INFO:telegram.ext.Application:Application started

# Open Telegram → Search your bot → Send /start
# If working, you'll get welcome message ✅

# Stop bot: Ctrl+C

# ============================================================================
# STEP 9: SETUP SYSTEMD SERVICE (PRODUCTION)
# ============================================================================

# Create service file
sudo nano /etc/systemd/system/security-bot.service

# Paste this:
"""
[Unit]
Description=UmiAgent Security Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/security_bot
ExecStart=/root/security_bot/venv/bin/python3 /root/security_bot/telegram_bot_integration.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

# Save: Ctrl+O, Enter, Ctrl+X

# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable security-bot

# Start bot
sudo systemctl start security-bot

# Check status
sudo systemctl status security-bot

# Should show:
# ● security-bot.service - UmiAgent Security Bot
#    Loaded: loaded
#    Active: active (running)

# ✅ Bot now running 24/7!

# ============================================================================
# STEP 10: USEFUL COMMANDS
# ============================================================================

# Check bot status
sudo systemctl status security-bot

# View live logs
sudo journalctl -u security-bot -f

# Restart bot
sudo systemctl restart security-bot

# Stop bot
sudo systemctl stop security-bot

# Disable auto-start
sudo systemctl disable security-bot

# View last 50 log lines
sudo journalctl -u security-bot -n 50

# Check if bot is running
ps aux | grep telegram_bot

# ============================================================================
# STEP 11: FIREWALL (OPTIONAL BUT RECOMMENDED)
# ============================================================================

# Allow SSH only
sudo ufw allow 22/tcp
sudo ufw enable

# Bot doesn't need open ports (outgoing only)
# Only Telegram API connections

# ============================================================================
# STEP 12: SECURITY HARDENING
# ============================================================================

# 1. Restrict file permissions
chmod 600 /root/security_bot/telegram_bot_integration.py
chmod 600 /root/security_bot/bot_advanced_modules.py

# 2. Use environment variables for token (recommended)
nano /root/security_bot/.env

# Add:
BOT_TOKEN=7123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw

# Save and protect
chmod 600 /root/security_bot/.env

# 3. Update bot code to load from .env:
# Add to telegram_bot_integration.py:
"""
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
"""

# Install python-dotenv:
pip install python-dotenv

# ============================================================================
# TROUBLESHOOTING COMMON ISSUES
# ============================================================================

# Issue 1: Module not found error
# Solution:
pip install python-telegram-bot aiohttp
# Or check if venv activated

# Issue 2: Bot not responding
# Solution:
sudo systemctl status security-bot
sudo journalctl -u security-bot -n 50
# Check for errors in logs

# Issue 3: "Unauthorized" message
# Solution:
# - Verify user ID in AUTHORIZED_USERS
# - Restart bot after config change
sudo systemctl restart security-bot

# Issue 4: APKTool not found
# Solution:
which apktool
# If not found, reinstall:
wget https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool -O /usr/local/bin/apktool
chmod +x /usr/local/bin/apktool

# Issue 5: Python version too old
# Solution on Ubuntu 20.04:
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv
python3.11 -m venv venv

# ============================================================================
# MAINTENANCE
# ============================================================================

# Update bot code
cd /root/security_bot
nano telegram_bot_integration.py
# Make changes
sudo systemctl restart security-bot

# Update dependencies
source venv/bin/activate
pip install --upgrade python-telegram-bot aiohttp

# Backup configuration
tar -czf security_bot_backup_$(date +%Y%m%d).tar.gz /root/security_bot/
# Move backup to safe location

# View disk usage
du -sh /root/security_bot/

# Clean old logs (if too large)
sudo journalctl --vacuum-time=7d  # Keep last 7 days only

# ============================================================================
# MONITORING SETUP (OPTIONAL)
# ============================================================================

# Create monitoring script
cat > /root/check_bot.sh << 'EOF'
#!/bin/bash
if ! systemctl is-active --quiet security-bot; then
    echo "Bot is down! Restarting..."
    systemctl start security-bot
    # Optional: Send alert via Telegram
    curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
         -d chat_id=7570665912 \
         -d text="⚠️ Security bot was down and has been restarted"
fi
EOF

chmod +x /root/check_bot.sh

# Add to crontab (check every 5 minutes)
crontab -e
# Add line:
*/5 * * * * /root/check_bot.sh

# ============================================================================
# PERFORMANCE OPTIMIZATION
# ============================================================================

# Limit memory usage (optional)
# Edit service file:
sudo nano /etc/systemd/system/security-bot.service

# Add under [Service]:
MemoryMax=500M
MemoryHigh=400M

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart security-bot

# Monitor resource usage
htop
# Or
top -p $(pgrep -f telegram_bot)

# ============================================================================
# MULTI-BOT SETUP (ADVANCED)
# ============================================================================

# Run multiple bot instances with different tokens

# Bot 1: Security Tools
# /root/security_bot/

# Bot 2: Different purpose
# /root/another_bot/

# Create separate systemd service for each
# sudo nano /etc/systemd/system/security-bot-2.service
# Change WorkingDirectory and ExecStart paths

# ============================================================================
# DEPLOYMENT CHECKLIST
# ============================================================================

# Before going live, verify:

# ✅ 1. Bot token configured correctly
grep "BOT_TOKEN" /root/security_bot/telegram_bot_integration.py

# ✅ 2. Authorized users list updated
grep "AUTHORIZED_USERS" /root/security_bot/telegram_bot_integration.py

# ✅ 3. All dependencies installed
pip list | grep telegram
pip list | grep aiohttp

# ✅ 4. APK tools working
apktool --version
java -jar /usr/local/bin/uber-apk-signer.jar --version

# ✅ 5. Service enabled and running
sudo systemctl status security-bot

# ✅ 6. Bot responds to /start command
# Test in Telegram

# ✅ 7. Logs show no errors
sudo journalctl -u security-bot -n 20

# ✅ 8. File permissions secure
ls -la /root/security_bot/

# ✅ 9. Firewall configured (if applicable)
sudo ufw status

# ✅ 10. Backup created
ls -lh /root/*backup*.tar.gz

# ============================================================================
# DONE! 🎉
# ============================================================================

# Your Security Bot is now:
# ✅ Running 24/7
# ✅ Auto-restarts on failure
# ✅ Auto-starts on server reboot
# ✅ Logging to journald
# ✅ Secured with authorization whitelist

# Test all features:
# /start
# /help
# /menu
# /ssl_bypass
# /sqli http://testphp.vulnweb.com/artists.php?artist=1
# /device_spoof
# /webshell php

# Enjoy! 🔐
