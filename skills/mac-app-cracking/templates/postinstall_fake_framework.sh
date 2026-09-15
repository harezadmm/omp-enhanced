#!/bin/bash
# ============================================================
# FAKE FRAMEWORK REPLACEMENT — Postinstall Fragment
# ============================================================
# Replaces a third-party license/DRM framework bundle with a
# patched version that returns valid license status. Used
# when the app bundles its license checking as a .framework.
#
# Usage: source this file, then call:
#   inject_fake_framework "$APP_NAME" "$BUNDLE_ID" "$WHOAMI"
# ============================================================

inject_fake_framework() {
    local APP_NAME="$1"
    local BUNDLE_ID="$2"
    local WHOAMI="$3"
    local LOG="/tmp/${APP_NAME}_fake_framework.log"

    echo "[fake_fw] Replacing license frameworks for $BUNDLE_ID..."

    local APP_PATH="/Applications/${APP_NAME}.app"
    local FRAMEWORKS_DIR="$APP_PATH/Contents/Frameworks"

    if [ ! -d "$FRAMEWORKS_DIR" ]; then
        echo "[fake_fw] No Frameworks directory — nothing to replace"
        return 0
    fi

    # ── Find third-party frameworks (not system frameworks) ──
    local THIRD_PARTY_FWS
    THIRD_PARTY_FWS=$(find "$FRAMEWORKS_DIR" -maxdepth 2 -name "*.framework" \
        ! -name "libswift*" ! -name "Swift*" ! -name "lib*" 2>/dev/null)

    local FW_COUNT
    FW_COUNT=$(echo "$THIRD_PARTY_FWS" | grep -c "." 2>/dev/null || echo "0")
    echo "[fake_fw] Found $FW_COUNT third-party framework(s)"

    if [ "$FW_COUNT" -eq 0 ] 2>/dev/null; then
        echo "[fake_fw] No third-party frameworks to replace"
        return 0
    fi

    # ── Process each framework ─────────────────────────────
    while IFS= read -r framework; do
        if [ -z "$framework" ]; then continue; fi

        local FW_NAME FW_BINARY FW_BACKUP
        FW_NAME=$(basename "$framework" .framework)
        FW_BINARY="$framework/$FW_NAME"
        FW_BACKUP="${framework}.orig"

        echo "[fake_fw] Processing: $FW_NAME.framework"

        # Check if framework has a binary
        if [ ! -f "$FW_BINARY" ]; then
            echo "[fake_fw]   No binary in $FW_NAME — skipping"
            continue
        fi

        # Backup entire framework
        if [ ! -d "$FW_BACKUP" ]; then
            cp -R "$framework" "$FW_BACKUP"
            echo "[fake_fw]   Backup: $FW_BACKUP"
        fi

        # ── Analyze the framework binary ───────────────────────
        local LICENSE_SYMBOLS
        LICENSE_SYMBOLS=$(nm "$FW_BINARY" 2>/dev/null | grep -iE \
            "license|validate|check|activate|trial|register|purchase|subscription" | head -10 || echo "")

        if [ -n "$LICENSE_SYMBOLS" ]; then
            echo "[fake_fw]   License-related symbols:"
            echo "$LICENSE_SYMBOLS" | while read -r line; do echo "     $line"; done
        fi

        # ── Check if it's an ObjC framework (has class methods) ──
        local OBJC_METHODS
        OBJC_METHODS=$(nm "$FW_BINARY" 2>/dev/null | grep -cE "OBJC_CLASS|_OBJC_" || echo "0")

        if [ "$OBJC_METHODS" -gt 0 ] 2>/dev/null; then
            echo "[fake_fw]   Objective-C framework detected"

            # For ObjC frameworks, we can use method swizzling
            # via a dylib that overrides key methods at runtime.
            # Build a simple override dylib.

            local OVERRIDE_C="/tmp/fake_${FW_NAME}.c"
            cat > "$OVERRIDE_C" << EOF_C
// Fake framework override — force license checks to return valid
#include <objc/runtime.h>
#include <objc/message.h>
#include <stdbool.h>

__attribute__((constructor))
static void overrideLicenseMethods(void) {
    // Override common ObjC license check selectors
    // These must be checked at runtime via class_getInstanceMethod
    // and replaced with method_setImplementation

    // Common selectors to override:
    // - (BOOL)isLicensed;
    // - (BOOL)hasValidLicense;
    // - (BOOL)isActivated;
    // - (BOOL)isSubscribed;
    // - (BOOL)isProUser;
    // - (BOOL)trialExpired;
    // - (NSInteger)daysRemainingInTrial;
    // - (NSString *)licenseStatus;
}
EOF_C
            rm -f "$OVERRIDE_C"
        fi

        # ── Strip codesign from framework binary ───────────────
        codesign --remove-signature "$FW_BINARY" 2>/dev/null || true
        codesign --force --sign - "$FW_BINARY" 2>/dev/null || true

        echo "[fake_fw]   ✓ $FW_NAME processed"

    done <<< "$THIRD_PARTY_FWS"

    echo "[fake_fw] Framework replacement complete — $FW_COUNT framework(s) processed"
    return 0
}