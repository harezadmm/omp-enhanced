---
name: bulk-repo-skill-migration
description: Copy skill libraries between repos with parallel cloning.
tags: [git, skills, repository-management, bulk-operations]
---

# Bulk Repository Skill Migration

Use when copying large skill/knowledge libraries from one GitHub repo to another without modifying the source repo.

## When to Use

- Merging skill libraries from multiple sources into one unified repo
- Migrating Hermes Agent skills between forks or deployment repos
- Consolidating documentation/knowledge bases across repositories
- User requests "copy all skills from repo X to repo Y"

## Workflow

1. **Clone both repos in parallel** to `/tmp/` for speed:
   ```bash
   cd /tmp
   git clone https://github.com/source/repo-a.git &
   git clone https://github.com/target/repo-b.git &
   wait
   ```

2. **Verify source structure** before copying:
   ```bash
   find /tmp/repo-a/skills -type f -name "SKILL.md" | wc -l
   ls -la /tmp/repo-a/skills/
   ```

3. **Create target directory structure** if missing:
   ```bash
   mkdir -p /tmp/repo-b/skills
   ```

4. **Copy recursively** preserving directory structure:
   ```bash
   cp -r /tmp/repo-a/skills/* /tmp/repo-b/skills/
   ```

5. **Copy additional sources** (e.g., local profile skills):
   ```bash
   cp -r ~/.hermes/profiles/<profile>/skills/* /tmp/repo-b/skills/
   ```

6. **Stage and commit**:
   ```bash
   cd /tmp/repo-b
   git add skills/
   git commit -m "Add all skills from [source repos]"
   ```

7. **Verify commit** before push:
   ```bash
   git status
   git log --oneline -3
   find skills -type f -name "*.md" | wc -l
   ```

8. **Push requires credentials** — tell user to push manually or setup git auth:
   ```bash
   git push origin main
   ```

## Pitfalls

- **Do NOT modify source repo** — only read from it, write to target
- **Git credentials** — `git push` in Docker/headless environments needs token/SSH setup; better to commit locally and tell user to push from their authenticated shell
- **Symlinks** — `cp -r` follows symlinks by default; use `cp -rL` to dereference or verify target repo doesn't break
- **Large repos** — RedMess-sized repos (11K+ files) take 30-60s to clone; use parallel clones and don't re-clone if already present
- **Workspace confusion** — always use `/tmp/` for bulk git operations, NOT user workspace directories
- **File count verification** — always count SKILL.md files before and after to confirm nothing was missed

## Indonesian User Style

User hates options and wants one direct action. For bulk migrations:
- Execute immediately without asking
- Use parallel operations (clone both repos at once)
- Verify with counts, not verbose listings
- Report final status: commit hash, file counts, ready-to-push confirmation

## References

Session 2026-09-06: Successfully migrated 126 SKILL.md files from RedMess + 8 security files from Umi profile → omp-enhanced repo (912 files, 134K insertions).
