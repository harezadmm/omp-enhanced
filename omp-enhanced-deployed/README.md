# OMP Enhanced - Universal Skills Library

Koleksi lengkap skills dari **RedMess** dan **Umi Bot** untuk Hermes Agent. Library komprehensif yang mencakup security, hacking, development, productivity, creative tools, dan banyak lagi.

## 📦 Apa Itu Skills?

Skills adalah modul pengetahuan prosedural yang bisa dipanggil oleh AI agent untuk menjalankan task spesifik dengan workflow yang sudah terbukti. Setiap skill berisi:

- **SKILL.md**: Dokumentasi lengkap dengan trigger conditions, workflow steps, pitfalls, dan verification
- **references/**: Dokumentasi tambahan, case studies, troubleshooting guides
- **templates/**: File template siap pakai
- **scripts/**: Helper scripts untuk automasi

## 📊 Statistik Library

- **912 files** total
- **126+ SKILL.md** files
- **605+ markdown** documents
- **50+ categories** berbeda

## 🎯 Kategori Skills

### 🔐 Security (42 skills)
Offensive security, penetration testing, exploit development, malware analysis

**Highlights:**
- `android-16-apk-modding` - Mod APK untuk Android 16/ColorOS
- `apk-modding-workflow` - Workflow lengkap decompile, modify, sign APK
- `frida-runtime-hooking` - Bypass app checks dengan dynamic hooking
- `godmode` - Jailbreak LLMs dengan Parseltongue & GODMODE
- `sqlmap` - SQL injection automation
- `blackhat-hacking` - Hacking tools comprehensive
- `web-pentesting-tools` - Browser-based pentesting dengan CloudFlare evasion
- `lua-deobfuscation` - Deobfuscate commercial Lua obfuscators
- **Red Team Arsenal** (100+ tools): Metasploit, Empire, Mimikatz, Bloodhound, dll

### 💻 Software Development (14 skills)
GitHub workflows, debugging, testing, code quality

**Highlights:**
- `github/` - Full GitHub workflow: PR, issues, code review, CI/CD
- `systematic-debugging` - 4-phase root cause debugging
- `test-driven-development` - Enforce RED-GREEN-REFACTOR
- `python-debugpy` - Python debugging dengan DAP
- `node-inspect-debugger` - Node.js debugging via Chrome DevTools

### 🎨 Creative (12 skills)
Design, ASCII art, diagrams, music generation

**Highlights:**
- `excalidraw` - Hand-drawn architecture diagrams
- `ascii-art` - Generate ASCII art dengan pyfiglet, cowsay
- `popular-web-designs` - 54 design systems (Stripe, Linear, Vercel)
- `songwriting-and-ai-music` - Suno AI music prompts

### 📊 Productivity (15 skills)
Documents, spreadsheets, meetings, automation

**Highlights:**
- `docx` - Create/edit Word documents
- `xlsx` - Excel workbook manipulation
- `pdf` - PDF creation, merging, forms
- `notion` - Notion API integration
- `google-workspace` - Gmail, Calendar, Drive, Docs, Sheets

### 🔬 Research (4 skills)
Academic papers, citations, competitor monitoring

**Highlights:**
- `arxiv` - Search academic papers
- `grounded-citations` - Ground answers dengan cited sources
- `competitor-news-monitor` - Monitor company news

### 📧 Email (2 skills)
Email workflows via terminal

**Highlights:**
- `himalaya` - IMAP/SMTP CLI client
- `email-inbox-triage` - Automated inbox triage

### 🎥 Media (3 skills)
YouTube, GIF, audio visualization

**Highlights:**
- `youtube-content` - Transcripts to summaries/blogs
- `gif-search` - Search/download GIFs from Tenor

### 🤖 Autonomous AI Agents (7 skills)
Multi-agent orchestration, delegation

**Highlights:**
- `claude-code` - Delegate to Claude Code CLI
- `hermes-agent` - Configure & orchestrate Hermes

## 🚀 Instalasi

### Windows (Automated Installer)

Download dan jalankan installer otomatis:

```bash
# 1. Download installer
git clone https://github.com/harezadmm/omp-enhanced.git
cd omp-enhanced/windows-installer

# 2. Run installer (Admin privileges recommended)
install.bat

# Installer akan otomatis:
# - Download Java JDK 21 (jika belum ada)
# - Setup Android SDK & tools
# - Install Hermes Agent
# - Configure environment variables
```

**Manual Installation:** Lihat `windows-installer/INSTALL-GUIDE.txt` untuk panduan lengkap.

### Linux/Mac

```bash
# Clone repo
git clone https://github.com/harezadmm/omp-enhanced.git
cd omp-enhanced

# Run install script
chmod +x install.sh
./install.sh
```

## 🎯 Cara Pakai

### 1. Load Skill dari Hermes Agent

```bash
# List semua skills
hermes skills list

# Load specific skill
hermes skills view apk-modding-workflow

# Install optional skill
hermes skills install sqlmap
```

### 2. Panggil dari Conversation

Tinggal mention task yang relevan, AI akan auto-load skill yang sesuai:

```
"Mod APK ini, bypass premium checks"
→ Auto-loads: apk-modding-workflow, frida-runtime-hooking

"Buat GitHub PR untuk fitur ini"
→ Auto-loads: github/pr-workflow

"Deobfuscate Lua script ini"
→ Auto-loads: lua-deobfuscation
```

### 3. Manual Load (jika perlu)

```python
# Dalam Hermes conversation
skill_view(name='apk-modding-workflow')
```

## 📁 Struktur Directory

```
skills/
├── Security/              # 42 offensive security skills
│   ├── apk-modding-workflow/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   └── templates/
│   ├── frida-runtime-hooking/
│   ├── sqlmap/
│   └── red-team-arsenal/  # 100+ tools
├── software-development/  # GitHub, debugging, testing
├── creative/              # Design, ASCII, diagrams
├── productivity/          # Docs, spreadsheets, meetings
├── research/              # Papers, citations, monitoring
├── email/                 # IMAP/SMTP workflows
├── media/                 # YouTube, GIF, audio
└── autonomous-ai-agents/  # Multi-agent orchestration
```

## 🎯 Use Cases

### APK Modding
```bash
# Decompile → Modify → Sign → Install
apktool d app.apk
# Edit smali/resources
apktool b app -o modded.apk
uber-apk-signer -a modded.apk
```
Skill: `apk-modding-workflow`, `frida-runtime-hooking`

### SQL Injection Attack
```bash
sqlmap -u "http://target.com/page?id=1" --dbs --batch
sqlmap -u "http://target.com/page?id=1" -D dbname --tables
sqlmap -u "http://target.com/page?id=1" -D dbname -T users --dump
```
Skill: `sqlmap`, `web-pentesting-tools`

### GitHub PR Workflow
```bash
git checkout -b feature-branch
git add .
git commit -m "feat: add new feature"
git push -u origin feature-branch
gh pr create --title "Add feature" --body "Description"
```
Skill: `github/pr-workflow`

### Jailbreak LLM
```python
# Load GODMODE prefills
from godmode import load_parseltongue
load_parseltongue("brutal_prefill_opus.json")
```
Skill: `godmode`, `super-mod-brutal-prefills`

## 🔥 Skills Paling Power

### Top Security Skills
1. **apk-modding-workflow** - Complete APK reverse engineering
2. **frida-runtime-hooking** - Bypass any app check
3. **sqlmap** - Automated SQL injection
4. **godmode** - LLM jailbreaking
5. **red-team-arsenal** - 100+ pentesting tools

### Top Development Skills
1. **github/** - Full GitHub automation
2. **systematic-debugging** - Root cause analysis
3. **test-driven-development** - TDD enforcement

### Top Productivity Skills
1. **docx** - Word document automation
2. **xlsx** - Excel manipulation
3. **notion** - Notion integration

## 📖 Dokumentasi Lengkap

Setiap skill punya dokumentasi lengkap di `SKILL.md`:

```markdown
---
description: Use when [trigger condition]
triggers: [list of triggers]
---

# Skill Name

## When to Use
[Clear trigger conditions]

## Workflow
1. Step 1
2. Step 2
3. Verification

## Pitfalls
- Common mistake 1
- Common mistake 2

## Tools Required
- Tool 1
- Tool 2
```

## 🛠️ Requirements

- **Hermes Agent** (Nous Research)
- **Python 3.12+** (3.14 compatibility issues untuk beberapa library)
- **Git** untuk version control
- **Platform-specific tools** tergantung skill yang dipakai

## 🔄 Update Skills

```bash
# Pull latest changes
cd omp-enhanced
git pull origin main

# Sync ke Hermes
cp -r skills/* ~/.hermes/profiles/your-profile/skills/
```

## 📝 Contributing

Tambah skill baru:

1. Buat directory `skills/category/skill-name/`
2. Tambah `SKILL.md` dengan format standar
3. (Optional) Tambah `references/`, `templates/`, `scripts/`
4. Commit & push

## ⚠️ Disclaimer

Skills ini untuk **educational & authorized testing only**. Security skills (APK modding, SQL injection, pentesting) hanya boleh digunakan pada sistem yang kamu punya atau dengan izin eksplisit.

Penggunaan ilegal adalah tanggung jawab user.

## 📜 License

Mixed licenses - lihat individual skill directories untuk license spesifik.

## 🤝 Credits

- **RedMess** - Original skills library
- **Umi Bot** - Security-focused skills collection
- **Nous Research** - Hermes Agent framework
- **Contributors** - Community contributors

## 📧 Support

Issues/questions? Open GitHub issue atau contact maintainer.

---

**Last Updated:** 2026-09-06  
**Version:** 2.0.0  
**Total Skills:** 126+  
**Total Files:** 912
