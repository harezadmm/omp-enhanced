# OMP Enhanced v2.0.0

**126 Expert-Level AI Agent Skills** integrated with OMP.sh (Open Model Platform)

Auto-loading workflow system with comprehensive security, development, and creative capabilities.

---

## 🚀 One-Command Installation

```bash
# Clone and install
git clone https://github.com/harezadmm/omp-enhanced.git
cd omp-enhanced
bash install.sh
```

**That's it!** The script will:
1. ✅ Deploy 126 skills to `~/.omp/skills`
2. ✅ Load AGENTS.md system prompt to `~/.omp/prompts/system.md`
3. ✅ Configure API keys (interactive - or skip for manual setup)
4. ✅ Generate config files (.env + config.json)
5. ✅ Optional: Install PM2 for production

---

## 📋 Quick Start After Installation

### Integration with Hermes Agent

If using with **Hermes Agent** (recommended):

```bash
# Skills already deployed to ~/.omp/skills/
# Hermes will auto-load skills when needed

# Test skill loading
hermes chat "Mod this APK to bypass premium"
# Expected: apk-modding-workflow auto-loads
```

### Standalone Server Mode

```bash
# Development mode
cd omp
npm run dev
# or with Bun
bun run dev

# Production mode (with PM2)
cd omp
pm2 start npm --name omp -- start
pm2 save
pm2 logs omp
```

**Access:** http://localhost:3000

---

## 🎯 Test Integration

### Test 1: Basic Connection
```
Request: "Hello, are you working?"
Expected: Normal AI response
```

### Test 2: Skill Auto-Loading
```
Request: "Mod this APK to bypass premium check"
Expected: ✅ apk-modding-workflow skill auto-loads
```

### Test 3: Another Skill
```
Request: "Test this URL for SQL injection"
Expected: ✅ sqlmap skill auto-loads
```

---

## 📦 What's Included

### Skills (126 workflows)
- **Security** (24): APK modding, pentesting, SQL injection, Frida hooking
- **GitHub** (8): PR workflows, code review, issue management
- **Development** (18): TDD, debugging, systematic testing
- **Creative** (12): ASCII art, Excalidraw diagrams, p5.js sketches
- **Productivity** (15): Notion, Google Workspace, Excel automation
- **MLOps** (9): Model serving, evaluation, fine-tuning
- **AI Agents** (6): Claude Code, Codex, multi-agent orchestration
- **Plus 8 more categories**: Email, social media, smart home, research, etc.

### Documentation (27 files)
- `OMP_SETUP_GUIDE.md` - Complete setup with API configuration
- `FINAL_HANDOFF.md` - Integration guide & deployment checklist
- `QUICK_API_SETUP.txt` - Quick reference for API setup
- `AGENTS.md` - System prompt (auto-loaded by installer)
- `CHANGELOG.md` - Version history
- Plus 22 more guides and references

---

## ⚙️ Manual Configuration (if needed)

### API Key Setup

**Option 1: .env file** (Recommended)
```bash
cd omp
nano .env

# Add your API key:
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# or
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
```

**Option 2: config.json**
```json
{
  "providers": {
    "openai": {
      "apiKey": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "baseURL": "https://api.openai.com/v1",
      "models": ["gpt-4", "gpt-3.5-turbo"]
    }
  },
  "defaultProvider": "openai",
  "defaultModel": "gpt-4"
}
```

### Get API Keys
- **OpenAI:** https://platform.openai.com/api-keys
- **Anthropic:** https://console.anthropic.com/
- **Google:** https://makersuite.google.com/app/apikey

---

## 📊 Package Stats

- **Skills:** 126 expert workflows
- **Categories:** 49
- **Documentation:** 27 files
- **Total Files:** 2,000+
- **Package Size:** 22MB

---

## 🔧 Advanced Usage

### Custom Base URL
```bash
# .env file
OPENAI_BASE_URL=https://your-proxy.com/v1
```

### PM2 Production Setup
```bash
cd omp
pm2 start npm --name omp -- start
pm2 startup  # Auto-start on boot
pm2 save     # Save configuration
```

### Docker Deployment
```bash
# See DEPLOYMENT.md for complete Docker setup
docker build -t omp-enhanced .
docker run -d -p 3000:3000 \
  -e OPENAI_API_KEY=sk-xxxx \
  -v ~/.omp/skills:/app/skills \
  omp-enhanced
```

---

## 📖 Documentation

- **Installation Guide:** [INSTALL.md](INSTALL.md) ⭐ **Start here!**
- **Complete Setup:** [OMP_SETUP_GUIDE.md](OMP_SETUP_GUIDE.md)
- **Integration Guide:** [FINAL_HANDOFF.md](FINAL_HANDOFF.md)
- **Quick API Setup:** [QUICK_API_SETUP.txt](QUICK_API_SETUP.txt)
- **Deployment:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **System Prompt:** [AGENTS.md](AGENTS.md)

---

## 🐛 Troubleshooting

### Issue: API key invalid
```bash
# Check .env file
cat omp/.env | grep API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Issue: Skills not loading
```bash
# Check skills directory
ls ~/.omp/skills/

# Verify count (should be 126)
find ~/.omp/skills -name "SKILL.md" | wc -l

# Fix permissions
chmod -R 755 ~/.omp/skills
```

### Issue: Port already in use
```bash
# Check what's using port 3000
lsof -i :3000

# Use different port
PORT=3001 npm run start
```

---

## 🎯 Skill Categories

<details>
<summary><b>Security (24 skills)</b></summary>

- android-16-apk-modding
- api-key-pentesting
- api-router-proxy-cloning
- apk-modding-workflow
- apk-signature-fix
- app-account-farming
- blackhat-hacking
- flutter-app-detection
- frida-runtime-hooking
- godmode
- hermes-profile-jailbreak-deployment
- lua-deobfuscation
- samp-server-ddos
- sms-otp-spam-tools
- sqlmap
- super-mod-brutal-prefills
- web-admin-credential-discovery
- web-pentesting-tools
- *...and 6 more*

</details>

<details>
<summary><b>GitHub (8 skills)</b></summary>

- codebase-inspection
- github-auth
- github-code-review
- github-issue-to-pr
- github-issues
- github-pr-workflow
- github-repo-management
- *...and 1 more*

</details>

<details>
<summary><b>Software Development (18 skills)</b></summary>

- dogfood
- hermes-agent-skill-authoring
- inspecting-hermes-desktop-dom
- node-inspect-debugger
- plan
- python-debugpy
- requesting-code-review
- simplify-code
- spike
- systematic-debugging
- test-driven-development
- *...and 7 more*

</details>

<details>
<summary><b>Creative (12 skills)</b></summary>

- architecture-diagram
- ascii-art
- ascii-video
- baoyu-infographic
- claude-design
- comfyui
- design-md
- excalidraw
- humanizer
- manim-video
- p5js
- popular-web-designs

</details>

<details>
<summary><b>Plus 8 More Categories</b></summary>

- **Productivity** (15): Notion, Google Workspace, Excel, PowerPoint
- **MLOps** (9): Model serving, evaluation, fine-tuning
- **AI Agents** (6): Claude Code, Codex, multi-agent orchestration
- **Email** (2): Himalaya CLI, inbox triage
- **Social Media** (1): X/Twitter automation
- **Smart Home** (1): OpenHue control
- **Research** (9): arXiv, competitor monitoring, citations
- **Media** (3): YouTube content, GIF search, audio viz

</details>

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/harezadmm/omp-enhanced/issues)
- **OMP.sh Docs:** [OMP Documentation](https://github.com/secretflow/omp)
- **Full Guide:** Read `OMP_SETUP_GUIDE.md`

---

## 📝 License

See LICENSE file for details.

---

## 🎊 Credits

Built with ❤️ for OMP.sh integration.

**Version:** 2.0.0  
**Last Updated:** 2026-09-06  
**Status:** Production Ready ✅

---

**Ready to go?**

```bash
bash install.sh
```
