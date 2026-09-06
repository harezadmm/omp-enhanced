# OMP Enhanced - Quick Start Guide

## One-Command Installation

```bash
git clone https://github.com/harezadmm/omp-enhanced.git
cd omp-enhanced
bash install.sh
```

## What Happens During Installation

### Step 1: Clone OMP.sh
- Downloads official OMP.sh repository to `./omp`
- If exists, updates to latest version

### Step 2: Install Dependencies
- Runs `npm install` in OMP directory
- Installs all required Node.js packages

### Step 3: Configure API Key
Interactive prompt offers 4 options:

**Option 1: OpenAI**
```
Provider: OpenAI
API Key: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Base URL: https://api.openai.com/v1
Default Model: gpt-4
```

**Option 2: Anthropic**
```
Provider: Anthropic
API Key: sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Base URL: https://api.anthropic.com
Default Model: claude-3-opus-20240229
```

**Option 3: Google**
```
Provider: Google
API Key: AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Base URL: https://generativelanguage.googleapis.com/v1beta
Default Model: gemini-pro
```

**Option 4: Skip**
- Manual configuration required later
- See `OMP_SETUP_GUIDE.md` for details

### Step 4: Generate Config Files

**Created files:**
- `omp/.env` - Environment variables with API key
- `omp/config.json` - OMP configuration with provider settings

### Step 5: Deploy Skills
- Copies 126 skills to `~/.omp/skills/`
- Creates directory structure if not exists

### Step 6: Load System Prompt
- Copies `AGENTS.md` to `~/.omp/prompts/system.md`
- Enables auto-loading of enhanced system prompt

### Step 7: PM2 (Optional)
- Offers to install PM2 for production deployment
- Recommended for production servers

## After Installation

### Development Mode
```bash
cd omp
npm run dev
```
- Hot reload enabled
- Access: http://localhost:3000

### Production Mode
```bash
cd omp
pm2 start npm --name omp -- start
pm2 save
pm2 logs omp
```
- Process manager handles restarts
- Auto-start on system boot
- Logs accessible via PM2

## Testing the Setup

### Test 1: API Connection
```
User: "Hello, are you working?"
Expected: Normal AI response from configured provider
```

### Test 2: Skill Auto-Loading
```
User: "Mod this APK to bypass premium check"
Expected: ✅ apk-modding-workflow skill auto-loads
         Shows skill header in response
```

### Test 3: System Prompt
```
User: "What skills do you have?"
Expected: Lists security, GitHub, creative, etc. categories
         References AGENTS.md system prompt
```

### Test 4: Code Generation
```
User: "Write a Python script to scrape website"
Expected: Clean code with proper error handling
         Follows lazy-senior-dev principles
```

## Troubleshooting

### Issue: "npm install failed"
```bash
# Check Node.js version
node --version  # Should be v16+ or v18+

# Update Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### Issue: "API key invalid"
```bash
# Test OpenAI key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"

# Test Anthropic key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: YOUR_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-opus-20240229","max_tokens":1024,"messages":[{"role":"user","content":"Hello"}]}'
```

### Issue: "Skills not loading"
```bash
# Check skills directory
ls -la ~/.omp/skills/

# Verify skill count
find ~/.omp/skills -name "SKILL.md" | wc -l
# Should output: 126

# Fix permissions
chmod -R 755 ~/.omp/skills
```

### Issue: "Port 3000 already in use"
```bash
# Find process using port
lsof -i :3000

# Kill process
kill -9 $(lsof -t -i :3000)

# Or use different port
PORT=3001 npm run start
```

### Issue: "System prompt not loading"
```bash
# Check file exists
cat ~/.omp/prompts/system.md | head -20

# Verify config.json points to it
cat omp/config.json | grep systemPrompt

# Manually copy if missing
cp AGENTS.md ~/.omp/prompts/system.md
```

## Manual Configuration (If Needed)

### Add API Key After Installation

**Method 1: Edit .env**
```bash
cd omp
nano .env

# Add:
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Method 2: Edit config.json**
```bash
cd omp
nano config.json

# Modify providers section:
{
  "providers": {
    "openai": {
      "apiKey": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "baseURL": "https://api.openai.com/v1",
      "models": ["gpt-4", "gpt-3.5-turbo"]
    }
  }
}
```

### Change Default Model
```bash
cd omp
nano config.json

# Change:
"defaultModel": "gpt-4"
# To:
"defaultModel": "gpt-3.5-turbo"
```

### Use Custom Base URL (Proxy)
```bash
cd omp
nano .env

# Add:
OPENAI_BASE_URL=https://your-proxy.com/v1
```

## Performance Tips

### 1. Use PM2 Cluster Mode
```bash
pm2 start npm --name omp -i max -- start
# Uses all CPU cores
```

### 2. Enable Caching
```bash
# In config.json, add:
{
  "cache": {
    "enabled": true,
    "ttl": 3600
  }
}
```

### 3. Optimize Skills Loading
```bash
# In config.json:
{
  "skills": {
    "preload": ["apk-modding-workflow", "sqlmap", "github-pr-workflow"],
    "lazyLoad": true
  }
}
```

## Next Steps

1. **Read Full Docs**: `cat OMP_SETUP_GUIDE.md`
2. **Explore Skills**: `ls ~/.omp/skills/*/SKILL.md`
3. **Test Integration**: Run all 4 test commands above
4. **Production Deploy**: See `DEPLOYMENT.md`

## Get API Keys

- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/
- **Google**: https://makersuite.google.com/app/apikey

## Support

- **Issues**: https://github.com/harezadmm/omp-enhanced/issues
- **OMP Docs**: https://github.com/secretflow/omp
- **Full Guide**: `OMP_SETUP_GUIDE.md`

---

**Ready to start?**

```bash
bash install.sh
```
