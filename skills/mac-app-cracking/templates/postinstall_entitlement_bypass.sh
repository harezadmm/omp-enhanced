#!/bin/bash
# ============================================================
# ENTITLEMENT BYPASS — Postinstall Fragment
# ============================================================
# Strips code signing entitlements from the app binary and
# re-signs with ad-hoc signature. Removes sandbox, Hardened
# Runtime, and other restrictions that prevent debugging,
# dylib injection, and license patching.
#
# Usage: source this file, then call:
#   inject_entitlement_bypass "$APP_NAME" "$BUNDLE_ID" "$WHOAMI"
# ============================================================

inject_entitlement_bypass() {
    local APP_NAME="$1"
    local BUNDLE_ID="$2"
    local WHOAMI="$3"
    local LOG="/tmp/${APP_NAME}_entitlement_bypass.log"

    echo "[entitlement] Stripping entitlements for $BUNDLE_ID..."

    local APP_PATH="/Applications/${APP_NAME}.app"
    local BINARY_PATH="$APP_PATH/Contents/MacOS/$APP_NAME"
    local ENTITLEMENTS_PLIST="$APP_PATH/Contents/entitlements.plist"

    if [ ! -f "$BINARY_PATH" ]; then
        echo "[entitlement] ERROR: Binary not found at $BINARY_PATH"
        return 1
    fi

    # ── Step 1: Dump current entitlements ──────────────────
    echo "[entitlement] Current entitlements:"
    codesign -d --entitlements :- "$APP_PATH" 2>/dev/null || echo "  (no entitlements found)"

    # ── Step 2: Remove problematic entitlements ─────────────
    # These entitlements prevent our patches from working:
    #   com.apple.security.app-sandbox          → blocks dylib injection
    #   com.apple.security.cs.disable-library-validation → if TRUE, blocks DYLD_INSERT
    #   com.apple.security.hardened-runtime     → blocks code injection
    #   com.apple.security.get-task-allow       → needed for debugging (add it)

    echo "[entitlement] Creating minimal entitlements..."

    # ── Build minimal entitlements plist ────────────────────
    cat > "$ENTITLEMENTS_PLIST" << 'EOF_ENTITLEMENTS'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Allow debugging and code injection -->
    <key>com.apple.security.get-task-allow</key>
    <true/>

    <!-- Disable library validation (allow DYLD_INSERT_LIBRARIES) -->
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>

    <!-- Allow unsigned executable memory (JIT, dylib loading) -->
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>

    <!-- Allow DYLD environment variables -->
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>

    <!-- Network access (most apps need this) -->
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>

    <!-- File access (user-selected files) -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
</dict>
</plist>
EOF_ENTITLEMENTS

    echo "[entitlement] Minimal entitlements written to $ENTITLEMENTS_PLIST"

    # ── Step 3: Remove code signature entirely ──────────────
    echo "[entitlement] Removing existing code signature..."
    codesign --remove-signature "$APP_PATH" 2>/dev/null || true

    # Also strip from all nested binaries and dylibs
    find "$APP_PATH" -type f \( -name "*.dylib" -o -name "*.framework" -o -perm +111 \) \
        -exec codesign --remove-signature {} \; 2>/dev/null || true

    # ── Step 4: Re-sign with minimal entitlements ───────────
    echo "[entitlement] Re-signing with ad-hoc signature..."
    codesign --force --deep --sign - \
        --entitlements "$ENTITLEMENTS_PLIST" \
        --options runtime \
        "$APP_PATH" 2>/dev/null || {
        echo "[entitlement] WARNING: Initial codesign failed — trying without options..."
        codesign --force --deep --sign - \
            --entitlements "$ENTITLEMENTS_PLIST" \
            "$APP_PATH" 2>/dev/null || {
            echo "[entitlement] WARNING: All codesign attempts failed"
            echo "[entitlement] App may need Gatekeeper disable: sudo spctl --master-disable"
        }
    }

    # ── Step 5: Verify ─────────────────────────────────────
    echo "[entitlement] Final entitlements:"
    codesign -d --entitlements :- "$APP_PATH" 2>/dev/null || echo "  (verification failed — app is unsigned)"

    echo "[entitlement] Entitlement bypass complete"
    return 0
}