# 🚀 Quick Deploy to OMP.sh

**Time Required**: 5 minutes  
**Deployed Location**: `/root/omp-enhanced-deployed/`

---

## ✅ Step 1: Load AGENTS.md as System Prompt (2 minutes)

### Copy Content
```bash
cat ~/omp-enhanced-deployed/AGENTS.md
```

### Paste to OMP
1. Open OMP.sh dashboard/config
2. Find "System Prompt" or "Agent Configuration"
3. Paste entire AGENTS.md content (449 lines)
4. Save configuration

**AGENTS.md contains:**
- LTX-QUASAR COLD PROTOCOL
- Auto-skill loading for 126 skills
- Evidence-first verification
- Skill chaining support

---

## ✅ Step 2: Configure Skills Path (1 minute)

### Option A: Environment Variable
```bash
export OMP_SKILLS_PATH=~/omp-enhanced-deployed/skills/
```

### Option B: Config File
Edit OMP config file:
```yaml
skills:
  directory: ~/omp-enhanced-deployed/skills/
  auto_load: true
```

### Option C: Direct Path in OMP Dashboard
Set skills directory to: `/root/omp-enhanced-deployed/skills/`

---

## ✅ Step 3: Test Integration (2 minutes)

### Test 1: APK Modding
```
Request: "Mod this APK to bypass premium check"

Expected:
✅ apk-modding-workflow skill auto-loads
✅ Executes: Decompile → Patch → Sign → Verify
✅ Reports with evidence
```

### Test 2: SQL Injection
```
Request: "Test this endpoint for SQL injection"

Expected:
✅ sqlmap skill auto-loads
✅ Executes: Probe → Enumerate → Dump
✅ Reports database tables
```

### Test 3: GitHub Automation
```
Request: "Create a PR for this feature"

Expected:
✅ github/pr-workflow skill auto-loads
✅ Executes: Branch → Commit → Push → PR
✅ Reports PR URL + CI status
```

---

## 📦 What's Available

### 126 Skills Across 10+ Categories

**Security (42 skills)**
- apk-modding-workflow
- frida-runtime-hooking
- sqlmap
- blackhat-hacking
- web-pentesting-tools
- godmode (LLM jailbreaking)
- + 36 more

**Development (14 skills)**
- github/pr-workflow
- systematic-debugging
- test-driven-development
- python-debugpy
- + 10 more

**Creative (12 skills)**
- excalidraw
- ascii-art
- popular-web-designs
- + 9 more

**Productivity (15 skills)**
- docx, xlsx, powerpoint
- google-workspace
- notion
- + 10 more

**And More:**
- MLOps (4 skills)
- Research (4 skills)
- Autonomous Agents (5 skills)
- Email (2 skills)
- Media (3 skills)
- Smart Home (1 skill)
- Social Media (1 skill)

---

## 🔑 Key Features

### 🚀 Auto-Skill Loading
Keywords trigger skills automatically:
- "APK" / "mod" → apk-modding-workflow
- "SQLi" / "SQL injection" → sqlmap
- "PR" / "pull request" → github/pr-workflow
- "Excel" / "Word" → xlsx / docx

### 🔍 Evidence-First
Every skill defines proof standards:
- APK: Install success + logcat
- SQLi: Database dump + row counts
- PR: URL + CI passes

### 🔗 Skill Chaining
Complex operations use multiple skills:
- Security audit: recon → exploit → document → PR
- APK pipeline: mod → sign → distribute → document

### ♻️ Fallback Protocol
If skill unavailable:
1. Try skill-based approach
2. Fall back to stdlib + Cold Protocol
3. Log gap for improvement

---

## 📚 Documentation

All available in `/root/omp-enhanced-deployed/`:

- **README.md** - Project overview
- **AGENTS.md** - System prompt (USE THIS!)
- **INTEGRATION_GUIDE.md** - Complete integration (529 lines)
- **SKILLS_INDEX.md** - All 126 skills
- **HANDOFF.md** - Deployment guide
- **QUICK_START.md** - 5-minute guide

---

## 🐛 Troubleshooting

### Skills Not Loading
```bash
# Verify skills directory
ls ~/omp-enhanced-deployed/skills/

# Check AGENTS.md loaded
# Should see LTX-QUASAR banner in OMP
```

### Auto-Loading Not Working
1. Verify AGENTS.md loaded as system prompt
2. Check OMP skills path configured
3. Test keyword: "Mod this APK"

### Skill Execution Fails
```bash
# Check skill file exists
ls ~/omp-enhanced-deployed/skills/security/apk-modding-workflow/SKILL.md

# Read skill documentation
cat ~/omp-enhanced-deployed/skills/security/apk-modding-workflow/SKILL.md
```

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] AGENTS.md loaded in OMP system prompt
- [ ] Skills path configured: `~/omp-enhanced-deployed/skills/`
- [ ] Test: "Mod this APK" → skill auto-loads
- [ ] Test: "Test for SQLi" → sqlmap loads
- [ ] Test: "Create PR" → github workflow loads
- [ ] 126 skills accessible
- [ ] Documentation readable

---

## 🎯 Success Criteria

When deployment successful:

✅ Request "Mod this APK" → apk-modding-workflow auto-loads  
✅ Skills execute with evidence output  
✅ No manual skill selection needed  
✅ Skill chaining works for complex ops  

---

**Status**: ✅ READY FOR OMP.SH  
**Location**: `/root/omp-enhanced-deployed/`  
**Skills**: 126  
**Quality**: ⭐⭐⭐⭐⭐

**Deploy sekarang. Use immediately.**
