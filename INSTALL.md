# OMP Enhanced - Installation Guide

## Quick Install (One Command)

### Method 1: Bun (Recommended - Fastest)

```bash
git clone https://github.com/harezadmm/omp-enhanced.git && cd omp-enhanced && bun install.sh
```

### Method 2: Bash (Standard)

```bash
git clone https://github.com/harezadmm/omp-enhanced.git && cd omp-enhanced && bash install.sh
```

---

## What Gets Installed

✅ **126 Skills** deployed to `~/.omp/skills/`
✅ **System Prompt** (AGENTS.md) → `~/.omp/prompts/system.md`
✅ **Config Files** (.env + config.json) - optional interactive setup
✅ **PM2** process manager - optional

---

## Installation Steps

The installer will:

### Step 1: Deploy Skills (Automatic)
```bash
mkdir -p ~/.omp/skills
cp -r skills/* ~/.omp/skills/
# Result: 126 skills available
```

### Step 2: Load System Prompt (Automatic)
```bash
mkdir -p ~/.omp/prompts
cp AGENTS.md ~/.omp/prompts/system.md
```

### Step 3: API Configuration (Interactive)
```
Choose your AI provider:
1) OpenAI (GPT-4, GPT-3.5)
2) Anthropic (Claude)
3) Google (Gemini)
4) Skip (configure manually later)
```

Press `4` to skip and configure manually.

### Step 4: PM2 Installation (Optional)
```
Install PM2? [y/N]: n
```

Press `n` to skip PM2 (not needed for Hermes Agent integration).

---

## Post-Installation

### For Hermes Agent Users (Recommended)

Skills auto-load when needed:

```bash
# Test skill loading
hermes chat "Mod this APK to bypass premium check"
# Expected: apk-modding-workflow skill auto-loads

hermes chat "Test SQL injection on https://example.com"
# Expected: sqlmap skill auto-loads
```

Verify skills:
```bash
find ~/.omp/skills -name "SKILL.md" | wc -l
# Should show: 126
```

### For Standalone Server Users

Start OMP server:

```bash
cd omp
npm run dev
# or
bun run dev

# Access: http://localhost:3000
```

---

## Manual API Configuration

If you skipped API setup during installation:

### Option 1: Environment Variables (.env)

```bash
nano ~/.omp/.env
```

Add:
```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
DEFAULT_PROVIDER=openai
DEFAULT_MODEL=gpt-4
```

### Option 2: Config File (config.json)

```bash
nano ~/.omp/config.json
```

Add:
```json
{
  "providers": {
    "openai": {
      "apiKey": "sk-...",
      "baseURL": "https://api.openai.com/v1",
      "models": ["gpt-4", "gpt-3.5-turbo"]
    }
  },
  "defaultProvider": "openai",
  "defaultModel": "gpt-4",
  "systemPrompt": {
    "file": "~/.omp/prompts/system.md",
    "autoReload": true
  },
  "skills": {
    "directory": "~/.omp/skills",
    "autoLoad": true
  }
}
```

---

## Get API Keys

- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/
- **Google**: https://makersuite.google.com/app/apikey

---

## Verification

### Check Skills Deployment

```bash
ls ~/.omp/skills/security/
# Should show: apk-modding-workflow, sqlmap, frida-runtime-hooking, etc.

ls ~/.omp/skills/github/
# Should show: pr-workflow, code-review, issue-to-pr, etc.
```

### Check System Prompt

```bash
cat ~/.omp/prompts/system.md | head -20
# Should show: LTX-QUASAR v2.1 header
```

### Count Skills

```bash
find ~/.omp/skills -name "SKILL.md" | wc -l
# Expected: 126
```

---

## Troubleshooting

### Issue: "Please don't run as root"

**Solution**: Installer modified to allow root (Docker/Termux environments).

```bash
# If error persists, edit install.sh:
nano install.sh

# Comment out lines 27-30:
# if [ "$EUID" -eq 0 ]; then 
#    echo -e "${RED}❌ Please don't run as root${NC}"
#    exit 1
# fi
```

### Issue: Skills not deploying

```bash
# Check if skills directory exists
ls -la skills/

# Manual deployment
mkdir -p ~/.omp/skills
cp -r skills/* ~/.omp/skills/
```

### Issue: Permission denied

```bash
chmod -R 755 ~/.omp/
chmod +x install.sh
```

---

## Uninstall

```bash
rm -rf ~/.omp/
rm -rf omp-enhanced/
```

---

## Support

- **GitHub Issues**: https://github.com/harezadmm/omp-enhanced/issues
- **Documentation**: See OMP_SETUP_GUIDE.md
- **Hermes Integration**: See FINAL_HANDOFF.md

---

**Installation Complete!**

Ready to use 126 expert-level skills with Hermes Agent or standalone OMP server.
