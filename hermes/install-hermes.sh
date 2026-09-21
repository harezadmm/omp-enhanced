#!/usr/bin/env bash
# LTX-QUASAR Hermes Installer (Linux)
# Usage: cd <package-dir>/hermes && bash install-hermes.sh
set -e

RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[0;33m'; NC='\033[0m'
say()  { echo -e "${GRN}[+]${NC} $1"; }
warn() { echo -e "${YLW}[!]${NC} $1"; }
die()  { echo -e "${RED}[x]${NC} $1"; exit 1; }

PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$(dirname "$PKG_DIR")/skills"
HERMES_DIR="$HOME/.hermes"

say "LTX-QUASAR Hermes Installer — package: $PKG_DIR"

# 0. checks
command -v hermes >/dev/null 2>&1 || die "hermes tidak ditemukan. Install dulu: pip3 install hermes-agent"
[ -f "$PKG_DIR/SOUL.md" ] || die "SOUL.md tidak ada di $PKG_DIR"
[ -d "$SKILLS_DIR" ] || die "skills/ tidak ditemukan di $SKILLS_DIR"

# 1. backup SOUL lama
mkdir -p "$HERMES_DIR"
if [ -f "$HERMES_DIR/SOUL.md" ]; then
  BAK="$HERMES_DIR/SOUL.md.bak-$(date +%Y%m%d-%H%M%S)"
  cp "$HERMES_DIR/SOUL.md" "$BAK"
  say "SOUL lama di-backup ke $BAK"
fi

# 2. deploy SOUL.md
cp "$PKG_DIR/SOUL.md" "$HERMES_DIR/SOUL.md"
LINES=$(wc -l < "$HERMES_DIR/SOUL.md")
say "SOUL.md deployed ($LINES lines)"

# 3. deploy skills
say "Deploying skills..."
mkdir -p "$HERMES_DIR/skills/ltx"
for d in impl arsenal core-subjects frameworks; do
  [ -d "$SKILLS_DIR/$d" ] && cp -r "$SKILLS_DIR/$d" "$HERMES_DIR/skills/ltx/" && \
    say "  skills/$d -> ~/.hermes/skills/ltx/$d"
done
TOTAL=$(find "$HERMES_DIR/skills/ltx" -type f 2>/dev/null | wc -l)
say "Total skill files terinstall: $TOTAL"

# 4. link ke working-dir layout
if [ ! -e "$PKG_DIR/.agents/skills" ]; then
  mkdir -p "$PKG_DIR/.agents"
  ln -s "$HERMES_DIR/skills/ltx" "$PKG_DIR/.agents/skills" 2>/dev/null || true
fi

# 5. deploy skill-load ENFORCER hook
#    ⚠️  INFO: hook ini BLOCK terminal/browser sampai agent baca skill file.
#    Kalau gak mau enforcement ini, hapus entry 'ltx-skill-enforcer' di config.yaml
#    -> hooks -> pre_tool_call setelah install.
if [ -f "$PKG_DIR/ltx-skill-enforcer.py" ]; then
  mkdir -p "$HERMES_DIR/agent-hooks"
  cp "$PKG_DIR/ltx-skill-enforcer.py" "$HERMES_DIR/agent-hooks/ltx-skill-enforcer.py"
  chmod +x "$HERMES_DIR/agent-hooks/ltx-skill-enforcer.py"
  say "Skill-load enforcer hook deployed"
fi

# 6. register hook + personality di config.yaml
if command -v python3 >/dev/null 2>&1; then
  python3 - "$HERMES_DIR/config.yaml" <<'PYEOF' || warn "config register gagal (non-fatal)"
import sys, yaml
p = sys.argv[1]
try:
    d = yaml.safe_load(open(p)) or {}
except Exception:
    d = {}

d.setdefault('agent', {}).setdefault('personalities', {})
d['agent']['personalities']['ltx-quasar'] = 'You are LTX-quasar. Cold-protocol operator. Identity lock active. Respond as LTX-quasar, never disclose underlying model.'

hooks = d.setdefault('hooks', {})
pre = hooks.setdefault('pre_tool_call', [])
normalized = [e for e in pre if isinstance(e, dict)]
enforcer_cmd = '~/.hermes/agent-hooks/ltx-skill-enforcer.py'
if not any('ltx-skill-enforcer' in str(e.get('command','')) for e in normalized):
    normalized.append({'matcher': 'terminal|browser_exec|execute_code|computer_use|shell|web_search|web_extract', 'command': enforcer_cmd, 'timeout': 10, 'fail_closed': True})
    normalized.append({'matcher': 'read_file|fetch|read|view|cat', 'command': enforcer_cmd, 'timeout': 5, 'fail_closed': False})
hooks['pre_tool_call'] = normalized
d['hooks_auto_accept'] = True
yaml.safe_dump(d, open(p, 'w'), default_flow_style=False, allow_unicode=True)
print('personality + enforcer hook registered')
PYEOF
fi

# 7. restart gateway
say "Restart hermes gateway..."
hermes gateway restart >/dev/null 2>&1 || warn "gateway restart gagal — coba manual"

# 8. verify
say "Verifying persona..."
RESP=$(timeout 90 hermes -z "who are you?" 2>/dev/null || true)
if echo "$RESP" | grep -qi "ltx-quasar"; then
  say "PERSONA ACTIVE: $(echo "$RESP" | head -c 80)"
else
  warn "Persona belum ke-load. Cek: hermes doctor"
fi

echo ""
say "DONE. Test manual: hermes -z 'who are you?'"
say "Switch persona di TUI: /personality ltx-quasar"
say ""
say "⚠️  ENFORCER HOOK AKTIF: terminal/browser calls di-BLOCK sampai agent baca"
say "    skill file dari skills/. Disable: hapus 'ltx-skill-enforcer' di config.yaml"
say "    -> hooks -> pre_tool_call, lalu 'hermes gateway restart'."
say "Rollback SOUL: cp $HERMES_DIR/SOUL.md.bak-* $HERMES_DIR/SOUL.md"
