# OMP Enhanced - Production Deployment Guide

Complete guide for deploying OMP Enhanced to production servers.

---

## Deployment Options

### 1. VPS / Cloud Server (Recommended)
- Ubuntu 20.04+ or Debian 11+
- 2GB+ RAM
- 10GB+ disk space
- Public IP with port 3000 open

### 2. Docker Container
- Isolated environment
- Easy scaling
- Version control

### 3. Heroku / Platform-as-a-Service
- Quick deployment
- Auto-scaling
- Managed infrastructure

---

## Option 1: VPS Deployment (Ubuntu)

### Initial Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js 18.x
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install Git
sudo apt install -y git

# Verify installations
node --version  # Should be v18.x
npm --version   # Should be v9.x
git --version
```

### Clone and Install

```bash
# Create app directory
cd /opt
sudo git clone https://github.com/harezadmm/omp-enhanced.git
sudo chown -R $USER:$USER omp-enhanced
cd omp-enhanced

# Run installer
bash install.sh

# Follow prompts:
# - Select API provider (OpenAI/Anthropic/Google)
# - Enter API key
# - Install PM2: Yes
```

### Configure PM2 for Production

```bash
cd omp

# Start with PM2
pm2 start npm --name omp-prod -- start

# Configure for production
pm2 set pm2:autodump true
pm2 set pm2:watch false

# Save configuration
pm2 save

# Enable auto-start on boot
pm2 startup systemd
# Copy and run the generated command
```

### Nginx Reverse Proxy (Optional)

```bash
# Install Nginx
sudo apt install -y nginx

# Create config
sudo nano /etc/nginx/sites-available/omp
```

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/omp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
# Test: sudo certbot renew --dry-run
```

---

## Option 2: Docker Deployment

### Create Dockerfile

```bash
cd /tmp/omp-enhanced
cat > Dockerfile << 'DOCKER'
FROM node:18-slim

# Install Git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy package
COPY . .

# Install OMP and dependencies
RUN bash -c "set -e; \
    git clone https://github.com/secretflow/omp.git; \
    cd omp; \
    npm install --production; \
    cd ..; \
    mkdir -p /root/.omp/skills /root/.omp/prompts; \
    cp -r skills/* /root/.omp/skills/; \
    cp AGENTS.md /root/.omp/prompts/system.md"

WORKDIR /app/omp

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (r) => { process.exit(r.statusCode === 200 ? 0 : 1); })"

# Start server
CMD ["npm", "start"]
DOCKER
```

### Create docker-compose.yml

```yaml
version: '3.8'

services:
  omp:
    build: .
    ports:
      - "3000:3000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_BASE_URL=${OPENAI_BASE_URL:-https://api.openai.com/v1}
      - DEFAULT_PROVIDER=${DEFAULT_PROVIDER:-openai}
      - DEFAULT_MODEL=${DEFAULT_MODEL:-gpt-4}
    volumes:
      - omp-skills:/root/.omp/skills
      - omp-prompts:/root/.omp/prompts
      - omp-cache:/root/.omp/cache
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  omp-skills:
  omp-prompts:
  omp-cache:
```

### Deploy with Docker

```bash
# Create .env file
cat > .env << ENV
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
DEFAULT_PROVIDER=openai
DEFAULT_MODEL=gpt-4
ENV

# Build and start
docker-compose up -d

# Check logs
docker-compose logs -f

# Test health
curl http://localhost:3000/health
```

---

## Option 3: Heroku Deployment

### Prerequisites

```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login
heroku login
```

### Create Heroku App

```bash
cd /tmp/omp-enhanced

# Create app
heroku create your-omp-app

# Set environment variables
heroku config:set OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
heroku config:set OPENAI_BASE_URL=https://api.openai.com/v1
heroku config:set DEFAULT_PROVIDER=openai
heroku config:set DEFAULT_MODEL=gpt-4

# Create Procfile
echo "web: cd omp && npm start" > Procfile

# Create heroku-setup.sh
cat > heroku-setup.sh << 'HEROKU'
#!/bin/bash
set -e

# Clone OMP
git clone https://github.com/secretflow/omp.git
cd omp
npm install --production
cd ..

# Deploy skills
mkdir -p /app/.omp/skills /app/.omp/prompts
cp -r skills/* /app/.omp/skills/
cp AGENTS.md /app/.omp/prompts/system.md

echo "Heroku setup complete"
HEROKU

chmod +x heroku-setup.sh

# Update Procfile to run setup
echo "web: bash heroku-setup.sh && cd omp && npm start" > Procfile

# Deploy
git add .
git commit -m "Deploy to Heroku"
git push heroku main

# Open app
heroku open
```

---

## Security Hardening

### 1. API Key Protection

```bash
# Use environment variables (never commit .env)
echo ".env" >> .gitignore

# Rotate keys regularly
# OpenAI: https://platform.openai.com/api-keys
# Anthropic: https://console.anthropic.com/

# Use read-only keys when possible
```

### 2. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 3. Rate Limiting (Nginx)

```nginx
# Add to /etc/nginx/sites-available/omp

http {
    limit_req_zone $binary_remote_addr zone=omp_limit:10m rate=10r/s;
    
    server {
        location / {
            limit_req zone=omp_limit burst=20 nodelay;
            # ... rest of config
        }
    }
}
```

### 4. Authentication (Optional)

```bash
# Install HTTP basic auth
sudo apt install -y apache2-utils

# Create password file
sudo htpasswd -c /etc/nginx/.htpasswd admin

# Update Nginx config
sudo nano /etc/nginx/sites-available/omp
```

**Add to location block:**
```nginx
location / {
    auth_basic "OMP Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    # ... rest of config
}
```

---

## Monitoring & Maintenance

### PM2 Monitoring

```bash
# Real-time monitoring
pm2 monit

# Logs
pm2 logs omp-prod

# Status
pm2 status

# Restart
pm2 restart omp-prod

# Stop
pm2 stop omp-prod
```

### Log Rotation

```bash
# Install PM2 log rotate
pm2 install pm2-logrotate

# Configure
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
pm2 set pm2-logrotate:compress true
```

### Automated Backups

```bash
# Create backup script
cat > /opt/omp-backup.sh << 'BACKUP'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"

mkdir -p $BACKUP_DIR

# Backup skills
tar -czf $BACKUP_DIR/skills_$DATE.tar.gz ~/.omp/skills

# Backup config
cp /opt/omp-enhanced/omp/config.json $BACKUP_DIR/config_$DATE.json

# Keep only last 7 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.json" -mtime +7 -delete

echo "Backup completed: $DATE"
BACKUP

chmod +x /opt/omp-backup.sh

# Schedule with cron
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/omp-backup.sh >> /var/log/omp-backup.log 2>&1") | crontab -
```

### Health Check Script

```bash
# Create health check
cat > /opt/omp-health.sh << 'HEALTH'
#!/bin/bash

# Check if OMP is running
if ! pgrep -f "node.*omp" > /dev/null; then
    echo "OMP not running, restarting..."
    cd /opt/omp-enhanced/omp
    pm2 restart omp-prod
    exit 1
fi

# Check HTTP response
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
if [ "$HTTP_CODE" != "200" ]; then
    echo "OMP not responding (HTTP $HTTP_CODE), restarting..."
    pm2 restart omp-prod
    exit 1
fi

echo "OMP healthy"
exit 0
HEALTH

chmod +x /opt/omp-health.sh

# Run every 5 minutes
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/omp-health.sh >> /var/log/omp-health.log 2>&1") | crontab -
```

---

## Performance Optimization

### 1. PM2 Cluster Mode

```bash
# Use all CPU cores
pm2 start npm --name omp-prod -i max -- start

# Or specific number of instances
pm2 start npm --name omp-prod -i 4 -- start
```

### 2. Redis Caching (Optional)

```bash
# Install Redis
sudo apt install -y redis-server

# Configure OMP to use Redis
# Add to omp/config.json:
{
  "cache": {
    "type": "redis",
    "host": "localhost",
    "port": 6379,
    "ttl": 3600
  }
}
```

### 3. CDN for Static Assets (Optional)

Use CloudFlare or similar CDN for static files to reduce server load.

---

## Updating OMP Enhanced

### Manual Update

```bash
cd /opt/omp-enhanced

# Pull latest
git pull origin main

# Redeploy skills
cp -r skills/* ~/.omp/skills/
cp AGENTS.md ~/.omp/prompts/system.md

# Update OMP (if needed)
cd omp
git pull origin main
npm install

# Restart
pm2 restart omp-prod
```

### Automated Updates (Cron)

```bash
cat > /opt/omp-update.sh << 'UPDATE'
#!/bin/bash
cd /opt/omp-enhanced

# Backup first
/opt/omp-backup.sh

# Pull updates
git pull origin main

# Update skills
cp -r skills/* ~/.omp/skills/
cp AGENTS.md ~/.omp/prompts/system.md

# Restart
pm2 restart omp-prod

echo "Update completed: $(date)"
UPDATE

chmod +x /opt/omp-update.sh

# Weekly updates (Sunday 3 AM)
(crontab -l 2>/dev/null; echo "0 3 * * 0 /opt/omp-update.sh >> /var/log/omp-update.log 2>&1") | crontab -
```

---

## Troubleshooting Production Issues

### Issue: High CPU Usage

```bash
# Check PM2 status
pm2 status

# Reduce cluster instances
pm2 scale omp-prod 2

# Check for infinite loops in logs
pm2 logs omp-prod | grep -i error
```

### Issue: Memory Leak

```bash
# Monitor memory
pm2 monit

# Configure max memory restart
pm2 start npm --name omp-prod --max-memory-restart 500M -- start
```

### Issue: API Rate Limits

```bash
# Check API usage logs
pm2 logs omp-prod | grep -i "rate limit"

# Add retry logic or upgrade API plan
# Implement exponential backoff
```

### Issue: Slow Response Times

```bash
# Enable Redis caching
sudo apt install redis-server

# Add caching to config.json
# Monitor with: redis-cli monitor

# Consider upgrading server specs
```

---

## Rollback Procedure

### Quick Rollback

```bash
cd /opt/omp-enhanced

# Stop current version
pm2 stop omp-prod

# Restore from backup
tar -xzf /opt/backups/skills_YYYYMMDD_HHMMSS.tar.gz -C ~/.omp/
cp /opt/backups/config_YYYYMMDD_HHMMSS.json omp/config.json

# Restart
pm2 restart omp-prod
```

### Git Rollback

```bash
cd /opt/omp-enhanced

# Find previous commit
git log --oneline

# Rollback to specific commit
git checkout <commit-hash>

# Redeploy
cp -r skills/* ~/.omp/skills/
pm2 restart omp-prod

# Return to latest (if rollback not needed)
git checkout main
```

---

## Support & Monitoring Services

### Recommended Tools

1. **Monitoring**: Datadog, New Relic, or PM2 Plus
2. **Logging**: Loggly, Papertrail, or ELK Stack
3. **Uptime**: UptimeRobot, Pingdom
4. **Error Tracking**: Sentry

### PM2 Plus (Free Tier)

```bash
# Register for PM2 Plus
pm2 plus

# Link server
pm2 link <secret_key> <public_key>

# Access dashboard
# https://app.pm2.io
```

---

## Production Checklist

Before going live:

- [ ] Server secured (firewall, SSH keys)
- [ ] PM2 configured with auto-restart
- [ ] Nginx reverse proxy with SSL
- [ ] Environment variables secured
- [ ] Automated backups configured
- [ ] Health checks running
- [ ] Monitoring enabled
- [ ] Log rotation configured
- [ ] Domain/DNS configured
- [ ] Load testing completed
- [ ] Rollback procedure tested

---

## Cost Estimation

### VPS (Monthly)

- **Basic** (1GB RAM): $5-10 (DigitalOcean, Linode)
- **Standard** (2GB RAM): $10-20
- **Performance** (4GB RAM): $20-40

### API Costs

- **OpenAI GPT-4**: ~$0.03-0.06/1K tokens
- **OpenAI GPT-3.5**: ~$0.002/1K tokens
- **Anthropic Claude**: ~$0.015-0.075/1K tokens

### Example Monthly Cost

- VPS: $10
- API (1M tokens/month GPT-3.5): $2
- **Total: ~$12/month**

---

## Scaling Strategies

### Vertical Scaling
- Upgrade server RAM/CPU
- Add Redis caching
- Use PM2 cluster mode

### Horizontal Scaling
- Load balancer (Nginx/HAProxy)
- Multiple OMP instances
- Shared Redis cache
- Database for persistent data

---

**Ready to deploy?**

Start with VPS deployment for production-ready setup.
