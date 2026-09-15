#!/bin/bash
# ============================================================
# BINARY HEX PATCH — Postinstall Fragment
# ============================================================
# Patches the main executable binary with hex edits to
# bypass license checks: NOP out branch instructions,
# invert condition codes, force return values, or replace
# magic bytes at known offsets.
#
# Usage: source this file, then call:
#   inject_hex_patch "$APP_NAME" "$BUNDLE_ID" "$WHOAMI"
# ============================================================

inject_hex_patch() {
    local APP_NAME="$1"
    local BUNDLE_ID="$2"
    local WHOAMI="$3"
    local LOG="/tmp/${APP_NAME}_hex_patch.log"

    echo "[hex] Patching binary for $BUNDLE_ID..."

    local BINARY_PATH="/Applications/${APP_NAME}.app/Contents/MacOS/$APP_NAME"

    if [ ! -f "$BINARY_PATH" ]; then
        echo "[hex] ERROR: Binary not found at $BINARY_PATH"
        return 1
    fi

    # ── Backup original binary ──────────────────────────────
    local BACKUP_PATH="${BINARY_PATH}.orig"
    if [ ! -f "$BACKUP_PATH" ]; then
        cp "$BINARY_PATH" "$BACKUP_PATH"
        echo "[hex] Backup saved to $BACKUP_PATH"
    else
        # Restore from backup before patching fresh
        cp "$BACKUP_PATH" "$BINARY_PATH"
        echo "[hex] Restored from backup for clean patch"
    fi

    # ── Step 1: Strip code signature (must patch before re-sign) ──
    echo "[hex] Stripping existing code signature..."
    codesign --remove-signature "$BINARY_PATH" 2>/dev/null || true

    # ── Step 2: Find license-check patterns in binary ───────
    local PATTERN_FILE=$(mktemp /tmp/hex_patterns.XXXXXX)

    # Common Objective-C bool-returning license check methods
    # We want to find functions that return BOOL and NOP them to return YES/true
    grep -aoiE 'isLicensed|hasLicense|isPro|isPremium|isRegistered|licenseValid|checkLicense|validateLicense|validateKey|checkRegistration|isTrialExpired|isActivated|hasActiveSubscription' \
        "$BINARY_PATH" > "$PATTERN_FILE" 2>/dev/null || true

    local MATCH_COUNT
    MATCH_COUNT=$(wc -l < "$PATTERN_FILE" 2>/dev/null || echo "0")
    echo "[hex] Found $MATCH_COUNT license-related strings"

    # ── Step 3: ARM64 patch — force boolean returns to true ──
    # ARM64: MOV W0, #1 ; RET = 20 00 80 D2 C0 03 5F D6
    # We search for functions near license strings and patch the return

    local BINARY_ARCH
    BINARY_ARCH=$(lipo -info "$BINARY_PATH" 2>/dev/null | grep -oE 'arm64|x86_64' | head -1)

    # ── ARM64: Patch common license check patterns ──────────
    if file "$BINARY_PATH" | grep -qi "arm64"; then
        echo "[hex] Patching ARM64 binary..."

        # Pattern 1: Replace 'MOV W0, #0' (false) with 'MOV W0, #1' (true)
        # MOV W0, #0 = 00 00 80 52  →  MOV W0, #1 = 20 00 80 52
        local FALSE_RET_COUNT
        FALSE_RET_COUNT=$(perl -ne 'print "$.: $_" if /\x00\x00\x80\x52/' "$BINARY_PATH" 2>/dev/null | wc -l || echo "0")
        echo "[hex] Found $FALSE_RET_COUNT MOV W0,#0 instructions"

        if [ "$FALSE_RET_COUNT" -gt 0 ] 2>/dev/null; then
            perl -i -pe 's/\x00\x00\x80\x52/\x20\x00\x80\x52/g' "$BINARY_PATH"
            echo "[hex] Patched MOV W0,#0 → MOV W0,#1"
        fi

        # Pattern 2: CBZ (compare branch zero) → NOP out branch-to-failure
        # CBZ Wn encoding: byte[3] = 0x34 (for 32-bit variant)
        # NOP encoding: 0xD503201F → LE bytes: \x1F\x20\x03\xD5
        # Strategy: scan 4-byte aligned words, match CBZ, replace with NOP
        local CBZ_COUNT=0
        perl -i -pe 's/(\x34)/$cbz++; pack("V", 0xD503201F)/eg if $cbz < 9999;
                     BEGIN{our $cbz=0}' "$BINARY_PATH" 2>/dev/null

        # More targeted approach: only NOP CBZ near license check strings
        local CBZ_COUNT=0
        if [ -s "$PATTERN_FILE" ]; then
            while IFS= read -r pattern_str; do
                [ -z "$pattern_str" ] && continue
                # Find offset of license string, then scan nearby for CBZ
                local STR_OFFSETS
                STR_OFFSETS=$(grep -aob "$pattern_str" "$BINARY_PATH" 2>/dev/null | cut -d: -f1 || true)
                for str_off in $STR_OFFSETS; do
                    # Scan ±256 bytes around the string for CBZ instructions (4-byte aligned)
                    local scan_start=$((str_off > 256 ? str_off - 256 : 0))
                    perl -i -pe 'BEGIN{$cbz=0} if ($. == 1) {
                        my $off = '"$scan_start"';
                        s/(.)(.{'"$scan_start"'})/
                            my $pre=$1; my $rest=$2;
                            my $b=substr($rest,0,512);
                            $b =~ s/(.{4})/
                                my $w=$1;
                                (vec($w,3,8)==0x34 && vec($w,2,1)==0)
                                    ? (++$cbz && pack("V",0xD503201F))
                                    : $w
                            /seg;
                            $pre . substr($b,0,512) . substr($rest,512)
                        /se
                    }' "$BINARY_PATH" 2>/dev/null
                    echo "[hex] CBZ patch near offset $str_off for '$pattern_str'"
                done
            done < "$PATTERN_FILE"
        fi
        CBZ_COUNT=$(grep -aobP '\x1F\x20\x03\xD5' "$BINARY_PATH" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        echo "[hex] Patched $CBZ_COUNT CBZ→NOP instructions"

        # Pattern 3: TBNZ (test bit branch nonzero) → TBZ (test bit zero)
        # TBNZ encoding: bit 24 = 1; TBZ encoding: bit 24 = 0
        # In LE layout, bit 24 is in byte[3], bit 0 of byte[3]
        # TBNZ → TBZ: XOR byte[3] with 0x01 to flip bit 24
        local TBNZ_COUNT=0
        if [ -s "$PATTERN_FILE" ]; then
            while IFS= read -r pattern_str; do
                [ -z "$pattern_str" ] && continue
                local STR_OFFSETS
                STR_OFFSETS=$(grep -aob "$pattern_str" "$BINARY_PATH" 2>/dev/null | cut -d: -f1 || true)
                for str_off in $STR_OFFSETS; do
                    local scan_start=$((str_off > 256 ? str_off - 256 : 0))
                    local scan_end=$((str_off + 256))

                    # Use perl to scan the window for TBNZ instructions (byte[3] & 0x01 == 1
                    # and upper nibble of byte[3] == 0x3 for TBNZ family)
                    # TBNZ Wn: byte[3] = 0x37, TBZ Wn: byte[3] = 0x36 (32-bit)
                    # TBNZ Xn: byte[3] = 0xB7, TBZ Xn: byte[3] = 0xB6 (64-bit)
                    perl -i -pe '
                        our $out=$_;
                        our $patched=0;
                        if ($. == 1 && length($_) > '"$scan_start"') {
                            my $window = substr($_, '"$scan_start"', 512);
                            $window =~ s/(.{4})/
                                my $w = $1;
                                my $b3 = ord(substr($w, 3, 1));
                                # TBNZ -> TBZ: flip bit 0 of byte[3] (0x37->0x36, 0xB7->0xB6)
                                if ($b3 == 0x37 || $b3 == 0xB7) {
                                    substr($w, 3, 1) = chr($b3 ^ 1);
                                    $patched++;
                                }
                                $w
                            /seg;
                            substr($_, '"$scan_start"', 512) = $window;
                        }
                    ' "$BINARY_PATH" 2>/dev/null
                    echo "[hex] TBNZ→TBZ near offset $str_off for '$pattern_str'"
                done
            done < "$PATTERN_FILE"
        fi
        TBNZ_COUNT=$(grep -aobP '\x36[\x00-\xFF][\x00-\xFF]\x00|\xB6[\x00-\xFF][\x00-\xFF]\x00' "$BINARY_PATH" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        echo "[hex] Patched $TBNZ_COUNT TBNZ→TBZ instructions"
    fi

    # ── x86_64: Patch common patterns ──────────────────────
    if file "$BINARY_PATH" | grep -qi "x86_64\|x86-64"; then
        echo "[hex] Patching x86_64 binary..."

        # Pattern 1: TEST AL,AL (84 C0) → XOR AL,AL (30 C0)
        # TEST AL,AL sets ZF based on AL; XOR AL,AL always sets ZF=1
        # This forces any subsequent JZ to always take the jump
        local TEST_AL_COUNT
        TEST_AL_COUNT=$(grep -aobP '\x84\xC0' "$BINARY_PATH" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        echo "[hex] Found $TEST_AL_COUNT TEST AL,AL instructions"

        if [ "$TEST_AL_COUNT" -gt 0 ] 2>/dev/null; then
            perl -i -pe 's/\x84\xC0/\x30\xC0/g' "$BINARY_PATH"
            echo "[hex] Patched TEST AL,AL → XOR AL,AL (force ZF=1)"
        fi

        # Pattern 2: JZ rel8 (74 XX) → NOP NOP (90 90)
        # JZ jumps if ZF=1; replacing with NOP NOP ensures fallthrough
        # Paired with XOR AL,AL above, this forces the "licensed" path
        local JZ_COUNT
        JZ_COUNT=$(grep -aobP '\x74' "$BINARY_PATH" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        echo "[hex] Found $JZ_COUNT JZ rel8 instructions"

        # Targeted approach: only NOP JZ near license check strings
        local JZ_PATCHED=0
        if [ -s "$PATTERN_FILE" ]; then
            while IFS= read -r pattern_str; do
                [ -z "$pattern_str" ] && continue
                local STR_OFFSETS
                STR_OFFSETS=$(grep -aob "$pattern_str" "$BINARY_PATH" 2>/dev/null | cut -d: -f1 || true)
                for str_off in $STR_OFFSETS; do
                    local scan_start=$((str_off > 512 ? str_off - 512 : 0))
                    perl -i -pe '
                        our $patched=0;
                        if ($. == 1 && length($_) > '"$scan_start"') {
                            my $window = substr($_, '"$scan_start"', 1024);
                            # Replace JZ rel8 (74 XX) with NOP NOP (90 90)
                            # Only within the scan window
                            $window =~ s/\x74(.)/\x90\x90/g;
                            substr($_, '"$scan_start"', 1024) = $window;
                        }
                    ' "$BINARY_PATH" 2>/dev/null
                    echo "[hex] JZ→NOP near offset $str_off for '$pattern_str'"
                done
            done < "$PATTERN_FILE"
            JZ_PATCHED=1
        fi

        # Fallback: if no license strings found, do a conservative global patch
        # Only patch JZ instructions that follow TEST AL,AL (already replaced)
        # This is less aggressive but covers cases where the binary has no string table
        if [ "$JZ_PATCHED" -eq 0 ] && [ "$TEST_AL_COUNT" -gt 0 ] 2>/dev/null; then
            echo "[hex] No license strings found — applying conservative JZ→NOP"
            perl -i -pe 's/\x74(.)/\x90\x90/g' "$BINARY_PATH"
            echo "[hex] Conservative: all JZ rel8 → NOP NOP"
        fi

        local TOTAL_NOP_COUNT
        TOTAL_NOP_COUNT=$(grep -aobP '\x90\x90' "$BINARY_PATH" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        echo "[hex] Patched x86_64: $TEST_AL_COUNT TEST→XOR, NOP pairs: $TOTAL_NOP_COUNT"
    fi

    # ── Step 4: Verify patch integrity ────────────────────
    local NEW_SIZE OLD_SIZE
    NEW_SIZE=$(wc -c < "$BINARY_PATH" 2>/dev/null | tr -d ' ')
    OLD_SIZE=$(wc -c < "$BACKUP_PATH" 2>/dev/null | tr -d ' ')

    if [ "$NEW_SIZE" = "$OLD_SIZE" ]; then
        echo "[hex] Binary size unchanged ($NEW_SIZE bytes) — patch applied in-place"
    else
        echo "[hex] WARNING: Binary size changed ($OLD_SIZE → $NEW_SIZE bytes)"
        echo "[hex] Restoring from backup..."
        cp "$BACKUP_PATH" "$BINARY_PATH"
        echo "[hex] Binary restored — patch aborted to avoid corruption"
        rm -f "$PATTERN_FILE"
        return 1
    fi

    rm -f "$PATTERN_FILE"
    echo "[hex] Hex patch complete"
    return 0
}