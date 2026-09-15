#!/bin/bash
# ============================================================
# JAVASCRIPT PATCH — Postinstall Fragment (Electron/Tauri)
# ============================================================
# Patches JavaScript in Electron/Tauri apps by replacing
# license check modules in Resources/app/ with patched
# versions. For Tauri/EDiSO bundles where the binary is huge
# (>80MB) and contains no license strings — all logic is in
# the embedded JS/web bundle.
#
# Usage: source this file, then call:
#   inject_js_patch "$APP_NAME" "$BUNDLE_ID" "$WHOAMI"
# ============================================================

inject_js_patch() {
    local APP_NAME="$1"
    local BUNDLE_ID="$2"
    local WHOAMI="$3"
    local LOG="/tmp/${APP_NAME}_js_patch.log"

    echo "[js_patch] Patching JS for $BUNDLE_ID..."

    local APP_PATH="/Applications/${APP_NAME}.app"
    local RESOURCES_DIR="$APP_PATH/Contents/Resources"
    local APP_DIR="$RESOURCES_DIR/app"
    local ASAR_PATH="$RESOURCES_DIR/app.asar"

    # ── Step 1: Locate JS source ───────────────────────────
    local JS_DIR=""
    if [ -d "$APP_DIR" ]; then
        JS_DIR="$APP_DIR"
        echo "[js_patch] Found unpacked app directory: $JS_DIR"
    elif [ -f "$ASAR_PATH" ]; then
        echo "[js_patch] Found .asar archive — extracting..."
        local ASAR_EXTRACT="$RESOURCES_DIR/app.extracted"
        mkdir -p "$ASAR_EXTRACT"

        if command -v npx &>/dev/null; then
            npx asar extract "$ASAR_PATH" "$ASAR_EXTRACT" 2>/dev/null || {
                echo "[js_patch] npx asar failed — trying node..."
                node -e "require('asar').extractAll('$ASAR_PATH','$ASAR_EXTRACT')" 2>/dev/null || true
            }
        fi

        if [ -d "$ASAR_EXTRACT" ] && [ "$(ls -A "$ASAR_EXTRACT" 2>/dev/null)" ]; then
            JS_DIR="$ASAR_EXTRACT"
            echo "[js_patch] .asar extracted to $JS_DIR"
        else
            echo "[js_patch] ERROR: Failed to extract .asar"
            echo "[js_patch] Install: npm install -g @electron/asar"
            return 1
        fi
    else
        echo "[js_patch] ERROR: No app/ or app.asar found in Resources/"
        return 1
    fi

    # ── Step 2: Find license-related JS files ──────────────
    echo "[js_patch] Scanning for license check modules..."
    local LICENSE_FILES
    LICENSE_FILES=$(grep -rlE \
        "isPro|isPremium|hasLicense|licenseCheck|checkLicense|validateLicense|\
isTrial|trialExpired|purchaseStatus|subscriptionActive|activationRequired|\
requireLicense|premium.*check|pro.*check|unlock.*pro" \
        "$JS_DIR" --include="*.js" --include="*.ts" --include="*.mjs" 2>/dev/null || echo "")

    local FILE_COUNT
    FILE_COUNT=$(echo "$LICENSE_FILES" | grep -c . 2>/dev/null || echo "0")
    echo "[js_patch] Found $FILE_COUNT license-related JS files"

    # ── Step 3: Patch each file ────────────────────────────
    if [ -n "$LICENSE_FILES" ]; then
        while IFS= read -r js_file; do
            if [ -z "$js_file" ]; then continue; fi

            local BASENAME
            BASENAME=$(basename "$js_file")
            local BACKUP="${js_file}.bak"

            # Backup
            cp "$js_file" "$BACKUP" 2>/dev/null || continue

            echo "[js_patch] Patching: $BASENAME"

            # ── Common patterns to patch ────────────────────────

            # Pattern 1: Boolean returns — force true
            sed -i '' 's/return\s*\(!\)\?this\.isLicensed\b/return true/g' "$js_file" 2>/dev/null || true
            sed -i '' 's/return\s*\(!\)\?this\.isPro\b/return true/g' "$js_file" 2>/dev/null || true
            sed -i '' 's/return\s*\(!\)\?this\.isPremium\b/return true/g' "$js_file" 2>/dev/null || true
            sed -i '' 's/return\s*\(!\)\?this\.hasLicense\b/return true/g' "$js_file" 2>/dev/null || true
            sed -i '' 's/return\s*\(!\)\?this\.hasSubscription\b/return true/g' "$js_file" 2>/dev/null || true
            sed -i '' 's/return\s*\(!\)\?this\.isActivated\b/return true/g' "$js_file" 2>/dev/null || true
            sed -i '' 's/return\s*\(!\)\?this\.trialExpired\b/return false/g' "$js_file" 2>/dev/null || true
            sed -i '' 's/return\s*\(!\)\?this\.isTrialExpired\(\)/return false/g' "$js_file" 2>/dev/null || true

            # Pattern 2: License check functions — return true
            sed -i '' 's/class LicenseChecker/class LicenseChecker { isLicensed() { return true; } /g' "$js_file" 2>/dev/null || true

            # Pattern 3: Subscription status — force "active"
            sed -i '' "s/subscriptionStatus\s*=\s*['\"][^'\"]*['\"]/subscriptionStatus = 'active'/g" "$js_file" 2>/dev/null || true
            sed -i '' 's/purchaseStatus\s*=\s*['"'"'"][^'"'"'"]*['"'"'"]/purchaseStatus = '"'"'purchased'"'"'/g' "$js_file" 2>/dev/null || true

            # Pattern 4: Trial days remaining — set to max
            sed -i '' 's/trialDaysLeft\s*=\s*\d\+/trialDaysLeft = 99999/g' "$js_file" 2>/dev/null || true
            sed -i '' 's/trialDaysRemaining\s*=\s*\d\+/trialDaysRemaining = 99999/g' "$js_file" 2>/dev/null || true

            # Pattern 5: Premium/Pro state — force on
            sed -i '' 's/state\.\(isPro\|isPremium\|isLicensed\)\s*=\s*false/state.\1 = true/g' "$js_file" 2>/dev/null || true
            sed -i '' 's/store\.\(isPro\|isPremium\|isLicensed\)\s*=\s*false/store.\1 = true/g' "$js_file" 2>/dev/null || true

            echo "[js_patch]   ✓ $BASENAME patched"
        done <<< "$LICENSE_FILES"
    fi

    # ── Step 4: If using .asar, repack ────────────────────
    if [ -f "$ASAR_PATH" ] && [ -n "$ASAR_EXTRACT" ] && [ -d "$ASAR_EXTRACT" ]; then
        echo "[js_patch] Repacking .asar..."
        mv "$ASAR_PATH" "${ASAR_PATH}.orig" 2>/dev/null || true
        if command -v npx &>/dev/null; then
            npx asar pack "$ASAR_EXTRACT" "$ASAR_PATH" 2>/dev/null || {
                echo "[js_patch] WARNING: asar repack failed — using unpacked dir"
                mv "${ASAR_PATH}.orig" "$ASAR_PATH" 2>/dev/null || true
            }
        fi
    fi

    echo "[js_patch] JS patch complete — $FILE_COUNT files modified"
    return 0
}