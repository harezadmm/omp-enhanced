#!/bin/bash
# ============================================================
# TRIAL EXTENSION — Postinstall Fragment
# ============================================================
# Extends trial period by rewriting trial-start dates to 1926
# and trial-end dates to 2126 (effectively unlimited).
#
# Usage: source this file, then call:
#   extend_trial "$APP_NAME" "$BUNDLE_ID" "$WHOAMI"
# ============================================================

extend_trial() {
    local APP_NAME="$1"
    local BUNDLE_ID="$2"
    local WHOAMI="$3"
    local LOG="/tmp/${APP_NAME}_trial_extension.log"

    echo "[trial] Extending trial period for $BUNDLE_ID..."

    # ── Common trial key names (check all) ──────────────────
    local TRIAL_KEYS=(
        "trialStartDate"
        "trialEndDate"
        "trialExpiryDate"
        "TrialStart"
        "TrialEnd"
        "installDate"
        "firstLaunchDate"
        "NSFirstRunDate"
        "trial_ends_at"
        "trial_started_at"
        "licenseExpiryDate"
        "evaluationExpiry"
        "demoExpires"
        "freeTrialEnd"
        "freeTrialStart"
        "trial_date"
        "expiry_date"
        "ExpirationDate"
    )

    # ── Detect trial keys in UserDefaults ───────────────────
    local FOUND_KEYS=()
    echo "[trial] Scanning UserDefaults for trial keys..."
    for key in "${TRIAL_KEYS[@]}"; do
        if su - "$WHOAMI" -c "defaults read '$BUNDLE_ID' '$key'" 2>/dev/null; then
            FOUND_KEYS+=("$key")
            echo "[trial]   Found: $key"
        fi
    done

    # ── Also check preference plist directly ────────────────
    local PREF_PLIST="$HOME/Library/Preferences/$BUNDLE_ID.plist"
    if [ -f "$PREF_PLIST" ]; then
        echo "[trial] Scanning $PREF_PLIST for trial keys..."
        for key in "${TRIAL_KEYS[@]}"; do
            if /usr/libexec/PlistBuddy -c "Print :$key" "$PREF_PLIST" 2>/dev/null; then
                if [[ ! " ${FOUND_KEYS[*]} " =~ " $key " ]]; then
                    FOUND_KEYS+=("$key")
                    echo "[trial]   Found in plist: $key"
                fi
            fi
        done
    fi

    if [ ${#FOUND_KEYS[@]} -eq 0 ]; then
        echo "[trial] WARNING: No trial keys found for $BUNDLE_ID"
        echo "[trial] The app may not use date-based trial. Check for other license methods."
        return 1
    fi

    # ── Backup existing preferences ─────────────────────────
    if [ -f "$PREF_PLIST" ]; then
        cp "$PREF_PLIST" "$PREF_PLIST.trial_backup_$(date +%Y%m%d_%H%M%S)"
        echo "[trial] Backed up: $PREF_PLIST"
    fi

    # ── Set trial dates: start=1926, end=2126 ───────────────
    # Why 1926? Most apps check "trialEnd - trialStart > trialDuration".
    # Setting the start to 1926 means the trial has been running for
    # ~200 years — any trial duration check will pass.
    #
    # Why 2126? Far enough in the future that no one will hit it.
    # Using 9999 can break 32-bit date representations.

    local START_DATE="1926-01-01T00:00:00Z"
    local END_DATE="2126-01-01T00:00:00Z"
    local START_UNIX=-1388534400   # 1926-01-01 in Unix epoch
    local END_UNIX=4924627200      # 2126-01-01 in Unix epoch

    echo "[trial] Setting trial start → $START_DATE"
    echo "[trial] Setting trial end   → $END_DATE"

    for key in "${FOUND_KEYS[@]}"; do
        local KEY_LOWER
        KEY_LOWER=$(echo "$key" | tr '[:upper:]' '[:lower:]')

        # Determine if this is a start or end key
        if [[ "$KEY_LOWER" =~ start|install|first|launch|began ]]; then
            # Trial start key → set to 1926
            su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '$key' -date '$START_DATE'" 2>/dev/null || true
            su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '${key}_unix' -int '$START_UNIX'" 2>/dev/null || true
            echo "[trial]   $key → 1926"
        elif [[ "$KEY_LOWER" =~ end|expir|demo|free ]]; then
            # Trial end key → set to 2126
            su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '$key' -date '$END_DATE'" 2>/dev/null || true
            su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '${key}_unix' -int '$END_UNIX'" 2>/dev/null || true
            echo "[trial]   $key → 2126"
        else
            # Unknown role → set to end date (safer to extend)
            su - "$WHOAMI" -c "defaults write '$BUNDLE_ID' '$key' -date '$END_DATE'" 2>/dev/null || true
            echo "[trial]   $key → 2126 (unknown role, set to end)"
        fi
    done

    # ── Also write to plist directly for stubborn apps ──────
    if [ -f "$PREF_PLIST" ]; then
        for key in "${FOUND_KEYS[@]}"; do
            /usr/libexec/PlistBuddy -c "Delete :$key" "$PREF_PLIST" 2>/dev/null || true
            /usr/libexec/PlistBuddy -c "Add :$key date '$END_DATE'" "$PREF_PLIST" 2>/dev/null || true
        done
    fi

    # ── Handle apps that store trial in custom plist ────────
    local CUSTOM_PLISTS=(
        "$HOME/Library/Application Support/$APP_NAME/preferences.plist"
        "$HOME/Library/Application Support/$BUNDLE_ID/settings.plist"
        "$HOME/Library/Application Support/$APP_NAME/config.json"
        "$HOME/Library/Caches/$BUNDLE_ID/trial.plist"
    )

    for pl in "${CUSTOM_PLISTS[@]}"; do
        if [ -f "$pl" ]; then
            echo "[trial] Found custom plist: $pl"
            cp "$pl" "$pl.trial_backup_$(date +%Y%m%d_%H%M%S)"
            for key in "${FOUND_KEYS[@]}"; do
                /usr/libexec/PlistBuddy -c "Delete :$key" "$pl" 2>/dev/null || true
                /usr/libexec/PlistBuddy -c "Add :$key date '$END_DATE'" "$pl" 2>/dev/null || true
            done
        fi
    done

    # ── Force sync ──────────────────────────────────────────
    su - "$WHOAMI" -c "defaults read '$BUNDLE_ID'" >/dev/null 2>&1 || true
    killall cfprefsd 2>/dev/null || true

    echo "[trial] Trial extended. Start=$START_DATE, End=$END_DATE"
    echo "[trial] Keys modified: ${FOUND_KEYS[*]}"
    return 0
}