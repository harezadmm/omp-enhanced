# Contributing to OMP Enhanced

Kontribusi untuk improve skills library ini sangat diterima!

## 🎯 What to Contribute

### High Priority
- **New Skills** - Workflow baru yang belum ada
- **Skill Updates** - Fix outdated commands/workflows
- **Documentation** - Improve existing SKILL.md files
- **Templates** - Reusable templates untuk common tasks
- **Scripts** - Helper scripts untuk automasi

### Medium Priority
- **Examples** - Real-world use cases
- **Pitfalls** - Common mistakes & solutions
- **References** - Additional documentation
- **Integrations** - Connect skills together

### Low Priority
- **Translations** - Translate docs ke bahasa lain
- **Style improvements** - Better formatting
- **Typo fixes** - Grammar/spelling

## 📝 Skill Structure

Setiap skill harus follow structure ini:

```
skills/
└── category/
    └── skill-name/
        ├── SKILL.md          # REQUIRED - Main documentation
        ├── references/       # OPTIONAL - Additional docs
        │   ├── examples.md
        │   └── troubleshooting.md
        ├── templates/        # OPTIONAL - File templates
        │   └── template.txt
        └── scripts/          # OPTIONAL - Helper scripts
            └── helper.py
```

## 📄 SKILL.md Format

```markdown
---
description: Use when [clear trigger condition in <57 chars]
triggers:
  - trigger phrase 1
  - trigger phrase 2
  - trigger phrase 3
---

# Skill Name

## When to Use

Clear trigger conditions yang explain kapan skill ini relevant.
Sertakan specific scenarios atau keywords.

## Workflow

1. **Step 1 Title**
   ```bash
   exact command here
   ```
   Brief explanation

2. **Step 2 Title**
   ```bash
   another command
   ```
   Explanation

3. **Verification**
   ```bash
   verify command
   ```
   Expected output

## Pitfalls

- **Pitfall 1:** Common mistake
  - Solution: How to fix

- **Pitfall 2:** Another mistake
  - Solution: Fix approach

## Tools Required

- Tool 1 (install: `apt install tool1`)
- Tool 2 (install: `pip install tool2`)
- Tool 3 (manual setup required)

## Related Skills

- `other-skill-1` - When to use instead
- `other-skill-2` - Can combine with this

## References

- [Documentation](https://example.com)
- [Tutorial](https://example.com/tutorial)
```

## ✅ Quality Checklist

Before submitting, ensure:

- [ ] SKILL.md has proper frontmatter
- [ ] Description is <57 chars (for system prompt truncation)
- [ ] Triggers are specific & actionable
- [ ] Workflow steps have exact commands
- [ ] Commands are tested & working
- [ ] Pitfalls section includes common mistakes
- [ ] Tools section lists all dependencies
- [ ] Related skills are linked
- [ ] No sensitive data (API keys, credentials)
- [ ] No hardcoded paths (use variables)
- [ ] Cross-platform compatible (or platform explicitly noted)

## 🔧 Testing Skills

### Manual Testing
```bash
# 1. Copy skill to Hermes
cp -r skills/category/new-skill ~/.hermes/skills/category/

# 2. Test from conversation
hermes chat
> skill_view(name='new-skill')
> [test the workflow]

# 3. Verify all commands work
> [execute each command from SKILL.md]
```

### Automated Testing
```bash
# Check frontmatter format
python scripts/validate_skills.py

# Check for common issues
python scripts/lint_skills.py

# Test all commands (if possible)
python scripts/test_skill_commands.py new-skill
```

## 📤 Submission Process

### 1. Fork & Clone
```bash
git clone https://github.com/your-username/omp-enhanced.git
cd omp-enhanced
```

### 2. Create Branch
```bash
git checkout -b skill/new-skill-name
```

### 3. Add Skill
```bash
mkdir -p skills/category/new-skill
# Create SKILL.md and other files
```

### 4. Test Locally
```bash
# Copy to Hermes & test
cp -r skills/category/new-skill ~/.hermes/skills/category/

# Verify it works
hermes chat
```

### 5. Commit
```bash
git add skills/category/new-skill
git commit -m "Add new-skill for [category]

- Description of what it does
- Key features
- Related skills"
```

### 6. Push & PR
```bash
git push origin skill/new-skill-name

# Create PR on GitHub
gh pr create --title "Add new-skill" --body "Description of skill"
```

## 🎨 Style Guide

### Naming Conventions
- **Skill names:** lowercase-with-hyphens
- **Categories:** lowercase, no spaces
- **Files:** lowercase, use underscores for scripts
- **Variables:** UPPERCASE for environment vars

### Command Style
```bash
# ✅ Good - Explicit, copy-pasteable
apktool d app.apk -o output_dir
cd output_dir
grep -r "premium" smali/

# ❌ Bad - Vague, not executable
decompile the APK
search for premium checks
```

### Documentation Style
```markdown
# ✅ Good - Clear, actionable
Run `apktool d app.apk` to decompile. Output goes to `app/` directory.

# ❌ Bad - Vague, passive voice
The APK should be decompiled using apktool.
```

## 🚫 What NOT to Include

### Security Issues
- Real credentials/API keys
- Actual exploits for unpatched vulnerabilities
- Personal information
- Malicious payloads (conceptual OK, functional NOT OK)

### Legal Issues
- Pirated software
- Copyrighted content
- Trademarked material without permission

### Quality Issues
- Untested commands
- Outdated information
- Broken links
- Platform-specific without note

## 🐛 Reporting Issues

### Bug Reports
Create issue dengan:
- Skill name & category
- Expected behavior
- Actual behavior
- Steps to reproduce
- Environment (OS, Python version, etc.)

### Feature Requests
Create issue dengan:
- Proposed skill name
- Use case / problem it solves
- Example workflow
- Related skills

## 🏆 Recognition

Contributors akan:
- Listed di CONTRIBUTORS.md
- Credited dalam skill frontmatter (jika signifikan)
- Thanked dalam release notes

## 📞 Questions?

- **General questions:** Open GitHub issue
- **Security concerns:** Email maintainer
- **Urgent issues:** Tag @maintainer dalam PR

## 🔄 Review Process

1. **Automated checks** - CI runs linting & validation
2. **Manual review** - Maintainer checks quality
3. **Testing** - Skill tested dalam real environment
4. **Merge** - Merged to main branch
5. **Release** - Included dalam next version

Typical turnaround: 2-7 days

## 📚 Learning Resources

### Writing Good Skills
- Read existing skills untuk examples
- Check `popular-web-designs` for structure inspiration
- Review `github/pr-workflow` for workflow clarity

### Hermes Agent Docs
- [Hermes Documentation](https://hermes-agent.nousresearch.com/docs)
- [Skill Authoring Guide](https://hermes-agent.nousresearch.com/docs/skills)

### Markdown & Documentation
- [Markdown Guide](https://www.markdownguide.org/)
- [GitHub Flavored Markdown](https://github.github.com/gfm/)

---

## 🎉 Thank You!

Setiap contribution, besar atau kecil, helps improve skills library untuk everyone.

**Happy contributing!** 🚀
