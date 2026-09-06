# Deployment Guide - OMP Enhanced v2.0.0

Guide untuk deploy OMP Enhanced skills library ke berbagai environment.

## 🎯 Deployment Targets

### 1. Local Installation (Single User)
```bash
# Clone repository
git clone https://github.com/your-org/omp-enhanced.git
cd omp-enhanced

# Run installer
./install.sh

# Verify
hermes skills list | grep "apk-modding-workflow"
```

### 2. Multi-User Server
```bash
# Install to shared location
sudo mkdir -p /opt/hermes/skills
sudo cp -r skills/* /opt/hermes/skills/
sudo chown -R hermes:hermes /opt/hermes/skills

# Users symlink to shared skills
ln -s /opt/hermes/skills ~/.hermes/skills
```

### 3. Docker Container
```dockerfile
FROM python:3.12-slim

# Install Hermes
RUN pip install hermes-agent

# Copy skills
COPY skills/ /root/.hermes/skills/

# Install dependencies
RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
CMD ["hermes", "chat"]
```

Build & run:
```bash
docker build -t omp-enhanced:v2.0.0 .
docker run -it omp-enhanced:v2.0.0
```

### 4. GitHub Release
```bash
# Tag release
git tag -a v2.0.0 -m "Release v2.0.0: Complete skills library"

# Push tags
git push origin v2.0.0

# Create release archive
tar -czf omp-enhanced-v2.0.0.tar.gz \
  skills/ docs/ *.md \
  install.sh omp_client_enhanced.py omp_config.yaml

# Upload to GitHub releases
gh release create v2.0.0 \
  omp-enhanced-v2.0.0.tar.gz \
  --title "OMP Enhanced v2.0.0" \
  --notes-file RELEASE_NOTES.md
```

## 🔧 Environment-Specific Setup

### Development Environment
```bash
# Clone with dev branch
git clone -b develop https://github.com/your-org/omp-enhanced.git

# Symlink for auto-updates
ln -s $(pwd)/omp-enhanced/skills ~/.hermes/skills/omp-dev

# Enable verbose logging
hermes config set log_level DEBUG
```

### Production Environment
```bash
# Clone stable release
git clone --branch v2.0.0 https://github.com/your-org/omp-enhanced.git

# Install to profile
cp -r omp-enhanced/skills ~/.hermes/profiles/production/skills/

# Verify integrity
cd omp-enhanced && git verify-tag v2.0.0
```

## 📦 Distribution Methods

### Method 1: Direct Git Clone
```bash
git clone https://github.com/your-org/omp-enhanced.git
cd omp-enhanced && ./install.sh
```

### Method 2: Release Archive
```bash
wget https://github.com/your-org/omp-enhanced/releases/download/v2.0.0/omp-enhanced-v2.0.0.tar.gz
tar -xzf omp-enhanced-v2.0.0.tar.gz
cd omp-enhanced && ./install.sh
```

## 🌐 Platform-Specific Deployment

### Ubuntu/Debian Server
```bash
# Install dependencies
sudo apt update
sudo apt install -y python3.12 python3-pip git openjdk-17-jdk

# Install Hermes
pip3 install hermes-agent

# Deploy skills
git clone https://github.com/your-org/omp-enhanced.git /opt/omp-enhanced
cd /opt/omp-enhanced && ./install.sh
```

### Android/Termux
```bash
# Update packages
pkg update && pkg upgrade

# Install dependencies
pkg install python git openjdk-17

# Install Hermes
pip install hermes-agent

# Deploy skills
git clone https://github.com/your-org/omp-enhanced.git
cd omp-enhanced && bash install.sh
```

## 🔐 Security Considerations

### File Permissions
```bash
# Secure skills directory
chmod 755 ~/.hermes/skills/
find ~/.hermes/skills/ -type f -exec chmod 644 {} \;
find ~/.hermes/skills/ -type f -name "*.sh" -exec chmod 755 {} \;
```

### Sensitive Data
```bash
# Never commit credentials
echo "*.key" >> .gitignore
echo "*.pem" >> .gitignore
echo "credentials.json" >> .gitignore
```

## 📊 Monitoring & Maintenance

### Health Check
```bash
#!/bin/bash
# Check Hermes is running
hermes status || exit 1

# Check skills are loaded
SKILL_COUNT=$(hermes skills list | wc -l)
if [ "$SKILL_COUNT" -lt 100 ]; then
  echo "ERROR: Only $SKILL_COUNT skills loaded"
  exit 1
fi

echo "OK: $SKILL_COUNT skills loaded"
```

### Update Procedure
```bash
# Backup current skills
cp -r ~/.hermes/skills ~/.hermes/skills.backup

# Pull updates
cd omp-enhanced
git pull origin main

# Install updates
./install.sh

# Verify
hermes skills list | wc -l
```

## ✅ Post-Deployment Checklist

- [ ] Skills installed successfully
- [ ] All dependencies installed
- [ ] Hermes agent running
- [ ] Can load skills via `skill_view()`
- [ ] Test 5 random skills
- [ ] Documentation accessible
- [ ] Logging configured
- [ ] Backup created

---

**Deployment Version:** 1.0.0  
**Last Updated:** 2026-09-06  
**Tested Platforms:** Ubuntu 22.04, Debian 12, macOS 13+, Android/Termux
