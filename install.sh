#!/bin/bash

# OMP Enhanced - One Command Setup Script
# Version: 2.0.0
# Date: 2026-09-06

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
cat << "EOF"
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║              OMP ENHANCED - ONE COMMAND SETUP                  ║
║                      Version 2.0.0                             ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check if running as root (disabled for Docker/root environments)
# if [ "$EUID" -eq 0 ]; then 
#    echo -e "${RED}❌ Please don't run as root${NC}"
#    exit 1
# fi

echo -e "${YELLOW}📋 Starting installation...${NC}\n"

# Step 1: Setup OMP directory
echo -e "${BLUE}[1/7]${NC} Setting up OMP directory..."
mkdir -p omp
echo -e "${GREEN}✅ OMP directory ready${NC}\n"

# Step 2: Skip dependencies (standalone mode)
echo -e "${BLUE}[2/7]${NC} Skipping Node.js dependencies (standalone)..."
echo -e "${GREEN}✅ Standalone mode${NC}\n"

# Step 3: Configure API keys
echo -e "${BLUE}[3/7]${NC} Configuring API keys..."
echo ""
echo -e "${YELLOW}Choose your AI provider:${NC}"
echo "1) OpenAI (GPT-4, GPT-3.5)"
echo "2) Anthropic (Claude)"
echo "3) Google (Gemini)"
echo "4) Skip (configure manually later)"
echo ""
read -p "Select [1-4]: " provider_choice

API_KEY=""
BASE_URL=""
DEFAULT_MODEL=""

case $provider_choice in
    1)
        read -p "Enter OpenAI API key (sk-...): " API_KEY
        BASE_URL="https://api.openai.com/v1"
        DEFAULT_MODEL="gpt-4"
        PROVIDER="openai"
        ;;
    2)
        read -p "Enter Anthropic API key (sk-ant-...): " API_KEY
        BASE_URL="https://api.anthropic.com"
        DEFAULT_MODEL="claude-3-opus-20240229"
        PROVIDER="anthropic"
        ;;
    3)
        read -p "Enter Google API key: " API_KEY
        BASE_URL="https://generativelanguage.googleapis.com/v1beta"
        DEFAULT_MODEL="gemini-pro"
        PROVIDER="google"
        ;;
    4)
        echo -e "${YELLOW}⚠️  Skipping API configuration${NC}"
        ;;
    *)
        echo -e "${RED}❌ Invalid choice${NC}"
        exit 1
        ;;
esac

if [ ! -z "$API_KEY" ]; then
    # Create .env file
    cat > .env << ENVEOF
# OMP Enhanced - API Configuration
${PROVIDER^^}_API_KEY=${API_KEY}
${PROVIDER^^}_BASE_URL=${BASE_URL}
DEFAULT_PROVIDER=${PROVIDER}
DEFAULT_MODEL=${DEFAULT_MODEL}

# Skills configuration
OMP_SKILLS_PATH=\${HOME}/.omp/skills

# System prompt
OMP_SYSTEM_PROMPT=\${HOME}/.omp/prompts/system.md
ENVEOF
    echo -e "${GREEN}✅ API configured (.env created)${NC}\n"
else
    echo -e "${YELLOW}⚠️  API not configured (manual setup required)${NC}\n"
fi

# Step 4: Create config.json
echo -e "${BLUE}[4/7]${NC} Creating config.json..."
if [ ! -z "$API_KEY" ]; then
    cat > config.json << CONFEOF
{
  "providers": {
    "${PROVIDER}": {
      "apiKey": "${API_KEY}",
      "baseURL": "${BASE_URL}",
      "models": ["${DEFAULT_MODEL}"]
    }
  },
  "defaultProvider": "${PROVIDER}",
  "defaultModel": "${DEFAULT_MODEL}",
  "systemPrompt": {
    "file": "~/.omp/prompts/system.md",
    "autoReload": true
  },
  "skills": {
    "directory": "~/.omp/skills",
    "autoLoad": true,
    "categories": [
      "security",
      "github",
      "software-development",
      "creative",
      "productivity",
      "mlops",
      "autonomous-ai-agents"
    ]
  },
  "server": {
    "port": 3000,
    "host": "0.0.0.0"
  }
}
CONFEOF
    echo -e "${GREEN}✅ config.json created${NC}\n"
else
    echo -e "${YELLOW}⚠️  config.json not created (manual setup required)${NC}\n"
fi

# Step 5: Deploy skills
echo -e "${BLUE}[5/7]${NC} Deploying OMP Enhanced skills..."
mkdir -p ~/.omp/skills
cp -r skills/* ~/.omp/skills/ 2>/dev/null || echo -e "${YELLOW}⚠️  Skills directory not found (clone omp-enhanced first)${NC}"
SKILL_COUNT=$(find ~/.omp/skills -name "SKILL.md" 2>/dev/null | wc -l)
echo -e "${GREEN}✅ Deployed ${SKILL_COUNT} skills${NC}\n"

# Step 6: Load system prompt
echo -e "${BLUE}[6/7]${NC} Loading system prompt..."
mkdir -p ~/.omp/prompts
if [ -f "AGENTS.md" ]; then
    cp AGENTS.md ~/.omp/prompts/system.md
    echo -e "${GREEN}✅ System prompt loaded (AGENTS.md)${NC}\n"
else
    echo -e "${YELLOW}⚠️  AGENTS.md not found (clone omp-enhanced first)${NC}\n"
fi

# Step 7: Install PM2 (optional)
echo -e "${BLUE}[7/7]${NC} Install PM2 for production? (recommended)"
read -p "Install PM2? [y/N]: " install_pm2
if [[ $install_pm2 =~ ^[Yy]$ ]]; then
    npm install -g pm2
    echo -e "${GREEN}✅ PM2 installed${NC}\n"
else
    echo -e "${YELLOW}⚠️  PM2 not installed${NC}\n"
fi

# Final summary
echo -e "${GREEN}"
cat << "EOF"
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║              ✨ INSTALLATION COMPLETE ✨                       ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${BLUE}📊 Installation Summary:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "OMP Directory:    ${GREEN}./omp${NC}"
echo -e "Skills Deployed:  ${GREEN}${SKILL_COUNT} workflows${NC}"
echo -e "System Prompt:    ${GREEN}~/.omp/prompts/system.md${NC}"
echo -e "Config File:      ${GREEN}./omp/config.json${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BLUE}🚀 Quick Start:${NC}"
echo ""
echo -e "  ${YELLOW}Development mode:${NC}"
echo "    cd omp"
echo "    npm run dev"
echo ""
echo -e "  ${YELLOW}Production mode (with PM2):${NC}"
echo "    cd omp"
echo "    pm2 start npm --name omp -- start"
echo "    pm2 save"
echo "    pm2 logs omp"
echo ""
echo -e "  ${YELLOW}Access:${NC}"
echo "    http://localhost:3000"
echo ""

echo -e "${BLUE}🧪 Test Commands:${NC}"
echo ""
echo "  1. Test API connection:"
echo "     Request: \"Hello, are you working?\""
echo ""
echo "  2. Test skill loading:"
echo "     Request: \"Mod this APK to bypass premium check\""
echo "     Expected: apk-modding-workflow auto-loads"
echo ""
echo "  3. Test another skill:"
echo "     Request: \"Test this URL for SQL injection\""
echo "     Expected: sqlmap skill auto-loads"
echo ""

echo -e "${BLUE}📖 Documentation:${NC}"
echo ""
echo "  • Full guide:       cat OMP_SETUP_GUIDE.md"
echo "  • Integration:      cat FINAL_HANDOFF.md"
echo "  • Quick reference:  cat QUICK_API_SETUP.txt"
echo ""

echo -e "${GREEN}✨ Setup complete! Start OMP with: ${YELLOW}cd omp && npm run dev${NC}"
echo ""
