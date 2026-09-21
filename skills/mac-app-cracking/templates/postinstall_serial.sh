#!/bin/bash
# ============================================================
# SERIAL/LICENSE KEY INJECTION — Postinstall Fragment
# ============================================================
# Injects serial numbers, license keys, registration codes,
# and activation tokens into UserDefaults, plist files, and
# application support directories.
#
# Usage: source this file, then call:
#   inject_serial "$APP_NAME" "$BUNDLE_ID" "$WHOAMI" "$SERIAL" "$LICENSE_KEY"
# ============================================================

inject_serial() {
    local APP_NAME="$1"
    local BUNDLE_ID="$2"
    local WHOAMI="$3"
    local SERIAL="${4:-}"
    local LICENSE_KEY="${5:-}"
    local LOG="/tmp/${APP_NAME}_serial_injection.log"

    echo "[serial] Injecting license for $BUNDLE_ID..."

    # ── Common serial/license key names ─────────────────────
    local LICENSE_KEYS=(
        # UserDefaults-style keys
        "LicenseKey"
        "licenseKey"
        "SerialNumber"
        "serialNumber"
        "RegistrationCode"
        "registrationCode"
        "ActivationCode"
        "activationCode"
        "RegCode"
        "regCode"
        "License"
        "license"
        "Serial"
        "serial"
        "ProductKey"
        "productKey"
        "LicenseData"
        "licenseData"
        "RegisteredTo"
        "registeredTo"
        "RegisteredName"
        "registeredName"
        "RegisteredEmail"
        "registeredEmail"
        "LicenseEmail"
        "licenseEmail"
        "ActivationToken"
        "activationToken"
        "LicenseToken"
        "licenseToken"
        "key"
        "Key"
    )

    # ── Generate a fake license if none provided ────────────
    if [ -z "$SERIAL" ]; then
        SERIAL="SLF-$(uuidgen | tr '[:lower:]' '[:upper:]' | cut -c1-8)-$(date +%Y)"
        echo "[serial] Generated serial: $SERIAL"
    fi
    if [ -z "$LICENSE_KEY" ]; then
        LICENSE_KEY="LK-$(uuidgen | tr '[:lower:]' '[:upper:]')-$(date +%Y%m%d)"
        echo "[serial] Generated license key: $LICENSE_KEY"
    fi

    # ── Collect registration data ───────────────────────────
    local REG_NAME="${REG_NAME:-Licensed User}"
    local REG_EMAIL="${REG_EMAIL:-licensed@example.com}"
    local REG_ORG="${REG_ORG:-}"

    # ── Backup existing preferences ─────────────────────────
    local PREF_PLIST="$HOME/Library/Preferences/$BUNDLE_ID.plist"
    if [ -f "$PREF_PLIST" ]; then
        cp "$PREF_PLIST" "$PREF_PLIST.serial_backup_$(date +%Y%m%d_%H%M%S)"
        echo "[serial] Backed up: $PREF_PLIST"
    fi

    # ── Inject into UserDefaults ────────────────────────────
    echo "[serial] Writing to UserDefaults..."

    # Detect which keys the app actually reads
    local EXISTING_KEYS
    EXISTING_KEYS=$(su - "$WHOAMI" -c "defaults read '$BUNDLE_ID'" 2>/dev/null || echo "")

    for key in "${LICENSE_KEYS[@]}"; do
        # Determine value based on key content
        local KEY_LOWER
        KEY_LOWER=$(echo "$key" | tr '[:upper:]' '[:lower:]')

        if [[ "$KEY_LOWER" =~ serial ]]; then
            su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '$key' -string '$SERIAL'" 2>/dev/null || true
        elif [[ "$KEY_LOWER" =~ (licensekey|productkey|activationcode|regcode|key$) ]]; then
            su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '$key' -string '$LICENSE_KEY'" 2>/dev/null || true
        elif [[ "$KEY_LOWER" =~ (name|registeredto) ]]; then
            su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '$key' -string '$REG_NAME'" 2>/dev/null || true
        elif [[ "$KEY_LOWER" =~ email ]]; then
            su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '$key' -string '$REG_EMAIL'" 2>/dev/null || true
        elif [[ "$KEY_LOWER" =~ (organization|company) ]]; then
            su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '$key' -string '${REG_ORG:-$REG_NAME}'" 2>/dev/null || true
        elif [[ "$KEY_LOWER" =~ (token) ]]; then
            su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '$key' -string 'tok_$(uuidgen | tr -d '-')'" 2>/dev/null || true
        elif [[ "$KEY_LOWER" =~ (data|license$) ]]; then
            # Binary/encoded license data — write as base64
            su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '$key' -data '$(echo -n "$LICENSE_KEY" | base64)'" 2>/dev/null || true
        else
            # Generic: write as string
            su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '$key' -string '$LICENSE_KEY'" 2>/dev/null || true
        fi
    done

    # ── Write boolean flags ─────────────────────────────────
    local BOOL_FLAGS=(
        "isRegistered"
        "IsRegistered"
        "isLicensed"
        "IsLicensed"
        "hasLicense"
        "HasLicense"
        "licenseAccepted"
        "LicenseAccepted"
        "pro"
        "Pro"
        "isPro"
        "IsPro"
        "premium"
        "Premium"
        "isPremium"
        "IsPremium"
        "purchased"
        "Purchased"
        "activated"
        "Activated"
    )

    for flag in "${BOOL_FLAGS[@]}"; do
        su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '$flag' -bool true" 2>/dev/null || true
    done

    # ── Also write integer flags (some apps use 0/1) ────────
    local INT_KEYS=(
        "licenseType"
        "LicenseType"
        "plan"
        "Plan"
        "subscriptionLevel"
        "SubscriptionLevel"
        "accountType"
        "AccountType"
    )

    for key in "${INT_KEYS[@]}"; do
        su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '$key' -int 1" 2>/dev/null || true
        # Some apps want "pro" as type 2 (0=free, 1=basic, 2=pro)
        su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '${key}Max' -int 2" 2>/dev/null || true
    done

    # ── Handle custom plist files ───────────────────────────
    echo "[serial] Checking custom plist locations..."

    local CUSTOM_PLISTS=(
        "$HOME/Library/Application Support/$APP_NAME/license.plist"
        "$HOME/Library/Application Support/$APP_NAME/registration.plist"
        "$HOME/Library/Application Support/$BUNDLE_ID/license.plist"
        "$HOME/Library/Application Support/$BUNDLE_ID/settings.plist"
        "$HOME/Library/Preferences/$APP_NAME.plist"
        "$HOME/.$APP_NAME/license.plist"
        "$HOME/.config/$APP_NAME/license.json"
    )

    for pl in "${CUSTOM_PLISTS[@]}"; do
        if [ -f "$pl" ]; then
            echo "[serial]   Found: $pl"
            cp "$pl" "$pl.serial_backup_$(date +%Y%m%d_%H%M%S)"

            # Detect if binary or XML plist
            if file "$pl" | grep -q "binary"; then
                echo "[serial]   Binary plist detected — converting to XML"
                plutil -convert xml1 "$pl" 2>/dev/null || true
            fi

            # Inject values
            for key in "${LICENSE_KEYS[@]}"; do
                /usr/libexec/PlistBuddy -c "Delete :$key" "$pl" 2>/dev/null || true
                /usr/libexec/PlistBuddy -c "Add :$key string '$LICENSE_KEY'" "$pl" 2>/dev/null || true
            done

            # Set boolean flags
            /usr/libexec/PlistBuddy -c "Delete :Registered" "$pl" 2>/dev/null || true
            /usr/libexec/PlistBuddy -c "Add :Registered bool true" "$pl" 2>/dev/null || true
            /usr/libexec/PlistBuddy -c "Delete :Licensed" "$pl" 2>/dev/null || true
            /usr/libexec/PlistBuddy -c "Add :Licensed bool true" "$pl" 2>/dev/null || true
        fi
    done

    # ── Handle JSON-based license files ─────────────────────
    local JSON_FILES=(
        "$HOME/Library/Application Support/$APP_NAME/license.json"
        "$HOME/Library/Application Support/$BUNDLE_ID/license.json"
        "$HOME/.$APP_NAME/config.json"
    )

    for jf in "${JSON_FILES[@]}"; do
        if [ -f "$jf" ]; then
            echo "[serial]   Found JSON: $jf"
            cp "$jf" "$jf.serial_backup_$(date +%Y%m%d_%H%M%S)"

            # Use python for JSON manipulation (more reliable than sed)
            python3 -c "
import json, sys
with open('$jf') as f:
    data = json.load(f)
data['licenseKey'] = '$LICENSE_KEY'
data['serialNumber'] = '$SERIAL'
data['isRegistered'] = True
data['isLicensed'] = True
data['registeredTo'] = '$REG_NAME'
data['registeredEmail'] = '$REG_EMAIL'
with open('$jf', 'w') as f:
    json.dump(data, f, indent=2)
" 2>/dev/null || echo "[serial]   WARNING: JSON manipulation failed for $jf"
        fi
    done

    # ── Force sync ──────────────────────────────────────────
    su - "$WHOAMI" -c "defaults read '$BUNDLE_ID'" >/dev/null 2>&1 || true
    killall cfprefsd 2>/dev/null || true

    echo "[serial] License injected."
    echo "[serial]   Serial:      $SERIAL"
    echo "[serial]   License Key: $LICENSE_KEY"
    echo "[serial]   Registered:  $REG_NAME <$REG_EMAIL>"
    return 0
}