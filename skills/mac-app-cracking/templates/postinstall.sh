#!/bin/bash
# ============================================================
# MAC APP — PKG POSTINSTALL TEMPLATE
# ============================================================
# Customize: APP_NAME, BUNDLE_ID, BLOCK_HOSTS, and inject method.
# ============================================================

set -e

# ─── CONFIGURE THESE ──────────────────────────────────────
APP_NAME="REPLACE_APP_NAME"
BUNDLE_ID="REPLACE_BUNDLE_ID"
WHOAMI=$(stat -f%Su /dev/console 2>/dev/null || logname 2>/dev/null || echo "$SUDO_USER")

# ─── LOG ──────────────────────────────────────────────────
LOG="/tmp/${APP_NAME}_crack_install.log"
exec > >(tee -a "$LOG") 2>&1
echo "=== ${APP_NAME} CRACK INSTALL $(date) ==="
echo "User: $WHOAMI"

# ─── LICENSE INJECTION TYPE ──────────────────────────────
# Pick ONE method below, delete the others:

# === METHOD A: RevenueCat (Pro subscription) ===
use_revenuecat() {
    su - "$WHOAMI" -c "python3 -c \"
import plistlib, json, subprocess
from pathlib import Path
from datetime import datetime

P = Path.home() / 'Library/Containers/${BUNDLE_ID}/Data/Library/Preferences/com.revenuecat.user_defaults.plist'
UID = 'REPLACE_UID'

subprocess.run(['chflags','nouchg',str(P)], capture_output=True)

info = {
    'schema_version':'3','first_seen':'2026-01-01T00:00:00Z',
    'original_app_user_id':UID,'original_source':'main',
    'entitlement_verification':1,'request_date':'2026-01-01T00:00:00Z',
    'subscriber':{
        'first_seen':'2026-01-01T00:00:00Z','management_url':None,
        'original_app_user_id':UID,
        'entitlements':{'pro':{
            'product_identifier':'REPLACE_PRODUCT_ID',
            'purchase_date':'2026-01-01T00:00:00Z',
            'original_purchase_date':'2026-01-01T00:00:00Z',
            'expires_date':'2099-01-01T00:00:00Z',
            'is_sandbox':False,'ownership_type':'PURCHASED',
            'store':'APP_STORE','is_active':True,'will_renew':True,
            'period_type':'NORMAL','latest_purchase_date':'2026-01-01T00:00:00Z',
        }},
        'subscriptions':{'REPLACE_PRODUCT_ID':{
            'product_identifier':'REPLACE_PRODUCT_ID',
            'purchase_date':'2026-01-01T00:00:00Z',
            'original_purchase_date':'2026-01-01T00:00:00Z',
            'expires_date':'2099-01-01T00:00:00Z',
            'is_sandbox':False,'ownership_type':'PURCHASED',
            'store':'APP_STORE','is_active':True,'will_renew':True,
            'period_type':'NORMAL','latest_purchase_date':'2026-01-01T00:00:00Z',
            'unsubscribe_detected_at':None,'billing_issues_detected_at':None,
        }},
        'non_subscriptions':{},
    },
}

json_bytes = json.dumps(info,ensure_ascii=False,separators=(',',':')).encode('utf-8')
data_blob = plistlib.dumps(json_bytes,fmt=plistlib.FMT_BINARY)
now = datetime(2026,1,1,0,0,0)
P.parent.mkdir(parents=True,exist_ok=True)

prefs = {
    'com.revenuecat.userdefaults.appUserID.new':UID,
    f'com.revenuecat.userdefaults.purchaserInfo.{UID}':data_blob,
    f'com.revenuecat.userdefaults.purchaserInfoLastUpdated.{UID}':now,
}

with open(P,'wb') as f: plistlib.dump(prefs,f,fmt=plistlib.FMT_BINARY)
subprocess.run(['chflags','uchg',str(P)], capture_output=True)
print('RevenueCat Pro injected (locked immutable)')
\""
}

# === METHOD B: UserDefaults ===
use_userdefaults() {
    su - "$WHOAMI" -c "
defaults write ${BUNDLE_ID} 'License.hasLicense' -bool true
defaults write ${BUNDLE_ID} 'License.type' -string 'lifetime'
defaults write ${BUNDLE_ID} 'License.expiry' -string '2099-01-01'
defaults write ${BUNDLE_ID} 'License.trialDays' -int 99999
"
}

# === METHOD C: Cache file ===
use_cache_file() {
    local CACHE_DIR="/Users/$WHOAMI/Library/Application Support/${APP_NAME}"
    su - "$WHOAMI" -c "
mkdir -p '${CACHE_DIR}'
cat > '${CACHE_DIR}/license.json' << 'EOF'
{\"hasLicense\":true,\"type\":\"lifetime\",\"expiry\":\"2099-01-01\"}
EOF
"
}

# ─── BLOCK API HOSTS ────────────────────────────────────
BLOCK_HOSTS=(
    # REPLACE: add license server hostnames
    # "api.example.com"
    # "license.example.com"
)

echo "[1/3] Blocking API servers..."
for HOST in "${BLOCK_HOSTS[@]}"; do
    if ! grep -q "0.0.0.0 $HOST" /etc/hosts 2>/dev/null; then
        echo "0.0.0.0 $HOST" >> /etc/hosts
        echo "  blocked: $HOST"
    else
        echo "  already blocked: $HOST"
    fi
done
dscacheutil -flushcache 2>/dev/null || true
killall -HUP mDNSResponder 2>/dev/null || true
echo "[1/3] Done"

# ─── INJECT LICENSE ──────────────────────────────────────
echo "[2/3] Injecting license..."

# REPLACE: call the method you chose above
# use_revenuecat
# use_userdefaults
# use_cache_file

echo "[2/3] Done"

# ─── RE-SIGN ─────────────────────────────────────────────
echo "[3/3] Re-signing..."
APP_PATH="/Applications/${APP_NAME}.app"
if [ -d "$APP_PATH" ]; then
    codesign --remove-signature "$APP_PATH" 2>/dev/null || true
    rm -rf "$APP_PATH/Contents/_CodeSignature" 2>/dev/null || true
    xattr -cr "$APP_PATH" 2>/dev/null || true
    codesign --force --deep --sign - "$APP_PATH" 2>/dev/null || true
fi
echo "[3/3] Done"
echo "=== ${APP_NAME} PRO — INSTALLED ==="