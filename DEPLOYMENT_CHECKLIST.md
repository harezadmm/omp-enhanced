# 🚀 Deployment Checklist - Security Bot

**Date:** 2026-09-06  
**Version:** 1.0.0

---

## Pre-Deployment Checklist

### ☐ 1. Server Requirements

- [ ] Ubuntu 20.04+ atau Debian 11+
- [ ] Python 3.9+
- [ ] Java 17+ (untuk APK tools)
- [ ] Minimal 2GB RAM
- [ ] Minimal 10GB disk space
- [ ] Root access atau sudo privileges

### ☐ 2. Accounts & Credentials

- [ ] Telegram account created
- [ ] Bot token obtained dari @BotFather
- [ ] User ID obtained dari @userinfobot
- [ ] Authorized user list prepared

### ☐ 3. Files Ready

- [ ] `telegram_bot_integration.py` - Main bot file
- [ ] `bot_advanced_modules.py` - Security modules
- [ ] `requirements.txt` - Python dependencies
- [ ] `quickstart.sh` - Automated setup script
- [ ] `.gitignore` - Exclude sensitive files

### ☐ 4. Configuration

- [ ] Bot token configured
- [ ] Authorized users list updated
- [ ] Environment variables set (optional)
- [ ] File permissions secured (chmod 600)

---

## Installation Steps

### ☐ Step 1: System Update
```bash
sudo apt update && sudo apt upgrade -y
```

### ☐ Step 2: Install Dependencies
```bash
# Python & Java
sudo apt install -y python3 python3-pip python3-venv openjdk-17-jre-headless

# Verify
python3 --version
java -version
```

### ☐ Step 3: Create Project Directory
```bash
mkdir -p /root/security_bot
cd /root/security_bot
```

### ☐ Step 4: Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### ☐ Step 5: Install Python Packages
```bash
pip install -r requirements.txt
```

### ☐ Step 6: Install APK Tools
```bash
# APKTool
wget https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool -O /usr/local/bin/apktool
chmod +x /usr/local/bin/apktool
wget https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar -O /usr/local/bin/apktool.jar

# Uber APK Signer
wget https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar -O /usr/local/bin/uber-apk-signer.jar
```

### ☐ Step 7: Copy Bot Files
```bash
# Upload files ke /root/security_bot/
# - telegram_bot_integration.py
# - bot_advanced_modules.py
```

### ☐ Step 8: Configure Bot
```bash
nano telegram_bot_integration.py

# Update:
# BOT_TOKEN = "YOUR_TOKEN"
# AUTHORIZED_USERS = [YOUR_USER_ID]
```

### ☐ Step 9: Test Bot
```bash
python3 telegram_bot_integration.py

# Test di Telegram: /start
# Ctrl+C untuk stop
```

### ☐ Step 10: Setup Systemd Service
```bash
sudo nano /etc/systemd/system/security-bot.service

# Paste service configuration
# Save & exit

sudo systemctl daemon-reload
sudo systemctl enable security-bot
sudo systemctl start security-bot
```

---

## Post-Deployment Verification

### ☐ 1. Service Status
```bash
sudo systemctl status security-bot
# Should show: active (running)
```

### ☐ 2. Bot Responds
```bash
# In Telegram:
/start
# Should receive welcome message
```

### ☐ 3. Core Features Work
```bash
/help          # Shows command list
/menu          # Shows interactive menu
/ssl_bypass    # Generates Frida script
/device_spoof  # Generates fingerprints
```

### ☐ 4. Logs Clean
```bash
sudo journalctl -u security-bot -n 50
# No errors or warnings
```

### ☐ 5. APK Tools Working
```bash
apktool --version
java -jar /usr/local/bin/uber-apk-signer.jar --version
```

---

## Security Hardening

### ☐ 1. File Permissions
```bash
chmod 600 /root/security_bot/telegram_bot_integration.py
chmod 600 /root/security_bot/bot_advanced_modules.py
chmod 600 /root/security_bot/.env  # If using .env
```

### ☐ 2. Firewall Configuration
```bash
sudo ufw allow 22/tcp  # SSH only
sudo ufw enable
sudo ufw status
```

### ☐ 3. Remove Sensitive Data from Logs
```bash
# Check no tokens in logs
sudo journalctl -u security-bot | grep -i token
# Should be empty
```

### ☐ 4. Backup Configuration
```bash
tar -czf security_bot_backup_$(date +%Y%m%d).tar.gz /root/security_bot/
# Move backup to safe location
```

---

## Monitoring Setup

### ☐ 1. Log Rotation
```bash
# Logs handled by systemd/journald
# Configure retention:
sudo nano /etc/systemd/journald.conf

# Add:
SystemMaxUse=500M
MaxRetentionSec=7day

sudo systemctl restart systemd-journald
```

### ☐ 2. Health Check Script
```bash
cat > /root/check_bot.sh << 'SCRIPT'
#!/bin/bash
if ! systemctl is-active --quiet security-bot; then
    systemctl start security-bot
    curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
         -d chat_id=YOUR_USER_ID \
         -d text="⚠️ Security bot restarted"
fi
SCRIPT

chmod +x /root/check_bot.sh

# Add to crontab
crontab -e
# Add: */5 * * * * /root/check_bot.sh
```

### ☐ 3. Resource Monitoring
```bash
# Install htop for easy monitoring
sudo apt install htop -y

# Check bot resources
htop -p $(pgrep -f telegram_bot)
```

---

## Performance Optimization

### ☐ 1. Memory Limits
```bash
sudo nano /etc/systemd/system/security-bot.service

# Add under [Service]:
MemoryMax=500M
MemoryHigh=400M

sudo systemctl daemon-reload
sudo systemctl restart security-bot
```

### ☐ 2. CPU Priority
```bash
# Add under [Service]:
Nice=-5
CPUSchedulingPolicy=fifo

sudo systemctl daemon-reload
sudo systemctl restart security-bot
```

---

## Troubleshooting Guide

### Issue 1: Bot Not Starting
```bash
# Check logs
sudo journalctl -u security-bot -n 50

# Common causes:
# - Missing dependencies
# - Wrong file paths
# - Invalid token
# - Python syntax errors
```

### Issue 2: "Unauthorized" Error
```bash
# Verify user ID
# Get from @userinfobot
# Update AUTHORIZED_USERS list
# Restart bot
sudo systemctl restart security-bot
```

### Issue 3: Commands Not Working
```bash
# Check bot is running
sudo systemctl status security-bot

# Check network connectivity
ping -c 3 api.telegram.org

# Restart bot
sudo systemctl restart security-bot
```

### Issue 4: High Memory Usage
```bash
# Check memory
free -h

# Restart bot
sudo systemctl restart security-bot

# Monitor
watch -n 5 'ps aux | grep telegram_bot'
```

### Issue 5: APK Modding Fails
```bash
# Verify tools installed
apktool --version
java -jar /usr/local/bin/uber-apk-signer.jar --version

# Check disk space
df -h

# Check logs for specific errors
sudo journalctl -u security-bot | grep -i apk
```

---

## Maintenance Schedule

### Daily
- [ ] Check bot status: `sudo systemctl status security-bot`
- [ ] Quick log review: `sudo journalctl -u security-bot --since today`

### Weekly
- [ ] Full log review: `sudo journalctl -u security-bot --since "7 days ago"`
- [ ] Check disk space: `df -h`
- [ ] Review resource usage: `htop`

### Monthly
- [ ] Update system: `sudo apt update && sudo apt upgrade`
- [ ] Update Python packages: `pip install --upgrade -r requirements.txt`
- [ ] Backup configuration: `tar -czf backup.tar.gz /root/security_bot/`
- [ ] Review and rotate logs: `sudo journalctl --vacuum-time=30d`

### Quarterly
- [ ] Security audit
- [ ] Review authorized users list
- [ ] Update bot features
- [ ] Performance optimization

---

## Emergency Procedures

### Bot Crashed
```bash
# 1. Check status
sudo systemctl status security-bot

# 2. View recent logs
sudo journalctl -u security-bot -n 100

# 3. Restart
sudo systemctl restart security-bot

# 4. If still failing, check manually
cd /root/security_bot
source venv/bin/activate
python3 telegram_bot_integration.py
# Watch for errors
```

### Server Under Attack
```bash
# 1. Stop bot immediately
sudo systemctl stop security-bot

# 2. Check connections
netstat -tunap | grep python

# 3. Block suspicious IPs
sudo ufw deny from <IP_ADDRESS>

# 4. Review logs for abuse
sudo journalctl -u security-bot | grep -E 'scan|exploit'

# 5. Restart when safe
sudo systemctl start security-bot
```

### Telegram API Rate Limit Hit
```bash
# Bot will auto-handle, but to manually check:
sudo journalctl -u security-bot | grep -i "rate"

# Wait 1 hour, then restart
sudo systemctl restart security-bot
```

---

## Rollback Procedure

### If Update Fails
```bash
# 1. Stop service
sudo systemctl stop security-bot

# 2. Restore from backup
cd /root
tar -xzf security_bot_backup_YYYYMMDD.tar.gz

# 3. Restart service
sudo systemctl start security-bot

# 4. Verify
sudo systemctl status security-bot
```

---

## Success Criteria

Bot deployment is successful when:

- ✅ Service is active and running
- ✅ Bot responds to /start command
- ✅ All core features work (/ssl_bypass, /sqli, /scan, etc)
- ✅ Logs show no errors
- ✅ APK tools are functional
- ✅ Memory usage < 200MB
- ✅ CPU usage < 5% idle
- ✅ Auto-restart on failure working
- ✅ Auto-start on boot working
- ✅ Authorized users can access
- ✅ Unauthorized users blocked

---

## Support

**Issue?** Contact: @sisuryaofficialkuu

**Documentation:**
- README_SECURITY_BOT.md - Full documentation
- UPDATE_GUIDE.md - Enhancement guide
- telegram_bot_skills.md - Features overview

**Logs Location:**
- Systemd: `sudo journalctl -u security-bot`
- Manual run: stdout/stderr

**Service Control:**
- Start: `sudo systemctl start security-bot`
- Stop: `sudo systemctl stop security-bot`
- Restart: `sudo systemctl restart security-bot`
- Status: `sudo systemctl status security-bot`
- Logs: `sudo journalctl -u security-bot -f`

---

**Deployment Date:** ___________  
**Deployed By:** ___________  
**Server:** ___________  
**Bot Username:** ___________  
**Status:** ___________

---

✅ **DEPLOYMENT COMPLETE!**
