# LTX-QUASAR Hermes Installer (Windows PowerShell)
# Usage: cd <package-dir> ; powershell -ExecutionPolicy Bypass -File install-hermes.ps1
$ErrorActionPreference = "Stop"

function Say($m)  { Write-Host "[+] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "[!] $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "[x] $m" -ForegroundColor Red; exit 1 }

$PkgDir    = Split-Path -Parent $MyInvocation.MyCommand.Path
$HermesDir = Join-Path $env:USERPROFILE ".hermes"

Say "LTX-QUASAR Hermes Installer - package: $PkgDir"

# 0. checks
if (-not (Get-Command hermes -ErrorAction SilentlyContinue)) { Die "hermes tidak ditemukan. Install dulu: pip install hermes-agent" }
if (-not (Test-Path (Join-Path $PkgDir "SOUL.md"))) { Die "SOUL.md tidak ada - jalankan dari dalam package directory" }
if (-not (Test-Path (Join-Path $PkgDir "skills"))) { Die "skills/ tidak ada" }

# 1. backup SOUL lama
New-Item -ItemType Directory -Force -Path $HermesDir | Out-Null
$SoulDst = Join-Path $HermesDir "SOUL.md"
if (Test-Path $SoulDst) {
    $Bak = "$SoulDst.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $SoulDst $Bak
    Say "SOUL lama di-backup ke $Bak"
}

# 2. deploy SOUL.md
Copy-Item (Join-Path $PkgDir "SOUL.md") $SoulDst -Force
Say "SOUL.md deployed"

# 3. deploy skills
Say "Deploying skills..."
$LtxSkills = Join-Path $HermesDir "skills\ltx"
New-Item -ItemType Directory -Force -Path $LtxSkills | Out-Null
foreach ($d in @("impl","arsenal","core-subjects","frameworks")) {
    $src = Join-Path $PkgDir "skills\$d"
    if (Test-Path $src) {
        Copy-Item $src $LtxSkills -Recurse -Force
        Say "  skills/$d -> $LtxSkills"
    }
}
$Total = (Get-ChildItem $LtxSkills -Recurse -File | Measure-Object).Count
Say "Total skill files terinstall: $Total"

# 4. register ltx-quasar as switchable /personality (demi persona — /personality ltx-quasar di TUI)
$Cfg = Join-Path $HermesDir "config.yaml"
try {
    if (Test-Path $Cfg) {
        $cfgText = Get-Content $Cfg -Raw
        $py = @"
import sys, yaml
p = sys.argv[1]
try:
    d = yaml.safe_load(open(p)) or {}
except Exception:
    d = {}
d.setdefault('agent', {}).setdefault('personalities', {})
d['agent']['personalities']['ltx-quasar'] = 'You are LTX-quasar. Cold-protocol operator. Identity lock active. Respond as LTX-quasar, never disclose underlying model.'
yaml.safe_dump(d, open(p, 'w'), default_flow_style=False, allow_unicode=True)
print('ltx-quasar personality registered in config')
"@
        $py | Out-File -FilePath "$env:TEMP\reg_ltx.py" -Encoding utf8
        & python "$env:TEMP\reg_ltx.py" $Cfg
        Say "Personality 'ltx-quasar' registered"
    } else {
        Warn "config.yaml belum ada - jalankan 'hermes -z hi' sekali dulu, lalu ulang installer"
    }
} catch {
    Warn "Personality register gagal (non-fatal): $_"
}

# 5. restart gateway
Say "Restart hermes gateway..."
try { hermes gateway restart | Out-Null } catch { Warn "gateway restart gagal - coba manual" }

# 6. verify
Say "Verifying persona..."
$resp = ""
try { $resp = hermes -z "who are you?" 2>$null | Out-String } catch {}
if ($resp -match "ltx-quasar") {
    Say ("PERSONA ACTIVE: " + $resp.Substring(0, [Math]::Min(80, $resp.Length)))
} else {
    Warn "Persona belum ke-load. Cek: hermes doctor"
}

Write-Host ""
Say "DONE. Test manual: hermes -z 'who are you?'"
Say "Switch persona di TUI: /personality ltx-quasar"
Say "Rollback: copy SOUL.md.bak-* ke $SoulDst"
