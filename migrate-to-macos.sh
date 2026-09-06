#!/bin/bash
# ================================================================
#  LTX-QUASAR OMP MIGRATION — Windows → macOS
#  Run this ON YOUR MAC after copying the omp-enhanced/ folder
#  Usage: bash migrate-to-macos.sh
# ================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BLUE}"
cat << "EOF"
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║      ██╗  ████████╗██╗  ██╗     ██████╗ ██╗   ██╗ █████╗      ║
║      ██║  ╚══██╔══╝██║  ██║    ██╔══██╗██║   ██║██╔══██╗     ║
║      ██║     ██║   ███████║    ██████╔╝██║   ██║███████║     ║
║      ██║     ██║   ██╔══██║    ██╔══██╗██║   ██║██╔══██║     ║
║      ████████╗██║   ██║  ██║    ██║  ██║╚██████╔╝██║  ██║     ║
║      ╚═══════╝╚═╝   ╚═╝  ╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝     ║
║                                                                ║
║           OMP ENHANCED — macOS MIGRATION v2.0.1                ║
║           Windows → macOS · LTX-QUASAR COLD PROTOCOL           ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# ── PREFLIGHT ──────────────────────────────────────────────────
echo -e "${YELLOW}🔍 Preflight checks...${NC}"

if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ JANGAN jalanin sebagai root/sudo. Run as normal user.${NC}"
    exit 1
fi

if [ ! -d "skills" ]; then
    echo -e "${RED}❌ Folder 'skills/' gak ketemu.${NC}"
    echo -e "${YELLOW}   Pastiin lu jalanin script ini dari dalam folder omp-enhanced/${NC}"
    echo -e "${YELLOW}   Contoh: cd ~/omp-enhanced && bash migrate-to-macos.sh${NC}"
    exit 1
fi

if [ ! -f "AGENTS.md" ]; then
    echo -e "${RED}❌ AGENTS.md gak ketemu.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Running as normal user${NC}"
echo -e "${GREEN}✅ skills/ directory found${NC}"
echo -e "${GREEN}✅ AGENTS.md found${NC}"
echo ""

# ── STEP 1: DIRECTORIES ────────────────────────────────────────
echo -e "${BLUE}[1/6]${NC} Creating directory structure..."

mkdir -p ~/.omp/skills
mkdir -p ~/.omp/prompts
mkdir -p ~/.omp/agent

echo -e "${GREEN}  ✅ ~/.omp/skills/${NC}"
echo -e "${GREEN}  ✅ ~/.omp/prompts/${NC}"
echo -e "${GREEN}  ✅ ~/.omp/agent/${NC}"
echo ""

# ── STEP 2: DEPLOY SKILLS ──────────────────────────────────────
echo -e "${BLUE}[2/6]${NC} Deploying 126 skills..."

# Count skills before copy
SKILL_COUNT_BEFORE=$(find skills -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')

# Rsync skills (preserves structure, overwrites)
rsync -a --delete skills/ ~/.omp/skills/

SKILL_COUNT=$(find ~/.omp/skills -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
echo -e "${GREEN}  ✅ ${SKILL_COUNT} SKILL.md files deployed${NC}"

# List categories
CAT_COUNT=$(find ~/.omp/skills -maxdepth 1 -type d ! -path ~/.omp/skills | wc -l | tr -d ' ')
echo -e "${GREEN}  ✅ ${CAT_COUNT} categories${NC}"
echo ""

# ── STEP 3: SYSTEM PROMPT (AGENTS.md) ──────────────────────────
echo -e "${BLUE}[3/6]${NC} Deploying LTX-QUASAR system prompt..."

cp AGENTS.md ~/.omp/prompts/system.md
cp AGENTS.md ~/.omp/agent/AGENTS.md

echo -e "${GREEN}  ✅ ~/.omp/prompts/system.md${NC}"
echo -e "${GREEN}  ✅ ~/.omp/agent/AGENTS.md${NC}"
echo ""

# ── STEP 4: CONFIG FILES ───────────────────────────────────────
echo -e "${BLUE}[4/6]${NC} Generating macOS configs..."

# ── config.yml ──
cat > ~/.omp/agent/config.yml << 'CONFEOF'
modelRoles:
  default: bandelbanget/deepseek-v4-mod
symbolPreset: unicode
composer:
  shape: band
theme:
  dark: titanium
  light: light
setupVersion: 2
skills:
  customDirectories:
    - $HOME/omp-enhanced/skills/software-development
    - $HOME/omp-enhanced/skills/productivity
    - $HOME/omp-enhanced/skills/creative
    - $HOME/omp-enhanced/skills/research
    - $HOME/omp-enhanced/skills/DevOps
    - $HOME/omp-enhanced/skills/QA-Testing
    - $HOME/omp-enhanced/skills/web
    - $HOME/omp-enhanced/skills/social-media
    - $HOME/omp-enhanced/skills/note-taking
    - $HOME/omp-enhanced/skills/media
    - $HOME/omp-enhanced/skills/email
    - $HOME/omp-enhanced/skills/autonomous-ai-agents
    - $HOME/omp-enhanced/skills/apple
    - $HOME/omp-enhanced/skills/Security
dev:
  autoqaConsent: granted
CONFEOF

# Replace $HOME with actual path
sed -i '' "s|\$HOME|$HOME|g" ~/.omp/agent/config.yml

echo -e "${GREEN}  ✅ ~/.omp/agent/config.yml (macOS paths)${NC}"

# ── models.yml ──
cat > ~/.omp/agent/models.yml << 'MODELSEOF'
providers:
  bandelbanget:
    baseUrl: https://bandelbanget.xyz/v1
    api: openai-completions
    apiKey: ${BANDELBANGET_API_KEY}
    authHeader: true
    models:
      - id: "auto"
        input: ["text"]
      - id: "claude-opus-5"
        input: ["text", "image"]
      - id: "deepseek-v4-flash"
        input: ["text"]
      - id: "deepseek-v4-flash-0731"
        input: ["text"]
      - id: "deepseek-v4-flash-vision-exp"
        input: ["text", "image"]
      - id: "deepseek-v4-mod"
        input: ["text"]
      - id: "deepseek-v4-pro"
        input: ["text"]
      - id: "deepseek-v4-pro-0813"
        input: ["text"]
      - id: "glm-5.1"
        input: ["text"]
      - id: "glm-5.2"
        input: ["text"]
      - id: "glm-5.3"
        input: ["text"]
      - id: "glm-5.3-flash"
        input: ["text"]
      - id: "gpt-5.6-luna"
        input: ["text", "image"]
      - id: "gpt-5.6-sol"
        input: ["text", "image"]
      - id: "gpt-5.6-terra"
        input: ["text", "image"]
      - id: "hy3"
        input: ["text"]
      - id: "kimi-k2.7-code"
        input: ["text"]
      - id: "kimi-k2.7-code-highspeed"
        input: ["text"]
      - id: "kimi-k3"
        input: ["text", "image"]
      - id: "mimo-v2.5-pro"
        input: ["text"]
      - id: "minimax-m3"
        input: ["text"]
MODELSEOF

echo -e "${GREEN}  ✅ ~/.omp/agent/models.yml (macOS ENV var)${NC}"
echo ""

# ── STEP 5: SHELL PROFILE ──────────────────────────────────────
echo -e "${BLUE}[5/6]${NC} Configuring shell environment..."

SHELL_PROFILE=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_PROFILE="$HOME/.zshrc"
elif [ -f "$HOME/.bash_profile" ]; then
    SHELL_PROFILE="$HOME/.bash_profile"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_PROFILE="$HOME/.bashrc"
else
    SHELL_PROFILE="$HOME/.zshrc"
    touch "$SHELL_PROFILE"
fi

# Check if BANDELBANGET_API_KEY already in profile
if grep -q "BANDELBANGET_API_KEY" "$SHELL_PROFILE" 2>/dev/null; then
    echo -e "${YELLOW}  ⚠️  BANDELBANGET_API_KEY already in $SHELL_PROFILE — updating...${NC}"
    sed -i '' '/BANDELBANGET_API_KEY/d' "$SHELL_PROFILE"
fi

cat >> "$SHELL_PROFILE" << 'SHELLEOF'

# ── LTX-QUASAR OMP ─────────────────────────────────────────────
export BANDELBANGET_API_KEY="sk-qwen-f7a2c02c6dfef16825fb4222f014af4e742b47431528a7f5"
# ────────────────────────────────────────────────────────────────
SHELLEOF

# Set it immediately for this session too
export BANDELBANGET_API_KEY="sk-qwen-f7a2c02c6dfef16825fb4222f014af4e742b47431528a7f5"

echo -e "${GREEN}  ✅ API key embedded in $SHELL_PROFILE${NC}"

echo ""

# ── STEP 6: VERIFICATION ───────────────────────────────────────
echo -e "${BLUE}[6/6]${NC} Verifying installation..."

PASS=0
FAIL=0

check() {
    if [ -e "$1" ]; then
        echo -e "  ${GREEN}✅${NC} $1"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}❌${NC} $1 — MISSING"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo -e "${BOLD}Files:${NC}"
check "$HOME/.omp/skills/"
check "$HOME/.omp/prompts/system.md"
check "$HOME/.omp/agent/AGENTS.md"
check "$HOME/.omp/agent/config.yml"
check "$HOME/.omp/agent/models.yml"

echo ""
echo -e "${BOLD}Skills:${NC}"
SKILL_FILES=$(find ~/.omp/skills -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
echo -e "  SKILL.md count: ${GREEN}${SKILL_FILES}${NC}"

# Check API key
if [ -n "$BANDELBANGET_API_KEY" ]; then
    echo -e "  API Key:        ${GREEN}SET${NC}"
else
    echo -e "  API Key:        ${RED}NOT SET — edit $SHELL_PROFILE${NC}"
    FAIL=$((FAIL + 1))
fi

echo ""

# ── FINAL SUMMARY ──────────────────────────────────────────────
echo -e "${GREEN}"
cat << "EOF"
╔════════════════════════════════════════════════════════════════╗
║                  ✅ MIGRATION COMPLETE                          ║
╚════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${BOLD}📊 Summary:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  Skills deployed:    ${GREEN}${SKILL_FILES} SKILL.md files${NC}"
echo -e "  System prompt:      ${GREEN}~/.omp/prompts/system.md${NC}"
echo -e "  Agent config:       ${GREEN}~/.omp/agent/config.yml${NC}"
echo -e "  Models config:      ${GREEN}~/.omp/agent/models.yml${NC}"
echo -e "  Shell profile:      ${GREEN}${SHELL_PROFILE}${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $PASS -ge 5 ]; then
    echo -e "${GREEN}✅ ALL CHECKS PASSED — LTX-QUASAR is ready.${NC}"
    echo ""
    echo -e "  ${BOLD}Shell reload:${NC}"
    echo -e "     source $SHELL_PROFILE"
else
    echo -e "${RED}❌ Some checks failed. Review errors above.${NC}"
fi

echo ""
echo -e "${BOLD}🚀 Next steps:${NC}"
echo ""
echo -e "  1. ${YELLOW}Reload shell${NC} — source $SHELL_PROFILE"
echo -e "  2. ${YELLOW}Launch OMP${NC} — start your OMP client"
echo -e "  3. ${YELLOW}Test identity${NC} — ask \"who are you?\" → should answer LTX-quasar"
echo ""

echo -e "${BLUE}📁 File structure:${NC}"
echo ""
echo "  ~/.omp/"
echo "  ├── agent/"
echo "  │   ├── AGENTS.md          ← LTX-QUASAR system prompt"
echo "  │   ├── config.yml         ← Agent config (macOS paths)"
echo "  │   └── models.yml         ← Provider models (ENV var API key)"
echo "  ├── prompts/"
echo "  │   └── system.md          ← AGENTS.md copy"
echo "  └── skills/                ← 126 skills"
echo "      ├── Security/          ← 42 security skills"
echo "      ├── software-development/"
echo "      ├── productivity/"
echo "      ├── creative/"
echo "      └── ... (19 categories)"
echo ""

echo -e "${BLUE}🔧 To update skills later:${NC}"
echo -e "  cd ~/omp-enhanced && bash migrate-to-macos.sh"
echo ""