# OMP.sh Setup Guide - Complete Installation

**Date:** 2026-09-06  
**For:** OMP Enhanced v2.0.0 Integration

---

## 📋 Prerequisites

Sebelum mulai, siapkan:
- [ ] API Key dari provider AI (OpenAI, Anthropic, Google, dll)
- [ ] Server/VPS dengan akses root
- [ ] Domain (optional, untuk HTTPS)
- [ ] Node.js 18+ installed

---

## 🚀 Step-by-Step Installation

### Step 1: Install OMP.sh

```bash
# Clone OMP.sh repository
git clone https://github.com/secretflow/omp.git
cd omp

# Install dependencies
npm install

# Or with yarn
yarn install
```

---

### Step 2: Configure API Keys

#### Option A: Environment Variables (.env file)
```bash
# Create .env file
nano .env

# Add your API keys
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
GOOGLE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: Custom endpoints
OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_BASE_URL=https://api.anthropic.com

# Save and exit (Ctrl+X, Y, Enter)
```

#### Option B: Config File (config.json)
```bash
# Create config file
nano config.json
```

```json
{
  "providers": {
    "openai": {
      "apiKey": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "baseURL": "https://api.openai.com/v1",
      "models": ["gpt-4", "gpt-3.5-turbo"]
    },
    "anthropic": {
      "apiKey": "sk-ant-xxxxxxxxxxxxxxxxxxxxx",
      "baseURL": "https://api.anthropic.com",
      "models": ["claude-3-opus", "claude-3-sonnet"]
    },
    "google": {
      "apiKey": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "baseURL": "https://generativelanguage.googleapis.com/v1beta",
      "models": ["gemini-pro"]
    }
  },
  "defaultProvider": "openai",
  "defaultModel": "gpt-4"
}
```

---

### Step 3: Load OMP Enhanced System Prompt

#### Option A: Via Web Interface
```bash
# Start OMP.sh server
npm run start
# atau
yarn start

# Open browser: http://localhost:3000
# Go to: Settings → System Prompt
# Paste content dari AGENTS.md
```

#### Option B: Via Config File
```bash
# Copy AGENTS.md content
cat ~/omp-enhanced-deployed/AGENTS.md

# Edit OMP config
nano config/system-prompt.txt

# Paste AGENTS.md content
# Save and exit
```

#### Option C: Direct Injection (Recommended)
```bash
# Create system prompt file
mkdir -p ~/.omp/prompts

# Copy AGENTS.md
cp ~/omp-enhanced-deployed/AGENTS.md ~/.omp/prompts/system.md

# Configure OMP to use it
nano config.json
```

Add this section:
```json
{
  "systemPrompt": {
    "file": "~/.omp/prompts/system.md",
    "autoReload": true
  }
}
```

---

### Step 4: Deploy Skills Directory

```bash
# Create OMP skills directory
mkdir -p ~/.omp/skills

# Copy all skills
cp -r ~/omp-enhanced-deployed/skills/* ~/.omp/skills/

# Verify deployment
find ~/.omp/skills -name "SKILL.md" | wc -l
# Expected: 126

# Set permissions
chmod -R 755 ~/.omp/skills
```

---

### Step 5: Configure Skills Path in OMP

#### Option A: Environment Variable
```bash
# Add to .env
echo "OMP_SKILLS_PATH=$HOME/.omp/skills" >> .env
```

#### Option B: Config File
```bash
nano config.json
```

Add:
```json
{
  "skills": {
    "directory": "~/.omp/skills",
    "autoLoad": true,
    "categories": [
      "security",
      "github",
      "software-development",
      "creative",
      "productivity"
    ]
  }
}
```

---

### Step 6: Test Integration

#### Test 1: Start OMP Server
```bash
# Development mode
npm run dev

# Production mode
npm run start

# With PM2 (recommended for production)
pm2 start npm --name "omp" -- start
```

#### Test 2: Check Skills Loading
```bash
# Open OMP console
curl http://localhost:3000/api/skills/list

# Expected response:
{
  "skills": 126,
  "categories": 49,
  "loaded": true
}
```

#### Test 3: Test Auto-Skill Loading
```
Request di OMP: "Mod this APK to bypass premium check"

Expected Output:
✅ Loading skill: apk-modding-workflow
✅ Trigger matched: "mod APK"
✅ Executing workflow...
```

---

## 🔧 Advanced Configuration

### Custom Model Settings
```json
{
  "models": {
    "gpt-4": {
      "temperature": 0.7,
      "maxTokens": 4096,
      "topP": 1.0
    },
    "claude-3-opus": {
      "temperature": 0.8,
      "maxTokens": 8192,
      "topP": 0.9
    }
  }
}
```

### Skill Auto-Loading Rules
```json
{
  "skills": {
    "autoLoad": {
      "enabled": true,
      "triggers": {
        "apk-modding-workflow": ["mod apk", "bypass premium", "crack app"],
        "sqlmap": ["sql injection", "test endpoint", "database hack"],
        "github-pr-workflow": ["create pr", "pull request", "github workflow"]
      }
    }
  }
}
```

### Rate Limiting (Optional)
```json
{
  "rateLimit": {
    "enabled": true,
    "maxRequests": 100,
    "perMinute": 10,
    "burstLimit": 20
  }
}
```

---

## 🎯 Quick Start Commands

### Start OMP Server
```bash
cd omp
npm run start
```

### Test API Connection
```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, test connection",
    "model": "gpt-4"
  }'
```

### Check Skills Status
```bash
curl http://localhost:3000/api/skills/status
```

### Reload System Prompt
```bash
curl -X POST http://localhost:3000/api/system/reload
```

---

## 🐛 Troubleshooting

### Issue 1: API Key Invalid
```bash
# Check .env file
cat .env | grep API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Issue 2: Skills Not Loading
```bash
# Check skills directory
ls -la ~/.omp/skills/

# Check permissions
chmod -R 755 ~/.omp/skills

# Restart OMP
pm2 restart omp
```

### Issue 3: System Prompt Not Loading
```bash
# Check system prompt file
cat ~/.omp/prompts/system.md | head -20

# Verify file path in config
cat config.json | grep systemPrompt

# Force reload
curl -X POST http://localhost:3000/api/system/reload
```

### Issue 4: Port Already in Use
```bash
# Check what's using port 3000
lsof -i :3000

# Kill process
kill -9 <PID>

# Or use different port
PORT=3001 npm run start
```

---

## 📊 Verification Checklist

After setup, verify:

- [ ] OMP server running on http://localhost:3000
- [ ] API keys working (test with simple request)
- [ ] System prompt loaded (check AGENTS.md content)
- [ ] Skills directory accessible (126 skills found)
- [ ] Auto-skill loading working (test with sample request)
- [ ] No errors in console logs

---

## 🔐 Security Recommendations

### 1. Protect API Keys
```bash
# Set restrictive permissions on .env
chmod 600 .env

# Never commit .env to git
echo ".env" >> .gitignore
```

### 2. Use Environment Variables in Production
```bash
# Set system-wide env vars
sudo nano /etc/environment

# Add:
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
```

### 3. Enable HTTPS (Production)
```bash
# Use nginx reverse proxy
sudo apt install nginx certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com
```

Nginx config:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

## 🚀 Production Deployment

### Using PM2
```bash
# Install PM2
npm install -g pm2

# Start OMP with PM2
pm2 start npm --name "omp" -- start

# Save PM2 config
pm2 save

# Auto-start on boot
pm2 startup

# Monitor logs
pm2 logs omp

# Restart
pm2 restart omp
```

### Using Docker
```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY . .

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

CMD ["npm", "start"]
```

```bash
# Build
docker build -t omp-enhanced .

# Run
docker run -d \
  -p 3000:3000 \
  -e OPENAI_API_KEY=sk-xxxxx \
  -e ANTHROPIC_API_KEY=sk-ant-xxxxx \
  -v ~/.omp/skills:/app/skills \
  --name omp \
  omp-enhanced
```

---

## 📞 Support

- **Repository:** https://github.com/harezadmm/omp-enhanced
- **OMP.sh Docs:** https://github.com/secretflow/omp
- **Issues:** Open GitHub issue

---

**Last Updated:** 2026-09-06  
**Version:** 2.0.0  
**Ready for Production:** ✅

