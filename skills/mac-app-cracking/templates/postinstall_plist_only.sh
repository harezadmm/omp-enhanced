#!/bin/bash
# ============================================================
# PLIST-ONLY MODIFICATION — Postinstall Fragment
# ============================================================
# Modifies the app's Info.plist and related plist files to
# bypass license checks without touching the binary. Used
# for apps where license state is read from plist keys like
# "IsPro", "LicenseStatus", "TrialStartDate", etc.
#
# Usage: source this file, then call:
#   inject_plist_only "$APP_NAME" "$BUNDLE_ID" "$WHOAMI"
# ============================================================

inject_plist_only() {
    local APP_NAME="$1"
    local BUNDLE_ID="$2"
    local WHOAMI="$3"
    local LOG="/tmp/${APP_NAME}_plist_only.log"

    echo "[plist] Modifying plist files for $BUNDLE_ID..."

    local APP_PATH="/Applications/${APP_NAME}.app"
    local INFO_PLIST="$APP_PATH/Contents/Info.plist"

    # ── Step 1: Backup Info.plist ──────────────────────────
    if [ -f "$INFO_PLIST" ]; then
        local BACKUP="${INFO_PLIST}.orig"
        if [ ! -f "$BACKUP" ]; then
            cp "$INFO_PLIST" "$BACKUP"
            echo "[plist] Backup: $BACKUP"
        fi
    else
        echo "[plist] ERROR: No Info.plist found at $INFO_PLIST"
        return 1
    fi

    # ── Step 2: Read current plist for diagnosis ───────────
    echo "[plist] Current license-related keys in Info.plist:"
    /usr/libexec/PlistBuddy -c "Print" "$INFO_PLIST" 2>/dev/null | grep -iE \
        "license|pro|premium|trial|purchase|subscri|register|activate|unlock" || \
        echo "  (none found — will inject)"

    # ── Step 3: Add/Modify common license bypass keys ───────
    # Using PlistBuddy for XML plist editing
    # /usr/libexec/PlistBuddy is available on all macOS versions

    local PLIST_KEYS=(
        # Key                        Type    Value
        "IsPro:bool:true"
        "IsPremium:bool:true"
        "IsLicensed:bool:true"
        "IsRegistered:bool:true"
        "IsActivated:bool:true"
        "HasValidLicense:bool:true"
        "HasSubscription:bool:true"
        "ProUnlocked:bool:true"
        "PremiumUnlocked:bool:true"
        "LicenseStatus:string:active"
        "SubscriptionStatus:string:active"
        "PurchaseStatus:string:purchased"
        "TrialStatus:string:expired"
        "TrialStartDate:date:1926-01-01T00:00:00Z"
        "TrialEndDate:date:2126-01-01T00:00:00Z"
        "LicenseExpiryDate:date:2126-01-01T00:00:00Z"
        "RegistrationDate:date:1926-01-01T00:00:00Z"
        "TrialDaysRemaining:integer:99999"
        "LicenseType:string:pro"
        "AccountType:string:pro"
        "PlanType:string:lifetime"
        "SKProduct:string:lifetime_pro"
        "PurchasedProductIDs:array:com.app.pro.lifetime"
    )

    echo "[plist] Injecting bypass keys into Info.plist..."

    for entry in "${PLIST_KEYS[@]}"; do
        IFS=':' read -r KEY TYPE VALUE <<< "$entry"

        # Check if key already exists — skip if so
        if /usr/libexec/PlistBuddy -c "Print :$KEY" "$INFO_PLIST" &>/dev/null; then
            # Key exists — update it
            case "$TYPE" in
                bool)
                    [[ "$VALUE" == "true" ]] && /usr/libexec/PlistBuddy -c "Set :$KEY true" "$INFO_PLIST" 2>/dev/null
                    [[ "$VALUE" == "false" ]] && /usr/libexec/PlistBuddy -c "Set :$KEY false" "$INFO_PLIST" 2>/dev/null
                    ;;
                string)
                    /usr/libexec/PlistBuddy -c "Set :$KEY $VALUE" "$INFO_PLIST" 2>/dev/null
                    ;;
                integer)
                    /usr/libexec/PlistBuddy -c "Set :$KEY $VALUE" "$INFO_PLIST" 2>/dev/null
                    ;;
                date)
                    /usr/libexec/PlistBuddy -c "Set :$KEY $VALUE" "$INFO_PLIST" 2>/dev/null
                    ;;
            esac
        else
            # Key doesn't exist — add it
            case "$TYPE" in
                bool)
                    [[ "$VALUE" == "true" ]] && /usr/libexec/PlistBuddy -c "Add :$KEY bool true" "$INFO_PLIST" 2>/dev/null
                    [[ "$VALUE" == "false" ]] && /usr/libexec/PlistBuddy -c "Add :$KEY bool false" "$INFO_PLIST" 2>/dev/null
                    ;;
                string)
                    /usr/libexec/PlistBuddy -c "Add :$KEY string $VALUE" "$INFO_PLIST" 2>/dev/null
                    ;;
                integer)
                    /usr/libexec/PlistBuddy -c "Add :$KEY integer $VALUE" "$INFO_PLIST" 2>/dev/null
                    ;;
                date)
                    /usr/libexec/PlistBuddy -c "Add :$KEY date $VALUE" "$INFO_PLIST" 2>/dev/null
                    ;;
                array)
                    /usr/libexec/PlistBuddy -c "Add :$KEY array" "$INFO_PLIST" 2>/dev/null
                    /usr/libexec/PlistBuddy -c "Add :$KEY:0 string $VALUE" "$INFO_PLIST" 2>/dev/null
                    ;;
            esac
        fi
    done

    # ── Step 4: Also check companion plists ────────────────
    local COMPANION_PLISTS=(
        "$APP_PATH/Contents/Resources/License.plist"
        "$APP_PATH/Contents/Resources/license.plist"
        "$APP_PATH/Contents/Resources/Settings.plist"
        "$APP_PATH/Contents/Resources/Config.plist"
    )

    for cp in "${COMPANION_PLISTS[@]}"; do
        if [ -f "$cp" ]; then
            echo "[plist] Found companion plist: $(basename "$cp")"
            # Apply same bypass keys
            for entry in "${PLIST_KEYS[@]}"; do
                IFS=':' read -r KEY TYPE VALUE <<< "$entry"
                if ! /usr/libexec/PlistBuddy -c "Print :$KEY" "$cp" &>/dev/null; then
                    case "$TYPE" in
                        bool) [[ "$VALUE" == "true" ]] && /usr/libexec/PlistBuddy -c "Add :$KEY bool true" "$cp" 2>/dev/null ;;
                        string) /usr/libexec/PlistBuddy -c "Add :$KEY string $VALUE" "$cp" 2>/dev/null ;;
                        integer) /usr/libexec/PlistBuddy -c "Add :$KEY integer $VALUE" "$cp" 2>/dev/null ;;
                    esac
                fi
            done
        fi
    done

    # ── Step 5: Verify ─────────────────────────────────────
    echo "[plist] Verifying Info.plist modifications..."
    for entry in "${PLIST_KEYS[@]}"; do
        IFS=':' read -r KEY TYPE VALUE <<< "$entry"
        local ACTUAL
        ACTUAL=$(/usr/libexec/PlistBuddy -c "Print :$KEY" "$INFO_PLIST" 2>/dev/null || echo "MISSING")
        if [ "$ACTUAL" = "MISSING" ]; then
            echo "[plist]   ✗ $KEY = $ACTUAL"
        else
            echo "[plist]   ✓ $KEY = $ACTUAL"
        fi
    done

    echo "[plist] Plist modification complete — ${#PLIST_KEYS[@]} keys processed"
    return 0
}