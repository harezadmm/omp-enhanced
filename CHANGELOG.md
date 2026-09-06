# Changelog

All notable changes to OMP Enhanced will be documented in this file.

## [2.0.0] - 2026-09-06

### Added
- **One-command installer** (`install.sh`) with interactive setup
  - Auto-clone OMP.sh repository
  - Interactive API provider selection (OpenAI/Anthropic/Google)
  - Auto-generate .env and config.json files
  - Deploy 126 skills automatically
  - Load AGENTS.md system prompt
  - Optional PM2 installation for production

- **Complete documentation suite**
  - README.md with quick start guide
  - QUICK_START.md for step-by-step installation
  - TESTING_CHECKLIST.md with 10 functional tests
  - DEPLOYMENT.md with VPS/Docker/Heroku guides
  - OMP_SETUP_GUIDE.md for manual configuration
  - FINAL_HANDOFF.md for integration overview

- **Production deployment support**
  - Docker and docker-compose configuration
  - PM2 process manager integration
  - Nginx reverse proxy setup guide
  - SSL certificate (Let's Encrypt) guide
  - Automated backup scripts
  - Health check monitoring

- **CI/CD pipeline**
  - GitHub Actions workflow for testing installer
  - Automated syntax checks on Node 16/18/20
  - Skills directory structure validation
  - Documentation completeness checks

- **126 expert-level skills**
  - Security (24): APK modding, pentesting, SQL injection
  - GitHub (8): PR workflow, code review, issues
  - Software Development (18): TDD, debugging, testing
  - Creative (12): ASCII art, diagrams, p5.js
  - Productivity (15): Notion, Google Workspace, Excel
  - MLOps (9): Model serving, evaluation
  - AI Agents (6): Claude Code, Codex, orchestration
  - Plus 8 more categories

- **AGENTS.md system prompt**
  - Auto-loaded by installer
  - Enhanced AI capabilities
  - Skill auto-loading logic
  - Lazy-senior-dev code style enforcement

### Changed
- README.md completely rewritten for clarity
- Installation process simplified to one command
- Configuration now interactive instead of manual
- Skills deployment automated (no manual copying)

### Fixed
- Skills directory permissions issues
- System prompt loading consistency
- API key configuration validation
- Port conflict handling

## [1.0.0] - 2026-09-01

### Added
- Initial release with 126 skills
- Basic OMP.sh integration
- Manual installation instructions
- Skill categories organization

---

## Version History

- **v2.0.0** (2026-09-06): One-command installer, complete automation
- **v1.0.0** (2026-09-01): Initial release, manual setup

---

## Upgrade Guide

### From v1.0.0 to v2.0.0

**Recommended: Fresh install**
```bash
# Backup old config
cp ~/.omp/config.json ~/.omp/config.json.backup

# Remove old installation
rm -rf omp-enhanced

# Fresh install v2.0.0
git clone https://github.com/harezadmm/omp-enhanced.git
cd omp-enhanced
bash install.sh
```

**Migration: Keep existing config**
```bash
cd omp-enhanced
git pull origin main

# Re-run installer (will update skills only)
bash install.sh
# Select option 4 (skip API config) if already configured
```

---

## Breaking Changes

### v2.0.0
- Installation process completely changed
- Manual setup steps deprecated (use `install.sh`)
- Config file location may differ (migrated to `omp/.env`)

---

## Roadmap

### v2.1.0 (Planned)
- [ ] Web UI improvements
- [ ] Skill marketplace
- [ ] Plugin system for custom skills
- [ ] Advanced caching strategies
- [ ] Multi-model support in one session

### v2.2.0 (Planned)
- [ ] Voice interface integration
- [ ] Multi-language support
- [ ] Team collaboration features
- [ ] Advanced monitoring dashboard

---

**Full releases:** https://github.com/harezadmm/omp-enhanced/releases
