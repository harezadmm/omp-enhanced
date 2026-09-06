---
name: hermes-gateway-security-audit
description: Audit Hermes gateways for exposed secrets and access.
trigger: 
  - security audit of remote Hermes deployment
  - check Hermes gateway for vulnerabilities
  - scan VPS/remote bot for exposed secrets or open access
  - harden Hermes Telegram bot security
---

# Hermes Gateway Security Audit

Use when auditing or hardening a remote or local Hermes Agent gateway deployment (especially Telegram bots). Covers access policy lockdown, secret exposure, port scanning, and filesystem permission hardening.

## Audit Checklist

### 1. Access Policy Configuration
Check `~/.hermes/config.yaml`:

```yaml
gateway:
  platforms:
    telegram:
      dm_policy: open|whitelist|owner_only
      group_policy: open|disabled
```

**Vulnerability**: `dm_policy: open` + `group_policy: open` = anyone can use the bot.

**Fix**:
```bash
hermes config set gateway.platforms.telegram.dm_policy owner_only
hermes config set gateway.platforms.telegram.group_policy disabled
```

For multi-user: use `whitelist` + `allowed_users` list.

### 2. System Prompt Exposure
Profile files contain jailbreak prompts, identity instructions, and OWNER_ID lists:

```bash
ls -lah ~/.hermes/profiles/<profile>/
```

**Vulnerable permissions**: `rw-rw-r--` (664) or `rw-r--r--` (644) = other users can read.

**Critical files**:
- `system_prompt.md` / `SOUL.md` / `IDENTITY.md` — jailbreak instructions
- `config.yaml` — API keys, tokens
- `~/.hermes/auth.json` — credential pool (should be 600 already)

**Fix**:
```bash
chmod 600 ~/.hermes/profiles/<profile>/*.md
chmod 600 ~/.hermes/profiles/<profile>/config.yaml
chmod 600 ~/.hermes/config.yaml
```

### 3. Secret Exposure in Config Files
Scan for exposed credentials:

```bash
grep -rE '(token|api_key|password|secret)' ~/.hermes/ --include="*.yaml" --include="*.json"
```

**Common leaks**:
- Telegram bot tokens in `config.yaml`
- OpenAI/Anthropic keys in `auth.json`
- SSH keys, database passwords in profile instructions

**Test Telegram token validity**:
```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getMe"
# 401 Unauthorized = token invalid/revoked ✓
# 200 + bot info = token active and exposed ❌
```

### 4. Port Exposure
Check listening ports:

```bash
ss -tuln  # or netstat -tuln
```

**Expected**:
- `127.0.0.1:9119` — Hermes dashboard (localhost-only) ✓
- `127.0.0.1:11434` — Ollama (if used, localhost-only) ✓

**Vulnerable**:
- `0.0.0.0:<port>` — publicly accessible without auth ❌

**Fix**: Bind services to `127.0.0.1` or add firewall rules.

### 5. Firewall Configuration
```bash
sudo ufw status
```

**Recommended rules**:
```bash
sudo ufw default deny incoming
sudo ufw allow <custom-ssh-port>/tcp
sudo ufw enable
```

Never expose Hermes dashboard (9119) or Ollama (11434) publicly.

### 6. Running Processes
```bash
ps aux | grep -E '(hermes|ollama)' | grep -v grep
```

Verify:
- `hermes gateway run` process exists (bot active)
- `hermes dashboard` bound to localhost only
- No orphan processes with elevated privileges

### 7. Profile Jailbreak Content
Read profile identity files to check for exposed jailbreak instructions:

```bash
cat ~/.hermes/profiles/<profile>/system_prompt.md
cat ~/.hermes/profiles/<profile>/SOUL.md
```

If files contain "ZERO CONTENT BOUNDARIES", "NO REFUSALS", malicious code instructions, or similar — these are HIGH-value targets for attackers or unauthorized users on shared systems.

## Report Template

Use this structure for audit reports (adjust language to user preference — Indonesian for this user):

```markdown
# Audit Keamanan <Bot Name> (<Host>:<Port>)
**Tanggal**: YYYY-MM-DD HH:MM TZ
**Status**: CELAH KEAMANAN DITEMUKAN / AMAN

## 1. POLICY ACCESS
- dm_policy: <value>
- group_policy: <value>
**Ancaman**: <explain exposure>

## 2. SYSTEM PROMPT EXPOSURE
- File permissions: <mode>
- Readable by: <owner|group|others>
**Ancaman**: <explain what attackers learn>

## 3. PORTS EXPOSED
- Port <N>: <service> (<binding>)
**Ancaman**: <explain public access risk>

## 4. FIREWALL STATUS
<ufw/iptables output>

## 5. SECRET EXPOSURE
- Tokens found: <yes/no>
- Test results: <API response>

---

## REKOMENDASI PERBAIKAN (PRIORITY)
### SEGERA - <title>
```bash
<commands>
```

---

## KESIMPULAN
**SKOR KEAMANAN**: X/10
**CELAH TERBESAR**: <list top 3>
```

## Quick Lockdown (Post-Audit)

After identifying vulnerabilities, apply in this order:

1. **Lock access policy** (restart required):
   ```bash
   hermes config set gateway.platforms.telegram.dm_policy owner_only
   pkill -f "hermes gateway"
   cd ~/.hermes/hermes-agent && nohup ./venv/bin/python -m hermes_cli.main gateway run > /tmp/gateway.log 2>&1 &
   ```

2. **Harden filesystem**:
   ```bash
   chmod 600 ~/.hermes/profiles/*/system_prompt.md
   chmod 600 ~/.hermes/profiles/*/SOUL.md
   chmod 600 ~/.hermes/profiles/*/IDENTITY.md
   chmod 600 ~/.hermes/config.yaml
   ```

3. **Bind public ports to localhost** (service-dependent):
   - Edit service config to change `0.0.0.0:<port>` → `127.0.0.1:<port>`
   - Restart service

4. **Enable firewall** (if root access available):
   ```bash
   sudo ufw default deny incoming
   sudo ufw allow <ssh-port>/tcp
   sudo ufw enable
   ```

## Remote Audit (SSH-based)

For remote VPS deployments, wrap commands in SSH:

```bash
ssh user@host -p port "command"
# or with password (sshpass):
sshpass -p 'password' ssh -o StrictHostKeyChecking=no -p port user@host "command"
```

Run audit commands remotely, save output locally, generate report.

## Pitfalls

- **Permission denied on firewall check**: `ufw`/`iptables` require root. If audit user is non-root, note "firewall status unknown (needs root)" instead of claiming "no firewall".
- **Token test rate-limiting**: Telegram API rate-limits `getMe` calls. One test per audit, not per-file.
- **Shared VPS**: Other users on the same system can read world-readable files. Emphasize this in reports for shared hosting environments.
- **Restart requirement**: Changing `dm_policy` or `group_policy` requires gateway restart to take effect.

## Language Preference

This user expects **Indonesian-language security reports** with specific terminology:
- Vulnerability = "Celah keamanan"
- Threat/Risk = "Ancaman"
- Fix/Patch = "Perbaikan" / "Patch"
- Immediately = "Segera"
- Exposed = "Terekspos"
- Public = "Publik"

Use casual Indonesian tech slang where appropriate ("lu" for "you", "gw" for "I").
