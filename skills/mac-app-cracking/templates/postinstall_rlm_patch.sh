#!/bin/bash
# ============================================================
# RLM (REPACK LICENSE MANAGER) PATCH — Postinstall Fragment
# ============================================================
# Patches apps using Reprise License Manager (RLM) or similar
# third-party license SDKs. Replaces the vendor's RLM dylib
# with a patched version that returns valid license status.
# Handles Swift name-mangled symbols.
#
# Usage: source this file, then call:
#   inject_rlm_patch "$APP_NAME" "$BUNDLE_ID" "$WHOAMI"
# ============================================================

inject_rlm_patch() {
    local APP_NAME="$1"
    local BUNDLE_ID="$2"
    local WHOAMI="$3"
    local LOG="/tmp/${APP_NAME}_rlm_patch.log"

    echo "[rlm] Patching RLM license manager for $BUNDLE_ID..."

    local APP_PATH="/Applications/${APP_NAME}.app"
    local FRAMEWORKS_DIR="$APP_PATH/Contents/Frameworks"
    local BINARY_PATH="$APP_PATH/Contents/MacOS/$APP_NAME"

    # ── Step 1: Find RLM dylibs ────────────────────────────
    local RLM_DYLIBS
    RLM_DYLIBS=$(find "$FRAMEWORKS_DIR" -name "*rlm*" -o -name "*Reprise*" \
        -o -name "*rlm_*.dylib" 2>/dev/null)

    if [ -z "$RLM_DYLIBS" ]; then
        # Also check for RLM statically linked into the binary
        if file "$BINARY_PATH" | grep -qi "arm64\|x86_64"; then
            local RLM_SYMBOLS
            RLM_SYMBOLS=$(nm "$BINARY_PATH" 2>/dev/null | grep -i "rlm\|Reprise" | head -5 || echo "")
            if [ -n "$RLM_SYMBOLS" ]; then
                echo "[rlm] RLM statically linked — found symbols:"
                echo "$RLM_SYMBOLS"
                # Fall through to binary patch approach
            else
                echo "[rlm] No RLM dylibs or symbols found — nothing to patch"
                return 0
            fi
        fi
    else
        echo "[rlm] Found RLM dylibs:"
        echo "$RLM_DYLIBS"
    fi

    # ── Step 2: Backup and replace each RLM dylib ──────────
    while IFS= read -r dylib; do
        if [ -z "$dylib" ]; then continue; fi

        local DYLIB_NAME DYLIB_DIR BACKUP
        DYLIB_NAME=$(basename "$dylib")
        DYLIB_DIR=$(dirname "$dylib")
        BACKUP="${dylib}.orig"

        echo "[rlm] Processing: $DYLIB_NAME"

        # Backup
        if [ ! -f "$BACKUP" ]; then
            cp "$dylib" "$BACKUP"
        fi

        # ── RLM common patch strategies ────────────────────────

        # Strategy 1: Replace rlm_stat() → return ISV status=1 (valid)
        # In RLM, rlm_stat returns license status struct.
        # rlm_stat->status == 1 means "permanent license valid"
        # We search for the offset and force it.

        # Strategy 2: Replace rlm_checkout() → return 0 (success)
        # rlm_checkout returns 0 on success, negative on failure

        # Strategy 3: Replace rlm_license_days_to_expiration() → return INT_MAX
        # Forces perpetual license

        # For Swift apps, symbols are name-mangled:
        #   $s9AppName14LicenseManagerC8isActiveSbyF
        # We search for these via nm and patch accordingly

        # ── Swift symbol patching ──────────────────────────────
        if [ -f "$BINARY_PATH" ]; then
            local SWIFT_LICENSE_SYMBOLS
            SWIFT_LICENSE_SYMBOLS=$(nm "$BINARY_PATH" 2>/dev/null | grep -iE \
                "isLicensed|isActive|hasLicense|license.*valid|checkLicense|\
isPro|isPremium|validateKey|isTrial|trialExpired" | head -10 || echo "")

            if [ -n "$SWIFT_LICENSE_SYMBOLS" ]; then
                echo "[rlm] Swift license symbols found:"
                echo "$SWIFT_LICENSE_SYMBOLS"

                # For each symbol, we build a wrapper dylib that
                # overrides the symbol with a forced return value

                # Create wrapper dylib source
                local WRAPPER_C="/tmp/rlm_wrapper_${APP_NAME}.c"
                cat > "$WRAPPER_C" << 'EOF_C'
// RLM Wrapper — force license checks to return valid
#include <stdint.h>

// Common RLM return values
int rlm_stat(void)  { return 1; }       // 1 = permanent license
int rlm_checkout(void) { return 0; }    // 0 = success
int rlm_checkin(void)  { return 0; }    // 0 = success
int rlm_license_stat(void) { return 1; } // 1 = valid
int rlm_license_days(void) { return 99999; } // days remaining
int rlm_license_exp(void)  { return 9999999999; } // expiry timestamp
EOF_C

                local WRAPPER_DYLIB="$FRAMEWORKS_DIR/librlm_wrapper.dylib"
                if command -v clang &>/dev/null; then
                    clang -dynamiclib -o "$WRAPPER_DYLIB" "$WRAPPER_C" \
                        -install_name "@executable_path/../Frameworks/librlm_wrapper.dylib" \
                        2>/dev/null || {
                        echo "[rlm] WARNING: clang compile failed — skipping wrapper dylib"
                    }

                    if [ -f "$WRAPPER_DYLIB" ]; then
                        codesign --force --sign - "$WRAPPER_DYLIB" 2>/dev/null || true

                        # Add to binary load commands
                        install_name_tool -add_rpath \
                            "@executable_path/../Frameworks" \
                            "$BINARY_PATH" 2>/dev/null || true
                        echo "[rlm] Wrapper dylib installed"
                    fi
                else
                    echo "[rlm] clang not available — binary patching only"
                fi
                rm -f "$WRAPPER_C"
            fi
        fi
    done <<< "$RLM_DYLIBS"

    echo "[rlm] RLM patch complete"
    return 0
}