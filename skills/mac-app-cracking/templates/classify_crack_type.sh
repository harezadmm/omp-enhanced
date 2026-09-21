#!/bin/bash
# ============================================================
# CRACK TYPE CLASSIFIER — Auto-Detect from .app Structure
# ============================================================
# Priority-ordered detection: first match wins.
# Output: TYPE: <type> | CONFIDENCE: <high/medium/low> | EVIDENCE: <indicators>
#
# Usage: bash classify_crack_type.sh /path/to/AppName.app [app_binary_name]
# ============================================================

set -euo pipefail

APP_PATH="${1:-}"
BINARY_NAME="${2:-}"

# ── Validation ─────────────────────────────────────────────
if [ -z "$APP_PATH" ] || [ ! -d "$APP_PATH" ]; then
    echo "Usage: bash classify_crack_type.sh /path/to/AppName.app [binary_name]"
    echo ""
    echo "  binary_name is optional — auto-detected from Info.plist if omitted"
    exit 1
fi

APP_NAME=$(basename "$APP_PATH" .app)

# Auto-detect binary name from Info.plist
if [ -z "$BINARY_NAME" ]; then
    BINARY_NAME=$(/usr/libexec/PlistBuddy -c "Print :CFBundleExecutable" "$APP_PATH/Contents/Info.plist" 2>/dev/null || echo "")
    if [ -z "$BINARY_NAME" ]; then
        BINARY_NAME="$APP_NAME"
    fi
fi

BINARY_PATH="$APP_PATH/Contents/MacOS/$BINARY_NAME"
BUNDLE_ID=$(/usr/libexec/PlistBuddy -c "Print :CFBundleIdentifier" "$APP_PATH/Contents/Info.plist" 2>/dev/null || echo "unknown")
BINARY_SIZE=$(wc -c < "$BINARY_PATH" 2>/dev/null | tr -d ' ' || echo "0")
BINARY_SIZE_MB=$((BINARY_SIZE / 1048576))

# ── Helper: check if directory exists in app bundle ────────
dir_exists() { [ -d "$APP_PATH/$1" ]; }
file_exists() { [ -f "$APP_PATH/$1" ]; }

# ── Helper: scan binary for strings ────────────────────────
binary_has_string() {
    if [ ! -f "$BINARY_PATH" ]; then return 1; fi
    grep -aoiE "$1" "$BINARY_PATH" >/dev/null 2>&1
}

# ── Helper: count matching strings in binary ───────────────
binary_string_count() {
    if [ ! -f "$BINARY_PATH" ]; then echo "0"; return; fi
    grep -aoiE "$1" "$BINARY_PATH" 2>/dev/null | wc -l | tr -d ' '
}

# ── OUTPUT FUNCTION ────────────────────────────────────────
classify() {
    echo "TYPE: $1 | CONFIDENCE: $2 | EVIDENCE: $3"
    exit 0
}

# ============================================================
# PRIORITY-ORDERED DETECTION CHECKS
# First match wins — order matters.
# ============================================================

# ═══════════════════════════════════════════════════════════
# CHECK 1: TNT Gatekeeper
# ═══════════════════════════════════════════════════════════
# We look at the DMG context. If this is a TNT release, the
# DMG will contain Extra/tnt.nfo. Since we're inside the .app,
# we check sibling directories of the .app for TNT markers.
#
# Detection: Extra/tnt.nfo or Extra/tnt.sfv exists next to .app
TNT_DIR="$(dirname "$APP_PATH")"
if [ -f "$TNT_DIR/Extra/tnt.nfo" ] || [ -f "$TNT_DIR/Extra/tnt.sfv" ]; then
    EVIDENCE="tnt.nfo found"
    [ -f "$TNT_DIR/Extra/tnt.nfo" ] && EVIDENCE="$EVIDENCE, tnt.sfv found"
    [ -f "$TNT_DIR/Help.txt" ] && EVIDENCE="$EVIDENCE, Help.txt found"
    classify "TNT_GATEKEEPER" "high" "$EVIDENCE"
fi

# ═══════════════════════════════════════════════════════════
# CHECK 2: EDiSO StoreKit (EDiSO nfo + StoreKit strings)
# ═══════════════════════════════════════════════════════════
EDISO_DIR="$(dirname "$APP_PATH")"
if [ -f "$EDISO_DIR/ediso.nfo" ]; then
    SK_COUNT=$(binary_string_count "SKPayment\|purchaseCompleted\|SKProduct\|addTransactionObserver" || echo "0")

    if [ "$SK_COUNT" -gt 0 ] 2>/dev/null; then
        EVIDENCE="ediso.nfo found"
        binary_has_string "purchaseCompleted" && EVIDENCE="$EVIDENCE, purchaseCompleted in binary"
        binary_has_string "SKPaymentQueue" && EVIDENCE="$EVIDENCE, SKPaymentQueue in binary"
        binary_has_string "SUFeedURL" && EVIDENCE="$EVIDENCE, SUFeedURL in Info.plist"

        # Confirmation: Sparkle feed is the tell for StoreKit
        if binary_has_string "SUFeedURL" || grep -q "SUFeedURL" "$APP_PATH/Contents/Info.plist" 2>/dev/null; then
            classify "EDISO_STOREKIT" "high" "$EVIDENCE"
        else
            classify "EDISO_STOREKIT" "medium" "$EVIDENCE"
        fi
    fi
fi

# ═══════════════════════════════════════════════════════════
# CHECK 3: EDiSO Binary (EDiSO nfo + license server, NO StoreKit)
# ═══════════════════════════════════════════════════════════
if [ -f "$EDISO_DIR/ediso.nfo" ]; then
    # Check for protection label in binary
    PROT_LABEL=""
    binary_has_string "AES+ECC" && PROT_LABEL="AES+ECC detected"
    binary_has_string "license.*valid" && PROT_LABEL="$PROT_LABEL; license validation string found"
    binary_has_string "api.*license\|license.*api" && PROT_LABEL="$PROT_LABEL; license API endpoint found"

    # Check for NSLocalNetworkUsageDescription = license validation
    grep -q "license validation\|license check\|license server" "$APP_PATH/Contents/Info.plist" 2>/dev/null \
        && PROT_LABEL="$PROT_LABEL; NSLocalNetworkUsageDescription=license"

    if [ -n "$PROT_LABEL" ]; then
        EVIDENCE="ediso.nfo found"
        [ -n "$PROT_LABEL" ] && EVIDENCE="$EVIDENCE, $PROT_LABEL"

        # Check for dmgcanvas_bg.tiff (EDiSO signature)
        [ -f "$EDISO_DIR/.background/dmgcanvas_bg.tiff" ] && EVIDENCE="$EVIDENCE, dmgcanvas_bg.tiff"

        classify "EDISO_BINARY" "high" "$EVIDENCE"
    fi

    # ═══════════════════════════════════════════════════════
    # CHECK 4: Tauri JS Patch (EDiSO nfo + huge binary, ZERO license strings)
    # ═══════════════════════════════════════════════════════
    if [ "$BINARY_SIZE_MB" -gt 80 ] 2>/dev/null; then
        LICENSE_STRINGS=$(binary_string_count "license\|License\|purchase\|Purchase\|activate\|Activate\|trial\|Trial\|premium\|Premium" || echo "0")

        if [ "$LICENSE_STRINGS" -eq 0 ] 2>/dev/null; then
            EVIDENCE="ediso.nfo found, binary=${BINARY_SIZE_MB}MB with ZERO license strings"

            # Check for Tauri indicators
            dir_exists "Contents/Resources/app" && EVIDENCE="$EVIDENCE, Resources/app/ found"
            file_exists "Contents/Resources/app.asar" && EVIDENCE="$EVIDENCE, app.asar found"

            classify "TAURI_JS_PATCH" "high" "$EVIDENCE"
        fi
    fi
fi

# ═══════════════════════════════════════════════════════════
# CHECK 5: Patcher + Keygen (appstorrent)
# ═══════════════════════════════════════════════════════════
PATCHER_DIR="$(dirname "$(dirname "$APP_PATH")")"
if [ -d "$PATCHER_DIR/Patcher" ] || [ -d "$PATCHER_DIR/patchfiles" ]; then
    EVIDENCE="Patcher/ directory found"

    [ -f "$PATCHER_DIR/Patch" ] && EVIDENCE="$EVIDENCE, Patch script found"
    [ -f "$PATCHER_DIR/keygen" ] && EVIDENCE="$EVIDENCE, keygen binary found"
    [ -d "$PATCHER_DIR/patchfiles/arm64" ] && EVIDENCE="$EVIDENCE, patchfiles/arm64/"
    [ -d "$PATCHER_DIR/patchfiles/x86_64" ] && EVIDENCE="$EVIDENCE, patchfiles/x86_64/"

    # Check for V8 JSC files
    find "$PATCHER_DIR/patchfiles" -name "*.jsc" 2>/dev/null | grep -q . && EVIDENCE="$EVIDENCE, V8 JSC files"

    classify "PATCHER_KEYGEN" "high" "$EVIDENCE"
fi

# ═══════════════════════════════════════════════════════════
# CHECK 6: Hopper Injection
# ═══════════════════════════════════════════════════════════
if file_exists "Contents/Frameworks/macked.app.dylib"; then
    EVIDENCE="macked.app.dylib found"

    # Verify it's actually Hopper's dylib
    if grep -aoiE "Cryptic Apps SARL" "$APP_PATH/Contents/Frameworks/macked.app.dylib" >/dev/null 2>&1; then
        EVIDENCE="$EVIDENCE, (c) Cryptic Apps SARL confirmed"

        dir_exists "Contents/_MASReceipt" && EVIDENCE="$EVIDENCE, _MASReceipt found"

        classify "HOPPER_INJECTION" "high" "$EVIDENCE"
    else
        EVIDENCE="$EVIDENCE, but Cryptic Apps SARL NOT found (not Hopper?)"
        classify "HOPPER_INJECTION" "medium" "$EVIDENCE"
    fi
fi

# ═══════════════════════════════════════════════════════════
# CHECK 7: RevenueCat
# ═══════════════════════════════════════════════════════════
RC_BUNDLE=$(find "$APP_PATH" -name "RevenueCat_RevenueCat.bundle" -type d 2>/dev/null | head -1)
if [ -n "$RC_BUNDLE" ]; then
    EVIDENCE="RevenueCat_RevenueCat.bundle found at $RC_BUNDLE"

    # Check for RevenueCat UserDefaults plist
    RC_PLIST="$HOME/Library/Preferences/com.revenuecat.user_defaults.plist"
    [ -f "$RC_PLIST" ] && EVIDENCE="$EVIDENCE, com.revenuecat.user_defaults.plist found"

    classify "REVENUECAT" "high" "$EVIDENCE"
fi

# Check for Superwall (RevenueCat alternative)
SW_BUNDLE=$(find "$APP_PATH" -name "SuperwallKit*" -type d 2>/dev/null | head -1)
if [ -n "$SW_BUNDLE" ]; then
    EVIDENCE="SuperwallKit found at $SW_BUNDLE"
    classify "REVENUECAT" "medium" "$EVIDENCE (Superwall — treat as RevenueCat)"
fi

# ═══════════════════════════════════════════════════════════
# CHECK 8: UserDefaults (license keys found)
# ═══════════════════════════════════════════════════════════
if [ "$BUNDLE_ID" != "unknown" ]; then
    UD_OUTPUT=$(defaults read "$BUNDLE_ID" 2>/dev/null || echo "")
    UD_LICENSE=$(echo "$UD_OUTPUT" | grep -ciE "license|pro|premium|trial|purchase|subscri|register" || echo "0")

    if [ "$UD_LICENSE" -gt 0 ] 2>/dev/null; then
        UD_KEYS=$(echo "$UD_OUTPUT" | grep -iE "license|pro|premium|trial|purchase|subscri|register" | head -5 | tr '\n' '|')
        EVIDENCE="Bundle: $BUNDLE_ID, keys: $UD_KEYS"
        classify "USERDEFAULTS" "high" "$EVIDENCE"
    fi
fi

# ═══════════════════════════════════════════════════════════
# CHECK 9: License Server Block (/etc/hosts entries)
# ═══════════════════════════════════════════════════════════
if grep -q "0.0.0.0.*$BUNDLE_ID\|127.0.0.1.*license" /etc/hosts 2>/dev/null; then
    HOST_ENTRIES=$(grep "0.0.0.0\|127.0.0.1" /etc/hosts | grep -i "license\|activate\|api" | head -3 | tr '\n' '|')
    EVIDENCE="/etc/hosts entries: $HOST_ENTRIES"
    classify "LICENSE_SERVER_BLOCK" "high" "$EVIDENCE"
fi

# Check for immutable plist flags (chflags uchg)
if [ -f "$HOME/Library/Preferences/$BUNDLE_ID.plist" ]; then
    if ls -lO "$HOME/Library/Preferences/$BUNDLE_ID.plist" 2>/dev/null | grep -q "uchg"; then
        EVIDENCE="Immutable flag (uchg) on $BUNDLE_ID.plist"
        classify "LICENSE_SERVER_BLOCK" "high" "$EVIDENCE"
    fi
fi

# ═══════════════════════════════════════════════════════════
# CHECK 10: Activation Tool (.tool/.command file)
# ═══════════════════════════════════════════════════════════
TOOL_DIR="$(dirname "$APP_PATH")"
TOOL_FILE=$(find "$TOOL_DIR" -maxdepth 1 \( -name "*.tool" -o -name "*.command" \) 2>/dev/null | head -1)
if [ -n "$TOOL_FILE" ]; then
    EVIDENCE="Activation tool: $(basename "$TOOL_FILE")"
    classify "ACTIVATION_TOOL" "medium" "$EVIDENCE"
fi

# ═══════════════════════════════════════════════════════════
# CHECK 11: Generic Binary Patch (fallback)
# ═══════════════════════════════════════════════════════════
if [ -f "$BINARY_PATH" ]; then
    LICENSE_STRINGS=$(binary_string_count "license\|License\|activate\|Activate\|trial\|Trial\|validate\|Validate\|purchase\|Purchase\|pro\|Pro\|premium\|Premium\|register\|Register" || echo "0")

    if [ "$LICENSE_STRINGS" -gt 2 ] 2>/dev/null; then
        EVIDENCE="Binary has $LICENSE_STRINGS license-related strings (${BINARY_SIZE_MB}MB), no scene markers detected"
        classify "BINARY_PATCH" "low" "$EVIDENCE"
    fi
fi

# ═══════════════════════════════════════════════════════════
# FALLBACK: Unknown
# ═══════════════════════════════════════════════════════════
classify "UNKNOWN" "low" "No detection fingerprint matched. Bundle: $BUNDLE_ID, Binary: ${BINARY_SIZE_MB}MB"