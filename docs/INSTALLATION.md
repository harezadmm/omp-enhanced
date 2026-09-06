# Installation Guide

Step-by-step installation untuk OMP Enhanced skills library.

## Prerequisites

### Required
- **Hermes Agent** - Framework untuk running skills
- **Git** - Version control
- **Python 3.12+** - Beberapa skills butuh Python (avoid 3.14 karena compatibility issues)

### Optional (tergantung skills yang dipakai)
- **APKTool** - APK modding
- **Frida** - Runtime hooking
- **Node.js** - JavaScript/TypeScript projects
- **Docker** - Containerized environments
- **Java JDK** - APK signing

## Installation Methods

### Method 1: Quick Install (Recommended)

```bash
# Clone repository
git clone https://github.com/your-org/omp-enhanced.git
cd omp-enhanced

# Copy to default Hermes profile
cp -r skills/* ~/.hermes/skills/

# Verify installation
hermes skills list
```

### Method 2: Profile-Specific Install

```bash
# Clone repository
git clone https://github.com/your-org/omp-enhanced.git
cd omp-enhanced

# Copy to specific profile (contoh: umi2)
PROFILE="umi2"
cp -r skills/* ~/.hermes/profiles/$PROFILE/skills/

# Verify
hermes skills list --profile $PROFILE
```

### Method 3: Symlink (For Development)

```bash
# Clone repository
git clone https://github.com/your-org/omp-enhanced.git
cd omp-enhanced

# Create symlink (updates automatically dengan git pull)
ln -s $(pwd)/skills ~/.hermes/skills/omp-enhanced

# Verify
hermes skills list
```

## Platform-Specific Setup

### Linux (Ubuntu/Debian)

```bash
# Update system
sudo apt update

# Install dependencies
sudo apt install -y git python3 python3-pip openjdk-17-jdk

# Install APKTool
wget https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool
wget https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar
chmod +x apktool
sudo mv apktool apktool_2.9.3.jar /usr/local/bin/

# Install Frida
pip3 install frida-tools

# Install SQLMap
git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git ~/sqlmap
echo 'alias sqlmap="python3 ~/sqlmap/sqlmap.py"' >> ~/.bashrc
```

### macOS

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install git python@3.12 openjdk

# Install APKTool
brew install apktool

# Install Frida
pip3 install frida-tools

# Install SQLMap
brew install sqlmap
```

### Windows (WSL2 Recommended)

```bash
# Install WSL2 first: https://aka.ms/wsl2

# Inside WSL2, follow Linux instructions
sudo apt update
sudo apt install -y git python3 python3-pip openjdk-17-jdk

# Or use native Windows with Python from python.org
# Download APKTool from: https://ibotpeaches.github.io/Apktool/
```

### Android (Termux)

```bash
# Update Termux
pkg update && pkg upgrade

# Install dependencies
pkg install -y git python openjdk-17

# Install Hermes Agent
pip install hermes-agent

# Clone skills
git clone https://github.com/your-org/omp-enhanced.git
cd omp-enhanced
cp -r skills/* ~/.hermes/skills/
```

## Skill-Specific Setup

### APK Modding Skills

```bash
# APKTool (decompile/recompile)
# Linux/Mac: installed above
# Windows: Download from https://ibotpeaches.github.io/Apktool/

# Uber APK Signer (signing APKs)
wget https://github.com/patrickfav/uber-apk-signer/releases/latest/download/uber-apk-signer.jar
chmod +x uber-apk-signer.jar
sudo mv uber-apk-signer.jar /usr/local/bin/

# Frida Server (for hooking)
# Download dari: https://github.com/frida/frida/releases
# Push to device: adb push frida-server /data/local/tmp/
```

### Web Pentesting Skills

```bash
# SQLMap
git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git ~/sqlmap

# Burp Suite Community (optional)
# Download from: https://portswigger.net/burp/communitydownload

# Browser tools
pip install playwright
playwright install
```

### GitHub Skills

```bash
# GitHub CLI
# Linux
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# macOS
brew install gh

# Authenticate
gh auth login
```

### Document Skills

```bash
# Python libraries
pip install python-docx openpyxl python-pptx PyPDF2

# Office conversion tools (optional)
sudo apt install libreoffice  # Linux
brew install libreoffice      # macOS
```

### Creative Skills

```bash
# ASCII art tools
pip install pyfiglet art

# p5.js (runs in browser, no install needed)

# Manim (video animations)
pip install manim

# Excalidraw (browser-based, no install needed)
```

## Verification

### Test Basic Functionality

```bash
# Start Hermes
hermes chat

# In conversation, test skill loading:
> skill_view(name='apk-modding-workflow')
> skills_list(category='security')
```

### Test Specific Skills

```bash
# Test APK modding
apktool --version

# Test Frida
frida --version

# Test SQLMap
python3 ~/sqlmap/sqlmap.py --version

# Test GitHub CLI
gh --version

# Test Python libraries
python3 -c "import docx, openpyxl, pptx, PyPDF2; print('All libraries OK')"
```

## Troubleshooting

### Issue: Skills not showing up

```bash
# Check Hermes profile
hermes status

# Check skills directory
ls -la ~/.hermes/skills/

# Re-copy skills
cp -r /path/to/omp-enhanced/skills/* ~/.hermes/skills/

# Restart Hermes
hermes restart
```

### Issue: APKTool not working

```bash
# Check Java version (needs 8+)
java -version

# Reinstall APKTool
wget https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar
sudo mv apktool_2.9.3.jar /usr/local/bin/apktool.jar

# Create wrapper script
echo '#!/bin/bash\njava -jar /usr/local/bin/apktool.jar "$@"' | sudo tee /usr/local/bin/apktool
sudo chmod +x /usr/local/bin/apktool
```

### Issue: Frida not connecting

```bash
# Check Frida versions match (PC and device)
frida --version
adb shell /data/local/tmp/frida-server --version

# Reinstall matching versions
pip install frida-tools==16.1.4  # example version
# Download matching frida-server from GitHub releases
```

### Issue: Python compatibility (3.14)

```bash
# Install Python 3.12
sudo apt install python3.12 python3.12-venv

# Create virtual environment
python3.12 -m venv ~/.hermes/venv
source ~/.hermes/venv/bin/activate
pip install hermes-agent

# Use this venv for Hermes
hermes config set python_path ~/.hermes/venv/bin/python3
```

### Issue: Permission denied

```bash
# Fix Hermes directory permissions
chmod -R 755 ~/.hermes/

# Fix script permissions
find ~/.hermes/skills/ -name "*.sh" -exec chmod +x {} \;
find ~/.hermes/skills/ -name "*.py" -exec chmod +x {} \;
```

## Updates

### Update Skills Library

```bash
# Navigate to clone
cd /path/to/omp-enhanced

# Pull latest changes
git pull origin main

# Re-copy to Hermes
cp -r skills/* ~/.hermes/skills/

# Or if using symlink, no action needed (auto-updates)
```

### Update Specific Skill

```bash
# Pull updates
cd /path/to/omp-enhanced
git pull

# Copy specific skill
cp -r skills/security/apk-modding-workflow ~/.hermes/skills/security/
```

## Uninstallation

### Remove All Skills

```bash
# Backup first (optional)
cp -r ~/.hermes/skills/ ~/hermes-skills-backup/

# Remove OMP Enhanced skills
rm -rf ~/.hermes/skills/security/apk-*
rm -rf ~/.hermes/skills/security/frida-*
# etc... or remove entire categories

# Or remove all
rm -rf ~/.hermes/skills/*
```

### Remove Specific Category

```bash
# Remove security skills
rm -rf ~/.hermes/skills/security/

# Remove creative skills
rm -rf ~/.hermes/skills/creative/
```

## Next Steps

After installation:

1. Read [QUICK_START.md](../QUICK_START.md) untuk basic usage
2. Browse [SKILLS_INDEX.md](../SKILLS_INDEX.md) untuk available skills
3. Try example tasks dari documentation
4. Check skill-specific SKILL.md files untuk detailed workflows

---

**Installation Version:** 1.0.0  
**Last Updated:** 2026-09-06
