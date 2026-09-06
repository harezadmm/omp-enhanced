---
name: production-package-delivery
description: "One-command installer packages with Docker and docs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [deployment, packaging, installer, docker, documentation, production]
    related_skills: [github-repo-management, github-pr-workflow]
---

# Production Package Delivery

Build complete end-to-end installer packages for production deployment. When a user asks for "one command setup" or "production-ready package", deliver a comprehensive installer with all infrastructure.

## When to Use

- User requests "one command install/setup"
- User wants production-ready deployment package
- Delivering a complete tool/service that others will install
- Previously built separate components, user wants unified installer

## Core Components

A complete package includes:

1. **Interactive installer script** (`install.sh` or `setup.ps1`)
2. **Docker infrastructure** (Dockerfile, docker-compose.yml, health checks)
3. **Configuration generation** (.env templates, config files)
4. **Deployment automation** (skill/resource deployment)
5. **Comprehensive documentation** (README, quick start, testing guides)
6. **Production support** (PM2/systemd, logging, monitoring)

## Installer Best Practices

### Interactive Setup Pattern

```bash
#!/bin/bash
set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Project Installer v1.0.0 ===${NC}"

# Dependency checks
command -v docker >/dev/null 2>&1 || { echo -e "${RED}Error: docker required${NC}"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo -e "${RED}Error: docker-compose required${NC}"; exit 1; }

# Interactive prompts
echo -e "\n${YELLOW}Select provider:${NC}"
echo "1) OpenRouter"
echo "2) Anthropic"
echo "3) OpenAI"
read -p "Choice [1-3]: " PROVIDER_CHOICE

case $PROVIDER_CHOICE in
  1) PROVIDER="openrouter" ;;
  2) PROVIDER="anthropic" ;;
  3) PROVIDER="openai" ;;
  *) echo -e "${RED}Invalid choice${NC}"; exit 1 ;;
esac

# API key collection with validation
while true; do
  read -sp "Enter ${PROVIDER} API key: " API_KEY
  echo
  if [ -n "$API_KEY" ]; then
    break
  fi
  echo -e "${RED}API key cannot be empty${NC}"
done

# Generate .env
cat > .env <<EOF
PROVIDER=${PROVIDER}
API_KEY=${API_KEY}
PORT=3000
LOG_LEVEL=info
EOF

echo -e "${GREEN}✓ Configuration generated${NC}"

# Deploy resources
echo -e "\n${YELLOW}Deploying skills...${NC}"
mkdir -p skills
cp -r skill-library/* skills/
echo -e "${GREEN}✓ Skills deployed${NC}"

# Docker setup
echo -e "\n${YELLOW}Building Docker image...${NC}"
docker-compose build
echo -e "${GREEN}✓ Docker image built${NC}"

# Start services
echo -e "\n${YELLOW}Starting services...${NC}"
docker-compose up -d
echo -e "${GREEN}✓ Services started${NC}"

# Health check with retry
echo -e "\n${YELLOW}Waiting for service...${NC}"
for i in {1..30}; do
  if curl -sf http://localhost:3000/health >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Service healthy${NC}"
    break
  fi
  sleep 2
  if [ $i -eq 30 ]; then
    echo -e "${RED}Service failed to start${NC}"
    docker-compose logs
    exit 1
  fi
done

echo -e "\n${GREEN}=== Installation Complete ===${NC}"
echo -e "Service running at: ${YELLOW}http://localhost:3000${NC}"
echo -e "View logs: ${YELLOW}docker-compose logs -f${NC}"
echo -e "Stop: ${YELLOW}docker-compose down${NC}"
```

### Key Installer Features

1. **Error handling**: `set -e` fails fast on errors
2. **Validation**: Check dependencies before proceeding
3. **Retry logic**: Health checks with timeout
4. **User feedback**: Colored output for status (✓/✗)
5. **Interactive prompts**: Guide user through configuration
6. **Idempotent**: Safe to re-run without breaking existing setup
7. **Cleanup on failure**: Show logs when something breaks

## Docker Infrastructure

### Dockerfile Best Practices

```dockerfile
FROM node:18-alpine AS base
WORKDIR /app

# Dependencies layer (cached unless package.json changes)
COPY package*.json ./
RUN npm ci --only=production

# Application layer
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node healthcheck.js

EXPOSE 3000
CMD ["node", "index.js"]
```

### docker-compose.yml with Health Checks

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    env_file: .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 40s
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Documentation Structure

A complete package needs:

```
/
├── README.md              # Overview, features, architecture
├── QUICKSTART.md          # Fast path to running system
├── docs/
│   ├── installation.md    # Detailed install options
│   ├── configuration.md   # All config options explained
│   ├── deployment.md      # Production deployment guide
│   ├── testing.md         # How to test the system
│   ├── troubleshooting.md # Common issues + solutions
│   └── api.md            # API reference (if applicable)
├── install.sh             # One-command installer
├── docker-compose.yml     # Container orchestration
├── Dockerfile            # Container image
└── .env.example          # Configuration template
```

### README.md Template

```markdown
# Project Name

One-line description.

## Quick Start

```bash
curl -sSL https://example.com/install.sh | bash
# OR
git clone https://github.com/user/repo && cd repo && bash install.sh
```

## Features

- Feature A
- Feature B
- Feature C

## Architecture

[Diagram or brief explanation]

## Documentation

- [Quick Start](QUICKSTART.md)
- [Installation Guide](docs/installation.md)
- [Configuration](docs/configuration.md)
- [Deployment](docs/deployment.md)
- [API Reference](docs/api.md)

## Requirements

- Docker 20.10+
- docker-compose 2.0+
- 2GB RAM minimum

## Support

- Issues: https://github.com/user/repo/issues
- Docs: https://example.com/docs
```

## GitHub Actions Integration Pitfall

**CRITICAL**: When your installer or CI/CD pipeline updates `.github/workflows/`, the default `GITHUB_TOKEN` will fail with:

```
! [remote rejected] main -> main (refusing to allow a GitHub App to create or update workflow)
```

**Root Cause**: `GITHUB_TOKEN` lacks `workflow` scope to modify workflow files.

**Solution**: Generate Personal Access Token with `workflow` scope:

1. GitHub Settings → Developer settings → Personal access tokens
2. Generate token with scopes:
   - ✅ `repo` (full control)
   - ✅ `workflow` (update workflows)
3. Store as secret: `gh secret set GH_PAT_WORKFLOW`
4. Use in workflows:

```yaml
- name: Push workflow changes
  run: git push
  env:
    GITHUB_TOKEN: ${{ secrets.GH_PAT_WORKFLOW }}
```

## PM2 Production Setup (Node.js)

```bash
# Install PM2
npm install -g pm2

# Start with config
pm2 start ecosystem.config.js

# Enable startup script
pm2 startup
pm2 save
```

**ecosystem.config.js:**

```javascript
module.exports = {
  apps: [{
    name: 'app',
    script: './index.js',
    instances: 'max',
    exec_mode: 'cluster',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    time: true,
    max_memory_restart: '1G'
  }]
};
```

## Testing Before Delivery

Before marking package complete:

1. **Fresh environment test**: Run installer on clean Docker container
2. **Idempotency test**: Run installer twice, verify second run succeeds
3. **Service health**: Verify health checks pass
4. **Core functionality**: Test primary use case end-to-end
5. **Documentation accuracy**: Verify commands in docs actually work
6. **Error handling**: Break something (wrong API key), verify helpful error

```bash
# Fresh environment test
docker run -it --rm -v $(pwd):/src ubuntu:22.04 bash
cd /src && bash install.sh

# Idempotency test
bash install.sh  # First run
bash install.sh  # Should succeed without errors
```

## User Preference: One Command, No Options

When user says "buatin one command setup aja" (just make a one-command setup):

**USER WANTS**: Single unified installer, NOT separate manual steps.

**WRONG APPROACH**:
- Multiple commands to run
- "Choose method A or method B"
- Manual configuration steps

**RIGHT APPROACH**:
- `bash install.sh` handles EVERYTHING
- Interactive prompts for necessary choices (provider, API key)
- Auto-detects and installs dependencies where possible
- Zero manual config file editing

## Checklist

Before delivering a production package:

- [ ] Single-command installer (`install.sh`)
- [ ] Interactive configuration (prompts for required values)
- [ ] Docker + docker-compose setup
- [ ] Health checks configured
- [ ] Comprehensive README with Quick Start
- [ ] Installation, deployment, testing docs
- [ ] Troubleshooting guide
- [ ] All components tested end-to-end in fresh environment
- [ ] GitHub Actions workflow scope issue documented (if applicable)
- [ ] Production deployment option (PM2/systemd/Docker)
- [ ] Logging and monitoring configured

## Quick Reference

| Task | Command |
|------|---------|
| Create installer | Write interactive `install.sh` with prompts, validation, health checks |
| Docker setup | Dockerfile + docker-compose.yml with health checks |
| Generate configs | Create .env from prompts, deploy resources |
| Test fresh install | `docker run -it ubuntu:22.04` → run installer |
| Test idempotency | Run installer twice, verify success |
| Fix workflow 403 | Generate PAT with `workflow` scope |
| Production deploy | PM2 with cluster mode + startup script |