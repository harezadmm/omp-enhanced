# OMP Enhanced - Testing Checklist

Use this checklist to verify your installation is working correctly.

---

## Pre-Installation Checks

### System Requirements
- [ ] Node.js v16+ or v18+ installed (`node --version`)
- [ ] npm v8+ installed (`npm --version`)
- [ ] Git installed (`git --version`)
- [ ] At least 500MB free disk space
- [ ] Internet connection active

### API Prerequisites
- [ ] OpenAI API key obtained (https://platform.openai.com/api-keys)
- [ ] OR Anthropic API key obtained (https://console.anthropic.com/)
- [ ] OR Google API key obtained (https://makersuite.google.com/app/apikey)
- [ ] API key balance checked (has credits)

---

## Installation Process Checks

### Run installer
```bash
git clone https://github.com/harezadmm/omp-enhanced.git
cd omp-enhanced
bash install.sh
```

### During Installation
- [ ] [1/7] OMP.sh repository cloned successfully
- [ ] [2/7] Dependencies installed without errors
- [ ] [3/7] API provider selected (1-4)
- [ ] [3/7] API key entered correctly
- [ ] [4/7] config.json generated
- [ ] [5/7] Skills deployed (126 files)
- [ ] [6/7] System prompt loaded
- [ ] [7/7] PM2 installation completed (if chosen)

### Post-Installation Files
- [ ] `./omp/` directory exists
- [ ] `./omp/.env` file created (if API configured)
- [ ] `./omp/config.json` file created
- [ ] `~/.omp/skills/` directory has 126 SKILL.md files
- [ ] `~/.omp/prompts/system.md` exists

**Verify skill count:**
```bash
find ~/.omp/skills -name "SKILL.md" | wc -l
# Expected output: 126
```

---

## Functional Testing

### Test 1: Start Server (Development Mode)

**Command:**
```bash
cd omp
npm run dev
```

**Expected:**
- [ ] Server starts without errors
- [ ] Output shows: `Server running on http://localhost:3000`
- [ ] No error messages in console
- [ ] Process doesn't crash within 30 seconds

**Browser Test:**
- [ ] Open http://localhost:3000
- [ ] Web UI loads successfully
- [ ] Chat interface visible
- [ ] No console errors in browser DevTools

---

### Test 2: API Connection

**Test Command:**
```
Hello, are you working?
```

**Expected Response:**
- [ ] AI responds within 5-10 seconds
- [ ] Response is coherent and relevant
- [ ] No error messages
- [ ] Response shows configured provider (GPT-4/Claude/Gemini)

**If Failed:**
- Check `.env` file has correct API key
- Verify API key has credits: `curl https://api.openai.com/v1/models -H "Authorization: Bearer YOUR_KEY"`
- Check network connectivity
- Review server console logs

---

### Test 3: Skill Auto-Loading (APK Modding)

**Test Command:**
```
I need to mod this APK file to bypass the premium check. The app is a subscription-based note-taking app.
```

**Expected Response:**
- [ ] Response mentions `apk-modding-workflow` skill
- [ ] Response includes skill loading confirmation
- [ ] Provides step-by-step APK modding instructions
- [ ] Mentions tools: APKTool, JADX, sign.py
- [ ] Asks for APK file path or provides workflow outline

**Skill Loading Indicators:**
- [ ] Server console shows: `Loading skill: apk-modding-workflow`
- [ ] Response structure follows skill template
- [ ] References skill documentation

---

### Test 4: Skill Auto-Loading (SQL Injection)

**Test Command:**
```
Test this URL for SQL injection vulnerabilities: https://example.com/product?id=123
```

**Expected Response:**
- [ ] Response mentions `sqlmap` skill
- [ ] Provides sqlmap command syntax
- [ ] Explains injection testing methodology
- [ ] Warns about legal considerations
- [ ] Offers step-by-step testing approach

**Verification:**
```bash
# Check skill exists
cat ~/.omp/skills/security/sqlmap/SKILL.md | head -20
```

---

### Test 5: System Prompt Integration

**Test Command:**
```
What skills and capabilities do you have?
```

**Expected Response:**
- [ ] Lists multiple skill categories (security, GitHub, creative, etc.)
- [ ] Mentions 126 expert workflows
- [ ] References AGENTS.md system prompt
- [ ] Describes auto-loading functionality
- [ ] Mentions specific skill examples (APK modding, SQL injection, etc.)

**Verification:**
```bash
# Check system prompt loaded
cat ~/.omp/prompts/system.md | head -50
```

---

### Test 6: Code Generation Quality

**Test Command:**
```
Write a Python script to scrape product prices from an e-commerce website and save to CSV
```

**Expected Response:**
- [ ] Clean, working Python code
- [ ] Includes imports (requests, BeautifulSoup, csv)
- [ ] Has error handling
- [ ] Comments only for non-obvious logic
- [ ] No boilerplate or placeholder comments
- [ ] Follows lazy-senior-dev principles

**Code Quality Checks:**
- [ ] No comments like `# import modules` or `# handle error`
- [ ] Uses stdlib/native libraries first
- [ ] Minimal dependencies
- [ ] Runs without modification (copy-paste ready)

---

### Test 7: GitHub Skills Integration

**Test Command:**
```
Create a GitHub pull request for adding dark mode to my React app
```

**Expected Response:**
- [ ] Mentions `github-pr-workflow` skill
- [ ] Provides git commands (branch, commit, push)
- [ ] Shows `gh pr create` command
- [ ] Includes PR title and description template
- [ ] Asks for repository details

**Verification:**
```bash
# Check GitHub skill exists
cat ~/.omp/skills/github/github-pr-workflow/SKILL.md | head -30
```

---

### Test 8: Creative Skills

**Test Command:**
```
Create an ASCII art logo for my project called "DataFlow"
```

**Expected Response:**
- [ ] Mentions `ascii-art` skill
- [ ] Provides ASCII art output
- [ ] Uses pyfiglet or similar tool syntax
- [ ] Offers multiple font options
- [ ] Shows actual ASCII rendering

---

### Test 9: Multi-Turn Conversation

**Test Series:**
```
1. "I want to build a Node.js REST API"
2. "Add authentication with JWT"
3. "Now add rate limiting"
```

**Expected Behavior:**
- [ ] Maintains context across all 3 messages
- [ ] Each response builds on previous
- [ ] Doesn't repeat boilerplate code
- [ ] Shows only the diff/new code in responses 2-3
- [ ] Remembers project structure

---

### Test 10: Error Handling

**Test Command:**
```
[Send gibberish]: asdf qwer zxcv 1234
```

**Expected Response:**
- [ ] AI asks for clarification
- [ ] Doesn't crash or return errors
- [ ] Maintains professional tone
- [ ] Offers to help with common tasks

---

## Production Deployment Checks

### PM2 Setup (If Installed)

**Start with PM2:**
```bash
cd omp
pm2 start npm --name omp -- start
```

**Checks:**
- [ ] `pm2 list` shows OMP running
- [ ] Status is `online` not `errored`
- [ ] CPU usage reasonable (<50%)
- [ ] Memory usage reasonable (<500MB)
- [ ] `pm2 logs omp` shows no errors

**Auto-start on boot:**
```bash
pm2 startup
pm2 save
```

- [ ] Commands execute successfully
- [ ] Reboot test: Server auto-starts after reboot

---

## Performance Testing

### Response Time Check
- [ ] Simple queries respond in <3 seconds
- [ ] Skill-loading queries respond in <8 seconds
- [ ] Code generation completes in <15 seconds
- [ ] No timeouts under normal load

### Concurrent Requests
```bash
# Send 5 requests simultaneously
for i in {1..5}; do
  curl -X POST http://localhost:3000/api/chat \
    -H "Content-Type: application/json" \
    -d '{"message":"Hello"}' &
done
wait
```

- [ ] All requests complete successfully
- [ ] Server doesn't crash
- [ ] Response times remain acceptable

---

## Security Checks

### API Key Protection
- [ ] `.env` file not committed to Git
- [ ] `.env` in `.gitignore`
- [ ] API key not visible in browser DevTools
- [ ] API key not in error messages

### Skill Content Validation
```bash
# Check skills don't contain sensitive data
grep -r "api[_-]key" ~/.omp/skills/
grep -r "password" ~/.omp/skills/
grep -r "secret" ~/.omp/skills/
```

- [ ] No hardcoded credentials found
- [ ] No personal information in skills

---

## Integration Health Check

### Full System Status
```bash
cd /tmp/omp-enhanced && cat << 'HEALTH' > health_check.sh
#!/bin/bash

echo "🏥 OMP Enhanced - Health Check"
echo "════════════════════════════════════════════════════════════"

# Check OMP directory
if [ -d "omp" ]; then
  echo "✅ OMP directory exists"
else
  echo "❌ OMP directory missing"
fi

# Check config files
if [ -f "omp/.env" ] || [ -f "omp/config.json" ]; then
  echo "✅ Config files present"
else
  echo "⚠️  Config files missing (manual setup required)"
fi

# Check skills
SKILL_COUNT=$(find ~/.omp/skills -name "SKILL.md" 2>/dev/null | wc -l)
if [ "$SKILL_COUNT" -eq 126 ]; then
  echo "✅ All 126 skills deployed"
elif [ "$SKILL_COUNT" -gt 0 ]; then
  echo "⚠️  Only $SKILL_COUNT skills found (expected 126)"
else
  echo "❌ No skills found"
fi

# Check system prompt
if [ -f ~/.omp/prompts/system.md ]; then
  echo "✅ System prompt loaded"
else
  echo "❌ System prompt missing"
fi

# Check server process
if pgrep -f "node.*omp" > /dev/null; then
  echo "✅ OMP server running"
else
  echo "⚠️  OMP server not running"
fi

# Check API connectivity (if server running)
if curl -s http://localhost:3000 > /dev/null 2>&1; then
  echo "✅ Web UI accessible"
else
  echo "⚠️  Web UI not accessible"
fi

echo "════════════════════════════════════════════════════════════"
echo "Health check complete"
HEALTH

chmod +x health_check.sh
bash health_check.sh
```

**Expected Output:**
```
🏥 OMP Enhanced - Health Check
════════════════════════════════════════════════════════════
✅ OMP directory exists
✅ Config files present
✅ All 126 skills deployed
✅ System prompt loaded
✅ OMP server running
✅ Web UI accessible
════════════════════════════════════════════════════════════
Health check complete
```

---

## Rollback Procedure (If Needed)

### Complete Uninstall
```bash
# Stop server
cd omp
pm2 stop omp
pm2 delete omp

# Or kill process
pkill -f "node.*omp"

# Remove OMP
cd ..
rm -rf omp

# Remove skills
rm -rf ~/.omp

# Remove package
cd omp-enhanced
cd ..
rm -rf omp-enhanced
```

### Reinstall
```bash
# Start fresh
git clone https://github.com/harezadmm/omp-enhanced.git
cd omp-enhanced
bash install.sh
```

---

## Success Criteria

Your installation is SUCCESSFUL if:

- [x] All 10 functional tests pass
- [x] Health check shows all ✅
- [x] Skills auto-load correctly
- [x] System prompt integrates properly
- [x] Code generation follows lazy-senior-dev style
- [x] No errors in server logs
- [x] Performance is acceptable (<10s response time)
- [x] Production deployment stable (if using PM2)

---

## Support

If any test fails:

1. Check `QUICK_START.md` troubleshooting section
2. Review `OMP_SETUP_GUIDE.md` for detailed setup
3. Open issue: https://github.com/harezadmm/omp-enhanced/issues
4. Include:
   - Failed test number
   - Error messages from console
   - Output of `bash health_check.sh`
   - Node.js version (`node --version`)

---

**Test Date:** _______________

**Tester:** _______________

**Result:** ☐ PASS  ☐ FAIL

**Notes:**
```
[Add any observations or issues here]
```
