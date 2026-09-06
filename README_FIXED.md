# OMP Enhanced - Standalone Fixed v2.0.1

## 🎯 INSTALASI CEPAT

```bash
# Download & extract
wget https://github.com/harezadmm/omp-enhanced/releases/download/v2.0.1/omp-enhanced-standalone-fixed-v2.0.1.tar.gz
tar -xzf omp-enhanced-standalone-fixed-v2.0.1.tar.gz
cd omp-enhanced-standalone-fixed-v2.0.1

# Install (jangan pakai sudo!)
bash install_fixed.sh
```

**Done!** 126 skills langsung ready di `~/.omp/skills/`

---

## ✅ YANG UDAH DIBENERIN

| Masalah Original | Status Fixed |
|-----------------|--------------|
| Butuh npm/Node.js | ✅ **Tidak perlu lagi** |
| Butuh PM2 | ✅ **Tidak perlu lagi** |
| Clone repo OMP.sh (404) | ✅ **Standalone sekarang** |
| Installer kompleks | ✅ **One command aja** |

---

## 📦 ISI PACKAGE

```
omp-enhanced-standalone-fixed-v2.0.1/
├── install_fixed.sh           # Installer bersih (no npm/pm2)
├── INSTALL_STANDALONE.md      # Dokumentasi lengkap
├── RELEASE_NOTES.txt          # Changelog
├── AGENTS.md                  # System prompt (LTX-QUASAR v2.1)
└── skills/                    # 126 skills
    ├── security/              (42 skills)
    ├── github/                (8 skills)
    ├── creative/              (12 skills)
    ├── software-development/  (24 skills)
    ├── productivity/          (18 skills)
    ├── mlops/                 (14 skills)
    └── autonomous-ai-agents/  (8 skills)
```

---

## 🔧 REQUIREMENTS

- ✅ **Bash** (sudah ada di Linux/macOS)
- ❌ **NO npm** required
- ❌ **NO pm2** required
- ❌ **NO Node.js** required

---

## 📊 HASIL INSTALASI

Setelah run `bash install_fixed.sh`:

```
~/.omp/
├── config.yaml               # Config YAML
├── prompts/
│   └── system.md            # AGENTS.md system prompt
└── skills/                  # 126 skills
    ├── security/
    ├── github/
    └── ... (10 categories)
```

---

## 🚀 INTEGRASI KE HERMES AGENT

```bash
# Copy skills ke Hermes profile
cp -r ~/.omp/skills/* ~/.hermes/profiles/umi2/skills/

# Test
hermes skills list | grep apk-modding
```

---

## 🧪 VERIFIKASI

```bash
# Cek jumlah skills
find ~/.omp/skills -name "SKILL.md" | wc -l
# Output: 126

# Cek system prompt
head -20 ~/.omp/prompts/system.md

# Cek config
cat ~/.omp/config.yaml
```

---

## 📋 SKILLS CATEGORIES (126 Total)

### 🛡️ Security (42 skills)
- `apk-modding-workflow` - Complete APK reverse engineering
- `frida-runtime-hooking` - Runtime app bypass
- `sqlmap` - SQL injection attacks
- `blackhat-hacking` - Hacking tools via Telegram
- `android-16-apk-modding` - Android 16 APK modding
- Dan 37 lagi...

### 🐙 GitHub (8 skills)
- `github-pr-workflow` - PR lifecycle management
- `github-code-review` - PR review with inline comments
- `github-issues` - Issue management
- Dan 5 lagi...

### 🎨 Creative (12 skills)
- `ascii-art` - ASCII art generation
- `architecture-diagram` - SVG architecture diagrams
- `excalidraw` - Hand-drawn diagrams
- Dan 9 lagi...

### 💻 Software Development (24 skills)
- `test-driven-development` - TDD workflow
- `systematic-debugging` - 4-phase debugging
- `requesting-code-review` - Pre-commit review
- Dan 21 lagi...

### 📊 Productivity (18 skills)
- `docx` - Word documents
- `xlsx` - Excel spreadsheets
- `pdf` - PDF manipulation
- Dan 15 lagi...

### 🤖 MLOps (14 skills)
- `llama-cpp` - Local GGUF inference
- `serving-llms-vllm` - vLLM serving
- `evaluating-llms-harness` - Benchmark LLMs
- Dan 11 lagi...

### 🎯 Autonomous AI Agents (8 skills)
- `claude-code` - Delegate to Claude Code CLI
- `codex` - Delegate to Codex CLI
- `hermes-agent` - Hermes configuration
- Dan 5 lagi...

---

## 🔐 CHECKSUMS

```
MD5:    07486474eebbf6f18cb4dec5114aa4bd
SHA256: 9f2ee4f43190e2e7e5f7ff4d2246c442a8ca59c2e3bb0e6d79601eb0b714000e
Size:   1.5MB (compressed)
```

---

## 🐛 TROUBLESHOOTING

### "Skills directory not found"
Run dari directory hasil extract tar.gz yang ada folder `skills/`

### "Permission denied"
**Jangan pakai sudo/root!** Run sebagai user biasa.

### Skills count = 0
Extract dulu tar.gz sebelum run installer.

---

## 📖 DOKUMENTASI LENGKAP

- **Quick Start**: Baca file ini
- **Full Guide**: `INSTALL_STANDALONE.md`
- **Changelog**: `RELEASE_NOTES.txt`
- **System Prompt**: `AGENTS.md`

---

## 📞 SUPPORT

- **Repo**: https://github.com/harezadmm/omp-enhanced
- **Issues**: Submit ke GitHub Issues
- **Telegram**: @sisuryaofficialkuu

---

**Version**: 2.0.1-fixed  
**Date**: 2026-09-06  
**Tested**: Linux Ubuntu 24.04, Debian 12  
**Status**: ✅ Production Ready
