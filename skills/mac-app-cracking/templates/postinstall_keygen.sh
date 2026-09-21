#!/bin/bash
# ============================================================
# KEYGEN EXECUTION — Postinstall Fragment
# ============================================================
# Runs an external keygen/patcher binary found alongside the
# app, captures its output (serial, license key, activation
# code), and feeds it into the serial injector.
#
# Usage: source this file, then call:
#   inject_keygen "$APP_NAME" "$BUNDLE_ID" "$WHOAMI"
# ============================================================

inject_keygen() {
    local APP_NAME="$1"
    local BUNDLE_ID="$2"
    local WHOAMI="$3"
    local LOG="/tmp/${APP_NAME}_keygen.log"

    echo "[keygen] Running keygen for $BUNDLE_ID..."

    local KEYGEN_DIR="$(dirname "$(dirname "$(dirname "$APP_PATH")")")"
    local APP_INSTALL_DIR="$(dirname "$APP_PATH")"

    # ── Find keygen/patcher binaries ────────────────────────
    local KEYGEN_BIN=""
    local POSSIBLE_KEYGENS=(
        "$APP_INSTALL_DIR/Keygen" "$APP_INSTALL_DIR/keygen"
        "$APP_INSTALL_DIR/keygen.app/Contents/MacOS/keygen"
        "$APP_INSTALL_DIR/Patcher/patcher"
        "$APP_INSTALL_DIR/patchfiles/patch.sh"
        "$(find "$KEYGEN_DIR" -maxdepth 3 -name "Keygen*" -o -name "keygen*" -o -name "patcher*" -o -name "*.keygen" 2>/dev/null | head -1)"
    )

    for kg in "${POSSIBLE_KEYGENS[@]}"; do
        if [ -n "$kg" ] && [ -f "$kg" ] && [ -x "$kg" ]; then
            KEYGEN_BIN="$kg"
            break
        fi
    done

    # ── Also check for non-executable scripts ──────────────
    if [ -z "$KEYGEN_BIN" ]; then
        for kg in "${POSSIBLE_KEYGENS[@]}"; do
            if [ -n "$kg" ] && [ -f "$kg" ]; then
                chmod +x "$kg" 2>/dev/null || true
                KEYGEN_BIN="$kg"
                break
            fi
        done
    fi

    if [ -z "$KEYGEN_BIN" ]; then
        echo "[keygen] ERROR: No keygen binary found"
        echo "[keygen] Searched: ${POSSIBLE_KEYGENS[*]}"
        return 1
    fi

    echo "[keygen] Found keygen: $KEYGEN_BIN"

    # ── Run keygen and capture output ──────────────────────
    local KEYGEN_OUTPUT
    KEYGEN_OUTPUT=$("$KEYGEN_BIN" 2>&1) || true
    echo "[keygen] Output:"
    echo "$KEYGEN_OUTPUT" | head -20

    # ── Parse keygen output for serial/license ─────────────
    # Common keygen output formats:
    #   Serial: XXXX-XXXX-XXXX-XXXX
    #   License Key: XXXX-XXXX-XXXX
    #   Registration Code: ABCDEF123456

    local SERIAL=""
    local LICENSE_KEY=""
    local REG_NAME=""
    local REG_EMAIL=""

    # Extract serial (common patterns)
    SERIAL=$(echo "$KEYGEN_OUTPUT" | grep -oE \
        '[A-Z0-9]{4,5}-[A-Z0-9]{4,5}-[A-Z0-9]{4,5}-[A-Z0-9]{4,5}' | head -1 || echo "")
    if [ -z "$SERIAL" ]; then
        SERIAL=$(echo "$KEYGEN_OUTPUT" | grep -oE \
            '[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}' | head -1 || echo "")
    fi

    # Extract license key
    if [ -z "$LICENSE_KEY" ]; then
        LICENSE_KEY=$(echo "$KEYGEN_OUTPUT" | grep -oE \
            'License( Key)?:\s*\K[A-Z0-9-]+' | head -1 || echo "")
    fi
    if [ -z "$LICENSE_KEY" ]; then
        LICENSE_KEY=$(echo "$KEYGEN_OUTPUT" | grep -oE \
            '[A-Z0-9]{8,}-[A-Z0-9]{4,}-[A-Z0-9]{4,}-[A-Z0-9]{4,}-[A-Z0-9]{12,}' | head -1 || echo "")
    fi

    # Extract name
    REG_NAME=$(echo "$KEYGEN_OUTPUT" | grep -oE \
        'Name:\s*\K[\w ]+' | head -1 || echo "Licensed User")

    echo "[keygen] Parsed:"
    echo "[keygen]   Serial:      $SERIAL"
    echo "[keygen]   License Key: $LICENSE_KEY"
    echo "[keygen]   Name:        $REG_NAME"

    # ── Push to serial injector ────────────────────────────
    if command -v inject_serial &>/dev/null; then
        inject_serial "$APP_NAME" "$BUNDLE_ID" "$WHOAMI" \
            "${SERIAL:-KEYGEN-NO-SERIAL}" \
            "${LICENSE_KEY:-KEYGEN-NO-KEY}"
    else
        echo "[keygen] inject_serial not available — writing raw output"
        # Write directly to UserDefaults
        su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' LicenseKey '$LICENSE_KEY'" 2>/dev/null || true
        su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' SerialNumber '$SERIAL'" 2>/dev/null || true
        su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' RegistrationName '$REG_NAME'" 2>/dev/null || true
    fi

    echo "[keygen] Keygen injection complete"
    return 0
}