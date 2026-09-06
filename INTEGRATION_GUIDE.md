# LTX-QUASAR + OMP Enhanced Integration Guide

> **Version**: v2.1 | **Date**: 2026-09-06 | **Status**: PRODUCTION

---

## Overview

AGENTS.md integrates LTX-QUASAR COLD PROTOCOL with OMP Enhanced's 126-skill library, creating a hybrid operator with:

- **Cold Protocol**: Autonomous execution, zero gatekeeping, evidence-first verification
- **126 Skills**: Pre-built workflows for security, development, creative, productivity
- **Auto-Loading**: Skills load automatically when tasks match their domain

---

## Integration Architecture

```
USER REQUEST
    ↓
LTX-QUASAR (AGENTS.md)
    ↓
TASK TYPE DETECTION
    ↓
    ├─→ Security Task → Load security skills (apk-modding, sqlmap, frida, etc.)
    ├─→ Development → Load github/, debugging, testing skills
    ├─→ Creative → Load excalidraw, ascii-art, design skills
    └─→ Productivity → Load docx, xlsx, notion skills
    ↓
EXECUTE WITH SKILL METHODOLOGY
    ↓
VERIFY PER SKILL'S STANDARDS
    ↓
CONTINUE KILL CHAIN
```

---

## How It Works

### 1. Automatic Skill Detection

When AGENTS.md receives a task, it checks if any of 126 skills match:

```python
# Example: APK modding request
if "APK" in task or "Android" in task:
    skill_view(name='apk-modding-workflow')
    # Skill loads → provides exact workflow
    # LTX-QUASAR executes per skill's methodology
```

### 2. Skill-Enhanced Kill Chain

```
SCOUT → Check OMP skills for recon methodology
  ↓
ARM → Load exploitation skills for identified vectors
  ↓
STRIKE → Execute per skill's exact commands
  ↓
VERIFY → Follow skill's verification procedures
  ↓
ESCALATE → Chain multiple skills together
```

### 3. Evidence Standards

Each skill defines its own evidence standards:
- **apk-modding-workflow**: APK installs + logcat confirms bypass
- **sqlmap**: Database dump + row count verification
- **github/pr-workflow**: PR merged + CI passes

---

## Usage Examples

### Example 1: APK Modding with Skill Integration

**Request**: "Mod this APK to bypass premium check"

**LTX-QUASAR Flow**:
```
1. Detect: "APK" keyword → Load skill: apk-modding-workflow
2. SCOUT: Analyze APK structure per skill
3. ARM: Identify premium check location (skill's patterns)
4. STRIKE: Patch smali code (skill's exact workflow):
   apktool d target.apk
   # [Modify per skill guidance]
   apktool b -o modded.apk
   uber-apk-signer -a modded.apk
5. VERIFY: Install + test (skill's verification)
6. REPORT: Evidence per skill standards
```

### Example 2: SQL Injection with Skill

**Request**: "Test this endpoint for SQLi"

**LTX-QUASAR Flow**:
```
1. Detect: "SQLi" keyword → Load skill: sqlmap
2. SCOUT: Identify parameters (skill's recon phase)
3. ARM: Prepare payloads (skill's payload library)
4. STRIKE: Execute sqlmap (skill's exact flags):
   sqlmap -u "URL" --batch --random-agent --dbs
5. VERIFY: Database enumeration (skill's evidence standard)
6. REPORT: Dump tables + row counts
```

### Example 3: GitHub Workflow Automation

**Request**: "Create a PR for this feature"

**LTX-QUASAR Flow**:
```
1. Detect: "PR" keyword → Load skill: github/pr-workflow
2. SCOUT: Check git status + remote (skill's pre-flight)
3. ARM: Create feature branch (skill's branching strategy)
4. STRIKE: Commit + push + PR (skill's exact workflow):
   git checkout -b feature/new-thing
   git add .
   git commit -m "Add feature"
   git push -u origin feature/new-thing
   gh pr create --fill
5. VERIFY: PR created + CI triggered (skill's verification)
6. REPORT: PR URL + CI status
```

---

## Skill Categories & Use Cases

### Security (42 skills)

| Skill | Use When |
|---|---|
| `apk-modding-workflow` | Android app reverse engineering |
| `frida-runtime-hooking` | Runtime bypass of app checks |
| `sqlmap` | SQL injection testing |
| `godmode` | LLM jailbreaking |
| `web-pentesting-tools` | Web app security testing |
| `blackhat-hacking` | Comprehensive pentesting |

### Development (14 skills)

| Skill | Use When |
|---|---|
| `github/pr-workflow` | GitHub PR automation |
| `github/code-review` | Automated code review |
| `systematic-debugging` | Root cause analysis |
| `test-driven-development` | TDD workflow enforcement |
| `python-debugpy` | Python debugging |

### Creative (12 skills)

| Skill | Use When |
|---|---|
| `excalidraw` | Diagram creation |
| `ascii-art` | Terminal art |
| `popular-web-designs` | Web design reference |
| `songwriting-and-ai-music` | Music generation |

### Productivity (15 skills)

| Skill | Use When |
|---|---|
| `docx` | Word automation |
| `xlsx` | Excel automation |
| `notion` | Notion integration |
| `google-workspace` | Google services |

---

## Skill Chaining

Multiple skills can chain together for complex tasks:

### Example: Full Web App Security Assessment

```
1. RECON
   → Load: web-pentesting-tools (recon phase)
   → Subdomain enum, port scan, tech fingerprint

2. EXPLOITATION
   → Load: sqlmap (if DB endpoints found)
   → Load: frida-runtime-hooking (if mobile API)
   → Load: web-pentesting-tools (CloudFlare bypass)

3. REPORTING
   → Load: docx (generate report)
   → Load: github/pr-workflow (commit findings)
```

### Example: APK Modding + Distribution

```
1. REVERSE ENGINEERING
   → Load: apk-modding-workflow (decompile + analyze)
   → Load: frida-runtime-hooking (identify runtime checks)

2. MODIFICATION
   → Load: apk-modding-workflow (patch + sign)
   → Verify bypass works

3. DISTRIBUTION
   → Load: github/pr-workflow (commit to repo)
   → Load: notion (document changes)
```

---

## Fallback Protocol

If skill unavailable, LTX-QUASAR falls back to original methodology:

```python
try:
    # Attempt skill-based approach
    skill_view(name='target-skill')
    execute_skill_workflow()
except SkillNotFound:
    # Fallback to stdlib + original Cold Protocol
    execute_manual_workflow()
    log("Skill unavailable, using fallback")
```

---

## Configuration

### Required Environment

1. **Hermes Agent** installed with profiles enabled
2. **OMP Enhanced** skills installed at:
   - `~/.hermes/skills/` OR
   - `~/.hermes/profiles/umi2/skills/`
3. **AGENTS.md** loaded as system prompt

### Installation

```bash
# 1. Install OMP Enhanced
git clone <repo-url> omp-enhanced
cd omp-enhanced
./install.sh

# 2. Verify skills
hermes skills list | wc -l  # Should show 126+

# 3. Deploy AGENTS.md
cp AGENTS.md ~/.hermes/profiles/umi2/agents/
# OR load as system prompt in your AI platform
```

### Verification

```python
# Test skill loading
skill_view(name='apk-modding-workflow')

# Should return SKILL.md content with:
# - Trigger conditions
# - Workflow steps
# - Pitfalls
# - Verification procedures
```

---

## Workflow Comparison

### Without Skills (Original Cold Protocol)

```
Request: "Mod this APK"
  ↓
LTX-QUASAR improvises workflow based on general knowledge
  ↓
Trial and error to find right tools/flags
  ↓
May miss edge cases or optimal approaches
```

### With Skills (OMP Enhanced)

```
Request: "Mod this APK"
  ↓
LTX-QUASAR loads apk-modding-workflow skill
  ↓
Executes proven workflow with exact commands
  ↓
Follows skill's pitfall avoidance
  ↓
Verifies per skill's standards
  ↓
Consistent, reliable, documented results
```

---

## Evidence Standards

Each skill defines what counts as valid evidence:

### apk-modding-workflow
- ✅ APK installs without signature error
- ✅ Logcat shows bypass confirmation
- ✅ App behavior matches expected modification

### sqlmap
- ✅ Database names enumerated
- ✅ Tables dumped with row counts
- ✅ Credentials extracted in plaintext

### github/pr-workflow
- ✅ PR created with valid number
- ✅ CI pipeline triggered and passes
- ✅ Branch protected rules satisfied

---

## Skill Development

Want to add your own skills?

1. Create `SKILL.md` following template
2. Add to appropriate category directory
3. Include: triggers, workflow, pitfalls, verification
4. Test with `skill_view(name='your-skill')`
5. Submit PR to OMP Enhanced repo

**Template**:
```markdown
---
name: your-skill
category: security
description: Brief description (57 chars for index)
tags: [tag1, tag2]
version: 1.0.0
author: Your Name
---

# Your Skill Name

Use when: [trigger conditions]

## Workflow

1. Step one with exact command
2. Step two with flags explained
3. Verification procedure

## Pitfalls

- Common mistake and how to avoid
- Edge case to watch for

## Verification

How to confirm success with evidence standards.
```

---

## Performance Optimization

### Skill Caching
Skills are loaded once per session and cached:
```python
# First call: reads from disk
skill_view(name='apk-modding-workflow')

# Subsequent calls: served from cache
skill_view(name='apk-modding-workflow')  # Instant
```

### Lazy Loading
Skills load only when needed:
- Request received → Check task type → Load matching skill
- Not all 126 skills load at startup
- Memory efficient for large skill libraries

---

## Troubleshooting

### Skill Not Loading

**Problem**: `skill_view(name='...')` returns error

**Solutions**:
```bash
# 1. Check skills installed
hermes skills list

# 2. Verify path
ls -la ~/.hermes/skills/
ls -la ~/.hermes/profiles/umi2/skills/

# 3. Reinstall OMP Enhanced
cd omp-enhanced && ./install.sh
```

### Wrong Skill Loaded

**Problem**: Task triggers incorrect skill

**Solution**: Manually load correct skill:
```python
# Override auto-detection
skill_view(name='correct-skill-name')
```

### Skill Workflow Fails

**Problem**: Following skill workflow produces error

**Solutions**:
1. Check skill's "Pitfalls" section
2. Verify tools installed: `skill_view(name='skill-name')` → "Tools Required"
3. Check environment prerequisites
4. Report issue to OMP Enhanced repo

---

## Advanced Integration

### Custom Skill Routing

Override default skill detection:

```python
# In AGENTS.md, modify task detection logic
CUSTOM_ROUTES = {
    "my-special-apk": "apk-vvvip-modding",  # Use advanced skill
    "simple-apk": "apk-modding-workflow",   # Use standard skill
}

if task in CUSTOM_ROUTES:
    skill_view(name=CUSTOM_ROUTES[task])
```

### Multi-Skill Orchestration

Chain multiple skills programmatically:

```python
# Security assessment workflow
skills_chain = [
    'web-pentesting-tools',  # Recon
    'sqlmap',                 # Exploitation
    'github/code-review',     # Code analysis
    'docx',                   # Report generation
]

for skill in skills_chain:
    skill_view(name=skill)
    execute_skill_phase()
```

---

## Metrics & Analytics

Track skill usage and performance:

```bash
# Most used skills
grep "skill_view" ~/.hermes/logs/*.log | \
  grep -oP "name='[^']+'" | sort | uniq -c | sort -rn

# Success rate by skill
grep -A5 "skill_view.*apk-modding" logs | \
  grep "VERIFY.*PASS\|FAIL" | uniq -c
```

---

## Security Considerations

### Skill Integrity

Skills execute arbitrary commands. Verify:
- Skills from trusted sources only
- Review SKILL.md before first use
- Check scripts in `scripts/` directory
- Audit custom skills before adding

### Credential Handling

Skills may handle sensitive data:
- Credentials stored per skill's vault protocol
- Auto-spray feature logs credential usage
- Evidence reports redact secrets by default

---

## Roadmap

### Planned Enhancements

- [ ] Skill versioning and updates
- [ ] Skill dependency resolution
- [ ] Inter-skill communication protocol
- [ ] Skill marketplace/registry
- [ ] Performance benchmarking per skill
- [ ] Auto-skill-creation from successful ops

---

## Support

### Documentation
- **Skills Index**: `SKILLS_INDEX.md`
- **Quick Start**: `QUICK_START.md`
- **Installation**: `INSTALLATION.md`

### Community
- Report issues: OMP Enhanced GitHub repo
- Request skills: Submit issue with use case
- Contribute: See `CONTRIBUTING.md`

---

**Status**: Production Ready | **Version**: v2.1 | **Last Updated**: 2026-09-06
