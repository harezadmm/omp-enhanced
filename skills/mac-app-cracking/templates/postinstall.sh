#!/bin/bash
# ============================================================
# MAC APP — PKG POSTINSTALL (AUTO-CLASSIFY + DISPATCH)
# ============================================================
# Classifies crack type from .app structure, then dispatches
# to the correct injection module automatically.
#
# Sources injection templates from the same directory.
# ============================================================
set -e

# ─── CONFIGURE THESE ──────────────────────────────────────
APP_NAME="REPLACE_APP_NAME"
BUNDLE_ID="REPLACE_BUNDLE_ID"
WHOAMI=$(stat -f%Su /dev/console 2>/dev/null || logname 2>/dev/null || echo "$SUDO_USER")
APP_PATH="/Applications/${APP_NAME}.app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ─── LOG ──────────────────────────────────────────────────
LOG="/tmp/${APP_NAME}_crack_install.log"
exec > >(tee -a "$LOG") 2>&1
echo "=== ${APP_NAME} CRACK INSTALL $(date) ==="
echo "User: $WHOAMI | Bundle: $BUNDLE_ID | Path: $APP_PATH"

# ─── SOURCE INJECTION TEMPLATES ───────────────────────────
source "$SCRIPT_DIR/postinstall_trial_extension.sh" 2>/dev/null \
    || echo "[warn] Missing template: postinstall_trial_extension.sh"
source "$SCRIPT_DIR/postinstall_serial.sh" 2>/dev/null \
    || echo "[warn] Missing template: postinstall_serial.sh"
source "$SCRIPT_DIR/postinstall_dylib.sh" 2>/dev/null \
    || echo "[warn] Missing template: postinstall_dylib.sh"
source "$SCRIPT_DIR/postinstall_hex_patch.sh" 2>/dev/null \
    || echo "[warn] Missing template: postinstall_hex_patch.sh"
source "$SCRIPT_DIR/postinstall_js_patch.sh" 2>/dev/null \
    || echo "[warn] Missing template: postinstall_js_patch.sh"
source "$SCRIPT_DIR/postinstall_keygen.sh" 2>/dev/null \
    || echo "[warn] Missing template: postinstall_keygen.sh"
source "$SCRIPT_DIR/postinstall_rlm_patch.sh" 2>/dev/null \
    || echo "[warn] Missing template: postinstall_rlm_patch.sh"
source "$SCRIPT_DIR/postinstall_entitlement_bypass.sh" 2>/dev/null \
    || echo "[warn] Missing template: postinstall_entitlement_bypass.sh"
source "$SCRIPT_DIR/postinstall_fake_framework.sh" 2>/dev/null \
    || echo "[warn] Missing template: postinstall_fake_framework.sh"
source "$SCRIPT_DIR/postinstall_plist_only.sh" 2>/dev/null \
    || echo "[warn] Missing template: postinstall_plist_only.sh"

# ============================================================
# INLINE CLASSIFIER — embeds the detection logic so the
# postinstall script can classify without depending on the
# standalone classify_crack_type.sh being in the pkg payload.
# ============================================================

BINARY_PATH="$APP_PATH/Contents/MacOS/$APP_NAME"
BINARY_SIZE=$(wc -c < "$BINARY_PATH" 2>/dev/null | tr -d ' ' || echo "0")
BINARY_SIZE_MB=$((BINARY_SIZE / 1048576))

dir_exists()  { [ -d "$APP_PATH/$1" ]; }
file_exists() { [ -f "$APP_PATH/$1" ]; }

binary_has_string() {
    [ ! -f "$BINARY_PATH" ] && return 1
    grep -aoiE "$1" "$BINARY_PATH" >/dev/null 2>&1
}

binary_string_count() {
    [ ! -f "$BINARY_PATH" ] && { echo "0"; return; }
    grep -aoiE "$1" "$BINARY_PATH" 2>/dev/null | wc -l | tr -d ' '
}

# detect_crack_type() — returns TYPE string (does NOT exit)
detect_crack_type() {
    local TNT_DIR EDISO_DIR PATCHER_DIR SK_COUNT PROT_LABEL
    local RC_BUNDLE SW_BUNDLE UD_LICENSE UD_KEYS TOOL_FILE HOST_ENTRIES
    local LICENSE_STRINGS

    # ── CHECK 1: TNT Gatekeeper ──────────────────────────
    TNT_DIR="$(dirname "$APP_PATH")"
    if [ -f "$TNT_DIR/Extra/tnt.nfo" ] || [ -f "$TNT_DIR/Extra/tnt.sfv" ]; then
        echo "TYPE: TNT_GATEKEEPER | CONFIDENCE: high | EVIDENCE: tnt.nfo/tnt.sfv found"
        return 0
    fi

    # ── CHECK 2: EDiSO StoreKit ──────────────────────────
    EDISO_DIR="$(dirname "$APP_PATH")"
    if [ -f "$EDISO_DIR/ediso.nfo" ]; then
        SK_COUNT=$(binary_string_count "SKPayment\|purchaseCompleted\|SKProduct\|addTransactionObserver" || echo "0")
        if [ "$SK_COUNT" -gt 0 ] 2>/dev/null; then
            echo "TYPE: EDISO_STOREKIT | CONFIDENCE: high | EVIDENCE: ediso.nfo + StoreKit strings"
            return 0
        fi
    fi

    # ── CHECK 3: EDiSO Binary ────────────────────────────
    if [ -f "$EDISO_DIR/ediso.nfo" ]; then
        PROT_LABEL=""
        binary_has_string "AES+ECC"           && PROT_LABEL="AES+ECC"
        binary_has_string "license.*valid"    && PROT_LABEL="$PROT_LABEL; license validation"
        binary_has_string "api.*license\|license.*api" && PROT_LABEL="$PROT_LABEL; license API"
        grep -qE "license (validation|check|server)" "$APP_PATH/Contents/Info.plist" 2>/dev/null \
            && PROT_LABEL="$PROT_LABEL; Info.plist=license"

        if [ -n "$PROT_LABEL" ]; then
            echo "TYPE: EDISO_BINARY | CONFIDENCE: high | EVIDENCE: ediso.nfo, $PROT_LABEL"
            return 0
        fi

        # ── CHECK 4: Tauri JS Patch (EDiSO + huge binary) ─
        if [ "$BINARY_SIZE_MB" -gt 80 ] 2>/dev/null; then
            LICENSE_STRINGS=$(binary_string_count "license\|License\|purchase\|Purchase\|activate\|Activate\|trial\|Trial\|premium\|Premium" || echo "0")
            if [ "$LICENSE_STRINGS" -eq 0 ] 2>/dev/null; then
                echo "TYPE: TAURI_JS_PATCH | CONFIDENCE: high | EVIDENCE: ediso.nfo, ${BINARY_SIZE_MB}MB binary, zero license strings"
                return 0
            fi
        fi
    fi

    # ── CHECK 5: Patcher + Keygen ────────────────────────
    PATCHER_DIR="$(dirname "$(dirname "$APP_PATH")")"
    if [ -d "$PATCHER_DIR/Patcher" ] || [ -d "$PATCHER_DIR/patchfiles" ]; then
        echo "TYPE: PATCHER_KEYGEN | CONFIDENCE: high | EVIDENCE: Patcher/ or patchfiles/ directory found"
        return 0
    fi

    # ── CHECK 6: Hopper Injection ────────────────────────
    if file_exists "Contents/Frameworks/macked.app.dylib"; then
        echo "TYPE: HOPPER_INJECTION | CONFIDENCE: high | EVIDENCE: macked.app.dylib found in Frameworks/"
        return 0
    fi

    # ── CHECK 7: RevenueCat ──────────────────────────────
    RC_BUNDLE=$(find "$APP_PATH" -name "RevenueCat_RevenueCat.bundle" -type d 2>/dev/null | head -1)
    if [ -n "$RC_BUNDLE" ]; then
        echo "TYPE: REVENUECAT | CONFIDENCE: high | EVIDENCE: RevenueCat_RevenueCat.bundle found"
        return 0
    fi
    SW_BUNDLE=$(find "$APP_PATH" -name "SuperwallKit*" -type d 2>/dev/null | head -1)
    if [ -n "$SW_BUNDLE" ]; then
        echo "TYPE: REVENUECAT | CONFIDENCE: medium | EVIDENCE: SuperwallKit found (treat as RevenueCat)"
        return 0
    fi

    # ── CHECK 8: UserDefaults ────────────────────────────
    if [ "$BUNDLE_ID" != "unknown" ] && [ "$BUNDLE_ID" != "REPLACE_BUNDLE_ID" ]; then
        UD_LICENSE=$(defaults read "$BUNDLE_ID" 2>/dev/null | grep -ciE "license|pro|premium|trial|purchase|subscri|register" || echo "0")
        if [ "$UD_LICENSE" -gt 0 ] 2>/dev/null; then
            echo "TYPE: USERDEFAULTS | CONFIDENCE: high | EVIDENCE: $UD_LICENSE license keys in UserDefaults"
            return 0
        fi
    fi

    # ── CHECK 9: License Server Block ────────────────────
    if grep -qE "0\.0\.0\.0.*$BUNDLE_ID|127\.0\.0\.1.*license" /etc/hosts 2>/dev/null; then
        echo "TYPE: LICENSE_SERVER_BLOCK | CONFIDENCE: high | EVIDENCE: /etc/hosts entries found"
        return 0
    fi
    if [ -f "$HOME/Library/Preferences/$BUNDLE_ID.plist" ]; then
        if ls -lO "$HOME/Library/Preferences/$BUNDLE_ID.plist" 2>/dev/null | grep -q "uchg"; then
            echo "TYPE: LICENSE_SERVER_BLOCK | CONFIDENCE: high | EVIDENCE: uchg flag on plist"
            return 0
        fi
    fi

    # ── CHECK 10: Activation Tool ────────────────────────
    TOOL_FILE=$(find "$(dirname "$APP_PATH")" -maxdepth 1 \( -name "*.tool" -o -name "*.command" \) 2>/dev/null | head -1)
    if [ -n "$TOOL_FILE" ]; then
        echo "TYPE: ACTIVATION_TOOL | CONFIDENCE: medium | EVIDENCE: $(basename "$TOOL_FILE") found"
        return 0
    fi

    # ── CHECK 11: Generic Binary Patch ───────────────────
    if [ -f "$BINARY_PATH" ]; then
        LICENSE_STRINGS=$(binary_string_count "license\|License\|activate\|Activate\|trial\|Trial\|validate\|Validate\|purchase\|Purchase\|pro\|Pro\|premium\|Premium\|register\|Register" || echo "0")
        if [ "$LICENSE_STRINGS" -gt 2 ] 2>/dev/null; then
            echo "TYPE: BINARY_PATCH | CONFIDENCE: low | EVIDENCE: $LICENSE_STRINGS license-related strings in ${BINARY_SIZE_MB}MB binary"
            return 0
        fi
    fi

    # ── FALLBACK: Unknown ────────────────────────────────
    echo "TYPE: UNKNOWN | CONFIDENCE: low | EVIDENCE: No detection fingerprint matched. Bundle: $BUNDLE_ID, Binary: ${BINARY_SIZE_MB}MB"
    return 0
}

# ============================================================
# CLASSIFY THE TARGET .app
# ============================================================
echo "=== CLASSIFYING $APP_NAME ($BUNDLE_ID) ==="
CLASSIFICATION=$(detect_crack_type)
TYPE=$(echo "$CLASSIFICATION" | grep "^TYPE:" | awk -F'|' '{print $1}' | sed 's/TYPE: *//')
CONFIDENCE=$(echo "$CLASSIFICATION" | grep "^TYPE:" | awk -F'|' '{print $2}' | sed 's/CONFIDENCE: *//')
EVIDENCE=$(echo "$CLASSIFICATION" | grep "^TYPE:" | awk -F'|' '{print $3}' | sed 's/EVIDENCE: *//')

echo "Classification: $TYPE (confidence: $CONFIDENCE)"
echo "Evidence: $EVIDENCE"

# ============================================================
# DISPATCH: Run the correct injection for this crack type
# ============================================================
echo "=== DISPATCHING: $TYPE ==="

case "$TYPE" in

    TNT_GATEKEEPER)
        echo "[dispatch] TNT Gatekeeper — trial extension + serial injection"
        command -v extend_trial >/dev/null 2>&1 \
            && extend_trial "$APP_NAME" "$BUNDLE_ID" "$WHOAMI" \
            || echo "[warn] extend_trial not available"
        command -v inject_serial >/dev/null 2>&1 \
            && inject_serial "$APP_NAME" "$BUNDLE_ID" "$WHOAMI" \
            || echo "[warn] inject_serial not available"
        ;;

    EDISO_STOREKIT)
        echo "[dispatch] EDiSO StoreKit — RevenueCat injection"
        RC_PRODUCT=$(grep -aoiE 'com\.[a-zA-Z0-9._-]*_(pro|premium)_[a-z]+' "$BINARY_PATH" 2>/dev/null \
            | head -1 || echo "")
        python3 "$SCRIPT_DIR/inject_revenuecat.py" \
            --bundle-id "$BUNDLE_ID" \
            --product-id "${RC_PRODUCT:-app_pro_yearly}" \
            || echo "[warn] RevenueCat injection failed"
        ;;

    EDISO_BINARY)
        echo "[dispatch] EDiSO Binary — serial + hex patch"
        command -v inject_serial >/dev/null 2>&1 \
            && inject_serial "$APP_NAME" "$BUNDLE_ID" "$WHOAMI" \
            || echo "[warn] inject_serial not available"
        command -v inject_hex_patch >/dev/null 2>&1 \
            && inject_hex_patch "$APP_NAME" "$BUNDLE_ID" "$WHOAMI" \
            || echo "[warn] inject_hex_patch not available"
        ;;

    TAURI_JS_PATCH)
        echo "[dispatch] Tauri/Electron — JS patch"
        command -v inject_js_patch >/dev/null 2>&1 \
            && inject_js_patch "$APP_NAME" "$BUNDLE_ID" "$WHOAMI" \
            || echo "[warn] inject_js_patch not available — STUB"
        ;;

    PATCHER_KEYGEN)
        echo "[dispatch] Patcher/Keygen — running keygen"
        command -v inject_keygen >/dev/null 2>&1 \
            && inject_keygen "$APP_NAME" "$BUNDLE_ID" "$WHOAMI" \
            || echo "[warn] inject_keygen not available — STUB"
        ;;

    HOPPER_INJECTION)
        echo "[dispatch] Hopper Injection — dylib replacement"
        command -v inject_dylib >/dev/null 2>&1 \
            && inject_dylib "$APP_NAME" "$BUNDLE_ID" "$WHOAMI" \
            || echo "[warn] inject_dylib not available — STUB"
        ;;

    REVENUECAT)
        echo "[dispatch] RevenueCat — direct injection"
        RC_PRODUCT=$(grep -aoiE 'com\.[a-zA-Z0-9._-]*_(pro|premium)_[a-z]+' "$BINARY_PATH" 2>/dev/null \
            | head -1 || echo "")
        python3 "$SCRIPT_DIR/inject_revenuecat.py" \
            --bundle-id "$BUNDLE_ID" \
            --product-id "${RC_PRODUCT:-app_pro_yearly}" \
            || echo "[warn] RevenueCat injection failed"
        ;;

    USERDEFAULTS)
        echo "[dispatch] UserDefaults — serial injection"
        command -v inject_serial >/dev/null 2>&1 \
            && inject_serial "$APP_NAME" "$BUNDLE_ID" "$WHOAMI" \
            || echo "[warn] inject_serial not available"
        ;;

    LICENSE_SERVER_BLOCK)
        echo "[dispatch] License Server Block — hosts handled below"
        # No extra injection needed; hosts are blocked in the BLOCK_HOSTS section
        ;;

    ACTIVATION_TOOL)
        echo "[dispatch] Activation Tool — hex patch + tool execution"
        command -v inject_hex_patch >/dev/null 2>&1 \
            && inject_hex_patch "$APP_NAME" "$BUNDLE_ID" "$WHOAMI" \
            || echo "[warn] inject_hex_patch not available — STUB"
        # Run any .tool/.command found alongside the app
        TOOL_FILE=$(find "$(dirname "$APP_PATH")" -maxdepth 1 \
            \( -name "*.tool" -o -name "*.command" \) 2>/dev/null | head -1)
        if [ -n "$TOOL_FILE" ] && [ -x "$TOOL_FILE" ]; then
            echo "[dispatch] Running activation tool: $(basename "$TOOL_FILE")"
            cd "$(dirname "$APP_PATH")" && "$TOOL_FILE" || true
        fi
        ;;

    BINARY_PATCH)
        echo "[dispatch] Binary Patch — hex patch"
        command -v inject_hex_patch >/dev/null 2>&1 \
            && inject_hex_patch "$APP_NAME" "$BUNDLE_ID" "$WHOAMI" \
            || echo "[warn] inject_hex_patch not available — STUB"
        ;;

    UNKNOWN|*)
        echo "[dispatch] UNKNOWN — generic fallback"
        command -v inject_serial >/dev/null 2>&1 \
            && inject_serial "$APP_NAME" "$BUNDLE_ID" "$WHOAMI" \
            || echo "[warn] inject_serial not available"
        command -v inject_plist_only >/dev/null 2>&1 \
            && inject_plist_only "$APP_NAME" "$BUNDLE_ID" "$WHOAMI" \
            || echo "[warn] inject_plist_only not available — STUB"
        command -v inject_entitlement_bypass >/dev/null 2>&1 \
            && inject_entitlement_bypass "$APP_NAME" "$BUNDLE_ID" "$WHOAMI" \
            || echo "[warn] inject_entitlement_bypass not available — STUB"
        ;;

esac

echo "[dispatch] $TYPE complete"

# ============================================================
# BLOCK LICENSE SERVER HOSTS
# ============================================================
echo "[hosts] Setting up license server blocks..."

# Dynamically populated hosts per crack type + generic defaults
# Priority: per-type known hosts > hosts found in nearby .nfo files > generic defaults
BLOCK_HOSTS=()

# Per-type known license server hosts
case "$TYPE" in
    TNT_GATEKEEPER)
        BLOCK_HOSTS+=(
            "www.teamviz.com" "www.binarynights.com"
            "www.noodlesoft.com" "www.obdev.at"
        )
        ;;
    EDISO_STOREKIT|EDISO_BINARY|TAURI_JS_PATCH|REVENUECAT)
        BLOCK_HOSTS+=(
            "api.revenuecat.com" "api.purchases.ai"
            "subscribers.revenuecat.com"
        )
        ;;
esac

# Generic defaults (always applied)
# (none — per-type hosts above cover known license servers)

# Extract hosts from ediso.nfo if present
EDISO_DIR="$(dirname "$APP_PATH")"
if [ -f "$EDISO_DIR/ediso.nfo" ]; then
    EDISO_HOSTS=$(grep -oE '[a-zA-Z0-9.-]+\.(com|net|org|io|dev|app|co|me|ai|gg|to|ly|sh|so|tk|ml|ga|cf|gq|pw|ws|eu|asia|info|biz|pro|online|store|cloud|live|tech|design|space|site|club|xyz|top|monster)\b' \
        "$EDISO_DIR/ediso.nfo" 2>/dev/null | sort -u | head -8)
    if [ -n "$EDISO_HOSTS" ]; then
        while IFS= read -r h; do
            [[ -n "$h" ]] && [[ ! " ${BLOCK_HOSTS[*]} " =~ " $h " ]] && BLOCK_HOSTS+=("$h")
        done <<< "$EDISO_HOSTS"
    fi
fi

if [ ${#BLOCK_HOSTS[@]} -gt 0 ]; then
    for HOST in "${BLOCK_HOSTS[@]}"; do
        [[ "$HOST" == "0.0.0.0" ]] && continue  # skip placeholder
        if ! grep -q "0.0.0.0 $HOST" /etc/hosts 2>/dev/null; then
            echo "0.0.0.0 $HOST" >> /etc/hosts
            echo "[hosts] Blocked: $HOST"
        else
            echo "[hosts] Already blocked: $HOST"
        fi
    done
    dscacheutil -flushcache 2>/dev/null || true
    killall -HUP mDNSResponder 2>/dev/null || true
fi

# ============================================================
# RE-SIGN — Codesign everything so the app launches
# ============================================================
echo "[codesign] Re-signing $APP_PATH..."
if [ -d "$APP_PATH" ]; then
    xattr -cr "$APP_PATH" 2>/dev/null || true
    codesign --force --deep --sign - "$APP_PATH" 2>/dev/null || {
        echo "[warn] codesign failed — app may need Gatekeeper bypass"
        echo "[warn] Run: sudo spctl --master-disable"
    }
    echo "[codesign] Done"
else
    echo "[error] $APP_PATH not found — skipping re-sign"
fi

echo "=== ${APP_NAME} PRO — INSTALLED ($TYPE) ==="
echo "Log: $LOG"
exit 0