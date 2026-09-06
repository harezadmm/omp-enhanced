#!/bin/bash

# OMP Enhanced - Standalone Setup (No npm/pm2)
# Version: 2.0.1-fixed

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
║              OMP ENHANCED - STANDALONE SETUP                   ║
║                      Version 2.0.1                             ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}❌ Please don't run as root${NC}"
   exit 1
fi

echo -e "${YELLOW}📋 Starting installation...${NC}\n"

# Step 1: Setup directories
echo -e "${BLUE}[1/5]${NC} Setting up directories..."
mkdir -p ~/.omp/skills
mkdir -p ~/.omp/prompts
echo -e "${GREEN}✅ Directories ready${NC}\n"

# Step 2: Deploy skills
echo -e "${BLUE}[2/5]${NC} Deploying OMP Enhanced skills..."
if [ -d "skills" ]; then
    cp -r skills/* ~/.omp/skills/
    SKILL_COUNT=$(find ~/.omp/skills -name "SKILL.md" 2>/dev/null | wc -l)
    echo -e "${GREEN}✅ Deployed ${SKILL_COUNT} skills${NC}\n"
else
    echo -e "${YELLOW}⚠️  Skills directory not found${NC}\n"
    SKILL_COUNT=0
fi

# Step 3: Load system prompt
echo -e "${BLUE}[3/5]${NC} Loading system prompt..."
if [ -f "AGENTS.md" ]; then
    cp AGENTS.md ~/.omp/prompts/system.md
    echo -e "${GREEN}✅ System prompt loaded (AGENTS.md)${NC}\n"
else
    echo -e "${YELLOW}⚠️  AGENTS.md not found${NC}\n"
fi

# Step 4: Create simple config
echo -e "${BLUE}[4/5]${NC} Creating configuration..."
cat > ~/.omp/config.yaml << 'CONFEOF'
# OMP Enhanced - Standalone Configuration

skills:
  directory: ~/.omp/skills
  autoLoad: true
  categories:
    - security
    - github
    - software-development
    - creative
    - productivity
    - mlops
    - autonomous-ai-agents

system_prompt:
  file: ~/.omp/prompts/system.md
  autoReload: true
CONFEOF
echo -e "${GREEN}✅ Config created at ~/.omp/config.yaml${NC}\n"

# Step 5: Verification
echo -e "${BLUE}[5/5]${NC} Verifying installation..."
if [ -f ~/.omp/prompts/system.md ] && [ -d ~/.omp/skills ]; then
    echo -e "${GREEN}✅ Installation verified${NC}\n"
else
    echo -e "${RED}❌ Installation incomplete${NC}\n"
    exit 1
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
echo -e "Skills Deployed:  ${GREEN}${SKILL_COUNT} workflows${NC}"
echo -e "System Prompt:    ${GREEN}~/.omp/prompts/system.md${NC}"
echo -e "Config File:      ${GREEN}~/.omp/config.yaml${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BLUE}📖 Files Installed:${NC}"
echo ""
echo "  • Skills:        ~/.omp/skills/"
echo "  • System prompt: ~/.omp/prompts/system.md"
echo "  • Config:        ~/.omp/config.yaml"
echo ""

echo -e "${GREEN}✨ Setup complete! Skills ready for Hermes Agent.${NC}"
echo ""
