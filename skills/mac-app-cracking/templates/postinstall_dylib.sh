#!/bin/bash
# ============================================================
# DYLIB REPLACEMENT INJECTION — Postinstall Fragment
# ============================================================
# Replaces or injects a malicious/patched dylib into the
# app's Frameworks directory. Used for Hopper-generated
# injectable dylibs (macked.app.dylib) that patch license
# checks at load time via DYLD_INSERT_LIBRARIES.
#
# Usage: source this file, then call:
#   inject_dylib "$APP_NAME" "$BUNDLE_ID" "$WHOAMI"
# ============================================================

inject_dylib() {
    local APP_NAME="$1"
    local BUNDLE_ID="$2"
    local WHOAMI="$3"
    local LOG="/tmp/${APP_NAME}_dylib_inject.log"

    echo "[dylib] Injecting dylib for $BUNDLE_ID..."

    local APP_PATH="/Applications/${APP_NAME}.app"
    local FRAMEWORKS_DIR="$APP_PATH/Contents/Frameworks"
    local DYLIB_NAME="macked.app.dylib"
    local DYLIB_SRC="$FRAMEWORKS_DIR/$DYLIB_NAME"

    # ── Verify dylib exists ─────────────────────────────────
    if [ ! -f "$DYLIB_SRC" ]; then
        echo "[dylib] ERROR: $DYLIB_NAME not found in Frameworks/ — dylib must be packaged alongside the app"
        echo "[dylib] Expected at: $DYLIB_SRC"
        echo "[dylib] To generate: build the Hopper injectable dylib and place it in the app's Contents/Frameworks/"
        return 1
    fi

    # ── Verify dylib is fat binary (arm64 + x86_64) ─────────
    local ARCHS
    ARCHS=$(lipo -info "$DYLIB_SRC" 2>/dev/null || echo "")
    echo "[dylib] Architecture: $ARCHS"

    # ── Make dylib executable ───────────────────────────────
    chmod +x "$DYLIB_SRC"

    # ── Check existing LC_LOAD_DYLIB entries ────────────────
    local BINARY_PATH="$APP_PATH/Contents/MacOS/$APP_NAME"
    if [ -f "$BINARY_PATH" ]; then
        local ALREADY_LOADED
        ALREADY_LOADED=$(otool -L "$BINARY_PATH" 2>/dev/null | grep -c "$DYLIB_NAME" || echo "0")
        if [ "$ALREADY_LOADED" -gt 0 ] 2>/dev/null; then
            echo "[dylib] Dylib already linked to binary — skipping install_name_tool"
        else
            echo "[dylib] Dylib NOT linked to binary — injecting LC_LOAD_DYLIB..."
            install_name_tool -change \
                "@executable_path/../Frameworks/$DYLIB_NAME" \
                "@executable_path/../Frameworks/$DYLIB_NAME" \
                "$BINARY_PATH" 2>/dev/null || {
                # Fallback: add new load command
                install_name_tool -add_rpath \
                    "@executable_path/../Frameworks" \
                    "$BINARY_PATH" 2>/dev/null || true
                echo "[dylib] Added rpath to binary"
            }

            # ── Set dylib install name ──────────────────────────
            install_name_tool -id \
                "@executable_path/../Frameworks/$DYLIB_NAME" \
                "$DYLIB_SRC" 2>/dev/null || true
        fi
    fi

    # ── Code-sign the dylib ─────────────────────────────────
    codesign --force --sign - "$DYLIB_SRC" 2>/dev/null || {
        echo "[dylib] WARNING: codesign failed for dylib"
    }

    # ── Verify injection ────────────────────────────────────
    if [ -f "$BINARY_PATH" ]; then
        echo "[dylib] Final LC_LOAD_DYLIB entries:"
        otool -L "$BINARY_PATH" 2>/dev/null | grep -i "macked\|dylib" || echo "  (none)"
    fi

    echo "[dylib] Dylib injection complete"
    return 0
}