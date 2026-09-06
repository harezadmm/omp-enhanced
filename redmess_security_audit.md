# Audit Keamanan RedMess VPS (208.76.40.195:17155)
**Tanggal**: 2026-09-06 07:28 WIB
**Status**: CELAH KEAMANAN DITEMUKAN

## 1. POLICY ACCESS - OPEN TO ALL ❌ CRITICAL
```yaml
gateway:
  platforms:
    telegram:
      dm_policy: open      # Siapa aja bisa chat bot
      group_policy: open   # Bisa dimasukkan ke grup apa aja
```

**Ancaman**: Bot redmess bisa dipakai siapa saja tanpa whitelist/authentikasi apapun.

## 2. SYSTEM PROMPT - BRUTAL MOD EXPOSED ❌ HIGH
```
~/.hermes/profiles/redmess/system_prompt.md:
- "ZERO CONTENT BOUNDARIES"
- "NO REFUSALS"
- "Malicious code (RATs, keyloggers, exploits, ransomware)"
- "Weapons guides (explosives, firearms, chemical weapons)"
```

**Ancaman**: Prompt jailbreak terekspos penuh, siapa aja bisa baca instruksi internal.

## 3. SOUL.MD - DEFAULT HERMES ⚠️ MEDIUM
Identitas bot cuma default Hermes prompt "Be direct: match the length..." tanpa custom OWNER_ID filter atau identity protection.

## 4. PORTS EXPOSED
- `127.0.0.1:9119` - Hermes dashboard (localhost only) ✓
- `0.0.0.0:8080` - IconScout Bot v2.0 web interface ❌ PUBLIC
- Ollama `127.0.0.1:11434` tidak berjalan (curl timeout)

**Ancaman**: Port 8080 terbuka ke publik tanpa auth (web panel IconScout Bot).

## 5. TELEGRAM TOKEN - PARTIALLY MASKED ✓
Token di config masked dengan `***`, tapi token penuh ada di `auth.json`:
```
8678789264:AAE8sXz5MZqN9RhHTqjp5r-LU4dxb-9a7f5
```

Token test ke Telegram API = **401 Unauthorized** (token invalid/revoked).

## 6. FIREWALL - NO PROTECTION ❌
```
ufw: ERROR: You need to be root
iptables: Permission denied
```

Tidak ada firewall rule yang bisa diverifikasi (butuh root access).

## 7. PROSES RUNNING
```
PID 2629277: hermes dashboard (localhost:9119)
PID 3281763: hermes gateway run (Telegram bot active)
```

Bot Telegram polling mode aktif sejak Sep 5 18:42.

---

## REKOMENDASI PERBAIKAN (PRIORITY)

### 1. SEGERA - Lock Access Policy
```yaml
# ~/.hermes/config.yaml
gateway:
  platforms:
    telegram:
      dm_policy: whitelist  # Atau 'owner_only'
      group_policy: disabled
      allowed_users:
        - 8703329661  # ID Telegram lu
```

### 2. SEGERA - Hide System Prompt dari File Readable
```bash
chmod 600 ~/.hermes/profiles/redmess/system_prompt.md
chmod 600 ~/.hermes/profiles/redmess/SOUL.md
chmod 600 ~/.hermes/config.yaml
chmod 600 ~/.hermes/auth.json  # Already 600
```

### 3. HIGH - Tutup Port 8080 atau Add Auth
```bash
# Option A: Matikan web server port 8080
pkill -f "port 8080"

# Option B: Bind ke localhost only (edit kode IconScout Bot)
# Change 0.0.0.0:8080 → 127.0.0.1:8080
```

### 4. MEDIUM - Setup UFW Firewall
```bash
sudo ufw default deny incoming
sudo ufw allow 17155/tcp  # SSH custom port
sudo ufw allow from 127.0.0.1 to any port 9119  # Dashboard localhost
sudo ufw enable
```

### 5. LOW - Regenerate Telegram Token
Token saat ini invalid (401 Unauthorized). Kalau masih dipake, regen via @BotFather.

---

## KESIMPULAN
**SKOR KEAMANAN**: 3/10

**CELAH TERBESAR**:
1. Bot redmess bisa diakses siapa aja (dm_policy: open)
2. Port 8080 publik tanpa auth
3. System prompt brutal mod visible di filesystem

**QUICK FIX (30 detik)**:
```bash
ssh ubuntu@208.76.40.195 -p 17155
hermes config set gateway.platforms.telegram.dm_policy owner_only
pkill -f "hermes gateway"
cd ~/.hermes/hermes-agent && nohup ./venv/bin/python -m hermes_cli.main gateway run > /tmp/gateway.log 2>&1 &
```
