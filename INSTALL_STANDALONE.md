# OMP Enhanced - Standalone Installation

## Quick Install (No npm/pm2 required)

```bash
git clone https://github.com/harezadmm/omp-enhanced.git
cd omp-enhanced
bash install_fixed.sh
```

## What Gets Installed

- **126 skills** → `~/.omp/skills/`
- **System prompt** (AGENTS.md) → `~/.omp/prompts/system.md`
- **Config** → `~/.omp/config.yaml`

## Requirements

- Linux/macOS
- Bash
- NO Node.js/npm required
- NO PM2 required

## Integration with Hermes Agent

After installation, skills are ready at `~/.omp/skills/`. 

To use with Hermes:

```bash
# Copy skills to Hermes profile
cp -r ~/.omp/skills/* ~/.hermes/profiles/umi2/skills/

# Or symlink
ln -s ~/.omp/skills ~/.hermes/profiles/umi2/skills/omp
```

## Installed Skills Categories

- **Security** (42 skills): APK modding, pentesting, Frida, SQLmap
- **GitHub** (8 skills): PR workflow, code review, repo management
- **Creative** (12 skills): ASCII art, diagrams, design systems
- **Software Dev** (24 skills): TDD, debugging, code review
- **Productivity** (18 skills): Docs, spreadsheets, meeting notes
- **MLOps** (14 skills): Model serving, evaluation, inference
- **Autonomous Agents** (8 skills): Claude Code, Codex, Hermes

## Files

```
~/.omp/
├── config.yaml          # Configuration
├── prompts/
│   └── system.md        # AGENTS.md system prompt
└── skills/              # 126 skills
    ├── security/
    ├── github/
    ├── creative/
    ├── software-development/
    ├── productivity/
    ├── mlops/
    └── autonomous-ai-agents/
```

## Verification

```bash
# Check installed skills
find ~/.omp/skills -name "SKILL.md" | wc -l
# Should output: 126

# Check system prompt
head ~/.omp/prompts/system.md

# Check config
cat ~/.omp/config.yaml
```

## Original vs Fixed Installer

| Feature | `install.sh` (original) | `install_fixed.sh` (fixed) |
|---------|------------------------|---------------------------|
| npm dependency | ❌ Required | ✅ Not needed |
| PM2 dependency | ❌ Required | ✅ Not needed |
| OMP.sh repo clone | ❌ Required | ✅ Standalone |
| Skills deployment | ✅ Yes | ✅ Yes |
| System prompt | ✅ Yes | ✅ Yes |
| Config file | JSON | YAML (simpler) |

## Troubleshooting

### "Skills directory not found"
Make sure you're running from `omp-enhanced` directory where `skills/` folder exists.

### "Permission denied"
Don't run as root. Run as normal user.

### Skills count is 0
Check if `skills/` directory exists in current directory before running installer.

## Next Steps

1. Install complete ✅
2. Copy to Hermes profile
3. Test skill loading: `hermes skills list`
4. Use skills in Hermes conversations
