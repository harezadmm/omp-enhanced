# mac-app-cracking

Universal Mac app reverse-engineering & crack packaging skill. Produces self-contained `.dmg` with `.pkg` installer — user double-clicks `.pkg`, app is cracked automatically. No terminal, no scripts, no extra steps.

Covers **14 crack types** across 4 major Mac crack scenes (TNT, EDiSO, Hopper, appstorrent) — from simple UserDefaults injection to full binary patching with keygen.

## Triggers

- "crack this Mac app"
- "make a cracked DMG"
- "bypass license/Mac app"
- "inject license into .app"
- "build self-contained Mac installer"
- Any `.dmg`/`.app` with license/paywall/trial

## When to use

- User has a Mac app (`.app` or `.dmg`) with license check, trial limit, paywall, or subscription
- User wants a portable `.dmg` they can share — recipient just installs and it's cracked
- License type: any of 14 crack types (RevenueCat to TNT Gatekeeper bypass to patcher+keygen)

## Workflow

### Phase 1: Analysis — What kind of license?

All analysis runs on **Windows** using 7-Zip + Python. Mac only needed for final `.pkg` build.

#### 1a. Extract the DMG (two-phase)

```bash
# Phase 1a-1: Extract outer DMG
"C:\Program Files\7-Zip\7z.exe" x "AppName.dmg" -o"dmg_outer/" -y

# Phase 1a-2: Look for inner DMG/ISO/payload
"C:\Program Files\7-Zip\7z.exe" l "dmg_outer/*.dmg" 2>nul || :  # Check for inner DMG
"C:\Program Files\7-Zip\7z.exe" x "dmg_outer/inner.dmg" -o"dmg_inner/" -y

# ⚠️ Bracket characters in filenames MUST be renamed to _ before extraction:
# mv "file[1].dmg" "file_1_.dmg"
```

#### 1b. Identify license method

```bash
# Check bundle ID
grep -r "CFBundleIdentifier" AppName.app/Contents/Info.plist 2>/dev/null

# Check for scene release markers (TNT/EDiSO/Hopper)
find . -name "*.nfo" -o -name "*.sfv" -o -name "Help.txt" -o -name "rhash" 2>/dev/null
find . -name "macked.app.dylib" -o -name "_MASReceipt" 2>/dev/null

# Check for license frameworks
find . -path "*/Frameworks/*" -name "*RevenueCat*" -o -name "*Superwall*" -o -name "*AppsFlyer*" -o -name "*Purchases*" 2>/dev/null

# Check for Sparkle update framework (used by EDiSO/StoreKit cracks)
find . -name "Sparkle.framework" -o -name "SUFeedURL" 2>/dev/null

# Check for Patcher + keygen (Plasticity-style cracks)
find . -name "Patch" -o -name "keygen" -o -path "*/patchfiles/*" 2>/dev/null

# Check for protection labels (EDiSO convention)
strings AppName.app/Contents/MacOS/* 2>/dev/null | grep -iE "AES\+ECC|protection|license server|key validation"

# Check binary for license/activation strings (Python — `strings` not on Windows PATH)
python3 -c "
import re, sys
data = open('AppName.app/Contents/MacOS/AppName','rb').read()
# ASCII strings ≥6 chars
try:
    text = data.decode('latin-1')
    for m in re.finditer(r'[\x20-\x7e]{6,}', text):
        s = m.group()
        if re.search(r'(?i)license|activate|trial|pro|premium|validate|purchase|subscript', s):
            print(s)
except: pass
"

# Check UserDefaults for license keys (on Mac)
defaults read com.example.bundle 2>/dev/null | grep -iE "license|pro|premium|trial|purchase|subscri"

# Check for cache files (on Mac)
find ~/Library -path "*com.example.bundle*" -name "*.plist" -o -name "*.json" 2>/dev/null

# Check Info.plist for custom keys, Sparkle feeds, LSEnvironment
grep -E "SUFeedURL|SUPublicEDKey|LSEnvironment|NSLocalNetworkUsageDescription" AppName.app/Contents/Info.plist 2>/dev/null
```

#### 1c. Auto-classify (Windows analysis)

```bash
# Priority-ordered detection. First match wins.
# 1. TNT Gatekeeper: Extra/tnt.nfo or Extra/tnt.sfv exists
# 2. EDiSO StoreKit: ediso.nfo + binary has StoreKit strings (purchaseCompleted, SKPayment)
# 3. EDiSO Binary:   ediso.nfo + dmgcanvas_bg.tiff + NO StoreKit + binary has license server URLs
# 4. Tauri JS Patch: ediso.nfo + binary 100MB+ with ZERO license strings
# 5. Patcher+Keygen: Patcher/ folder + keygen binary exists
# 6. Hopper Injection: macked.app.dylib + "Cryptic Apps SARL" copyright string
# 7. RevenueCat: RevenueCat_RevenueCat.bundle exists
# 8. UserDefaults: defaults read $BUNDLE_ID | grep license returns keys
# 9. License Server Block: /etc/hosts entries or plist immutable flags in existing crack
# 10. Activation Tool: Separate .tool/.command file alongside .dmg
# 11. BINARY_PATCH: Generic fallback — binary has license strings but nothing above matches
# 12. OnlineActivation+HMAC: Binary has RLM framework strings (rlm, ISV, REP) + OAuth2/Trimble ID + subscription state machine
# 13. AppleReceipt+Keychain: _MASReceipt file + SKReceiptRefreshRequest + Keychain service strings (SecItemAdd/SecItemDelete)
# 14. Custom License + HWID: Binary has HWIDProvider + custom license API URLs (no StoreKit, no RevenueCat)
```

### Phase 2: Classify crack type

| # | Crack Type | Crack Method | Detection Fingerprint | Scene |
|---|---|---|---|---|
| 1 | **TNT Gatekeeper** | Gatekeeper bypass + binary patch | `Help.txt` + `Extra/{tnt.nfo,tnt.sfv,rhash}` + `.VolumeIcon.icns` + PGP-signed `.nfo` | TNT |
| 2 | **EDiSO Binary** | Binary hex patch to NOP license checks | `ediso.nfo` + `dmgcanvas_bg.tiff` + protection label + license server URLs in binary | EDiSO |
| 3 | **EDiSO StoreKit** | Binary patch to fake StoreKit receipts | Same DMG as #2 + binary has `purchaseCompleted`/`SKPayment` + `SUFeedURL` | EDiSO |
| 3E | **EDiSO StoreKit Extended** | StoreKit bypass + DeviceLicenseService + Keychain UUID + Sparkle patch | `purchaseCompleted`/`SKPayment` strings + `DeviceLicenseService` class + `SecItemAdd` keychain UUID + `CustomSparkleUserDriver` + Sparkle appcast → 127.0.0.1:9 | EDiSO |
| 3+7 | **EDiSO StoreKit + Keychain + DNS** | StoreKit bypass + Keychain trial reset + license server DNS sinkhole | EDiSO scene + `SKProduct`/`purchaseCompleted` strings + `KeychainSwift`/`SecItemAdd` + DNS sinkhole IPs + `macked.app.pkg` + `keygen` Swift binary + `_MASReceipt` regeneration | EDiSO |
| 4 | **Tauri/JS Patch** | JavaScript-level crack (WebView logic) | Same DMG as #2 + binary 100MB+ with **zero** license strings | EDiSO |
| 5 | **Hopper Injection** | Runtime dylib injection via Hopper | `macked.app.dylib` in Frameworks + `(c) 2014 Cryptic Apps SARL` + `_MASReceipt` | Hopper |
| 6 | **Patcher + Keygen** | ISO-level binary swap + keygen | `Patcher/` folder + `keygen` Swift binary + `patchfiles/{arch}/` with V8 JSC | appstorrent |
| 12 | **OnlineActivation+HMAC** | RLM license server + HMAC validation bypass | Binary has RLM framework strings (`rlm`, `ISV`, `REP`) + OAuth2/Trimble ID + `Authorization: Basic` headers + subscription state machine + `entitlement` polling + device heartbeat + `.nfo` states: "no local license validation" | Self-built |
| 7 | **License Server Block** | Hosts block + immutable plists | `/etc/hosts` entries + `chflags uchg` on license plists | Any |
| 7+8 | **License Block + RevenueCat Combo** | Hosts block + RevenueCat fake `purchaserInfo` | `/etc/hosts` entries blocking `api.revenuecat.com` + `RevenueCat_RevenueCat.bundle` + bundled `license-domains.txt` | Scene (analyzed) |
| 8 | **RevenueCat** | Fake `purchaserInfo` plist injection | `RevenueCat_RevenueCat.bundle` + `com.revenuecat.user_defaults.plist` | Self-built |
| 9 | **Custom License + HWID** | Binary patch + HWID activation bypass | HWIDProvider class + custom license API URLs (`/api/v1/activate`, `/me`) + no StoreKit, no RevenueCat | Self-built |
| 13 | **AppleReceipt+Keychain** | IAP receipt regeneration + Keychain trial wipe | `_MASReceipt` file + `SKReceiptRefreshRequest` + Keychain service strings (`SecItemAdd`/`SecItemDelete`) + trial state in `com.apple.receipt` | Self-built |
| 10 | **Cache File** | Fake license JSON/plist to disk | License JSON/plist in `~/Library/Application Support/` | Self-built |
| 11 | **Activation Tool** ⚠️ | Separate `.tool`/`.command` script | `.tool`/`.command` file alongside .dmg — **THEORETICAL ONLY, zero analyzed examples** | Unknown |

### Crack Type Reference

Detailed detection → methodology → evidence → pitfalls for all 16 types.

---

#### Type 1: TNT Gatekeeper (`tnt_gatekeeper`)

**Detection fingerprint:**
```
DMG contains:
  Help.txt                    ← "Open Gatekeeper friendly" instructions
  Extra/
    tnt.nfo                   ← PGP-signed ASCII art release info
    tnt.sfv                   ← rhash-compatible SHA-256 checksums
    rhash                     ← Verification tool binary
  .VolumeIcon.icns            ← Custom DMG icon
  .background/                ← DMG background image (optional)

Binary analysis:
  Swift name-mangled license symbols → binary patch target
  RLM (Reprise License Manager) framework → license server bypass target
  PGP key fingerprint: 9D4B 00AE 65EC 2E79 F8AE 9B2D 3E42 3DD4 CF0A 7487
  PGP identity: tnt4mac@tuta.io
```

**Methodology:**

TNT releases ship the **original unmodified app** + a Gatekeeper bypass script. The crack is in the DMG packaging, not the app binary. The method:

1. **Gatekeeper bypass**: `xattr -rd com.apple.quarantine /Applications/AppName.app` or `spctl --master-disable`
2. **hdiutil shadow mount**: The DMG uses a shadow file to mount read-write without modifying the original DMG
3. **Binary patch** (already applied by TNT in the bundled app):
   - Swift apps: Patch `LicenseValidator.checkSignature(_,serial:)` — discovered via `nm -gU` for name-mangled Swift symbols
   - RLM apps (SketchUp, Autodesk): Patch RLM framework to (a) return cached license always valid, (b) block license server communication, (c) disable subscription expiry check
4. **Sparkle update block**: Disable `SUFeedURL` or block Sparkle update server
5. **Verification**: `Extra/rhash -r Extra/tnt.sfv --sha256 --skip-ok -c`

**Real-world evidence:**
- **ForkLift 4.7.5 [TNT]** — Ad-Hoc Sign Only | `NTLicenseFramework.framework` in Contents/Frameworks | Binary patch: `isValidLicense` → always return `true`, `trialDaysRemaining` → `INT_MAX` | `fwkNTLicenseFramework` dylib injection | `NSHumanReadableCopyright` → `"TNT team"` | All trial/validation messages intact in binary
- **SketchUp 2026.3** — 35MB C++ binary with full RLM framework | TNT Easter egg | RLM license server bypass

**Pitfalls:**
- The `.nfo` file must pass PGP signature verification for TNT authenticity — unsigned `.nfo` = fake/malware
- Rhash tool bundled in `Extra/` is known-good; don't replace it
- Post-install: user must still run `xattr -cr` if Gatekeeper is enabled (the Help.txt instructs this)

---

#### Type 2: EDiSO Binary Patch (`ediso_binary_patch`)

**Detection fingerprint:**
```
DMG contains:
  ediso.nfo                  ← ASCII-art release info (NOT PGP-signed, unlike TNT)
  .VolumeIcon.icns           ← Custom icon
  .background/
    dmgcanvas_bg.tiff        ← DMG Canvas background image (EDiSO signature)

App binary has:
  Protection label string    ← e.g., "AES+ECC+SHA+B64+CTM" (Alcove), "Polar" (other releases)
  License server URLs        ← e.g., https://api.example.com/license/validate
  NSLocalNetworkUsageDescription = "license validation" in Info.plist

NO StoreKit strings (no purchaseCompleted, no SKPaymentQueue, no SKProduct)
```

**Methodology:**

1. **Binary hex edit**: Find the license validation function via `strings | grep` pattern and hex-edit to NOP/bypass:
   - Replace `JNE` (conditional jump on failure) with `JMP` (unconditional jump)
   - Replace `CMP`-`RET` pattern with immediate `MOV RAX, 0` + `RET` (return success)
   - For the protection label (`AES+ECC+SHA+B64+CTM`): these describe how the license check is obfuscated in the binary — AES-encrypted sections, ECC key validation, SHA hash checks, Base64-encoded payloads, CTM (custom transform method)
2. **License server block**: Add `0.0.0.0 api.example.com` to `/etc/hosts`
3. **Re-sign ad-hoc**: `codesign --force --deep --sign - /Applications/AppName.app`
4. **xattr cleanup**: `xattr -cr /Applications/AppName.app`

**Real-world evidence:**
- **Alcove** — EDiSO binary patch | Protection label: `AES+ECC+SHA+B64+CTM` | `NSLocalNetworkUsageDescription` = license validation | All license logic in binary (no StoreKit, no RevenueCat)

**Pitfalls:**
- Protection label is obfuscation description, not a crypto challenge — don't try to actually decrypt; patch the binary around it
- `NSLocalNetworkUsageDescription` = "license validation" is an EDiSO convention — it's the app's stated purpose for local network access, which is the license check
- Multiple license server URLs → all must be blocked or the check may still pass

---

#### Type 3: EDiSO StoreKit Patch (`ediso_storekit_patch`)

**Detection fingerprint:**
```
Same DMG structure as EDiSO Binary (#2):
  ediso.nfo + dmgcanvas_bg.tiff + .VolumeIcon.icns

App binary ADDITIONALLY has:
  StoreKit strings: purchaseCompleted, SKPaymentQueue, SKProduct, addTransactionObserver
  "Activate License" string in binary
  LicenseManager / LicenseService class names
  SUFeedURL + SUPublicEDKey in Info.plist (Sparkle update framework)
```

**Methodology:**

1. **Binary patch for StoreKit**: Find `SKPaymentTransactionObserver` delegate methods and patch to always return `.purchased` / `.restored` state
2. **Fake receipt injection**: Some EDiSO StoreKit cracks inject a fake `receipt` into the app bundle
3. **Sparkle update block**: Remove `SUFeedURL` from Info.plist or block the Sparkle update server domain
4. **Re-sign ad-hoc**: Standard codesign flow

**Real-world evidence:**
- **SlapMac** — EDiSO StoreKit patch | `SUFeedURL` + `SUPublicEDKey` for Sparkle updates | `com.tonnoz.slapmac` | StoreKit purchaseCompleted strings in binary | "Activate License" string

**Additional variant (Hybrid Type 3+7):**
- **Wallspace 1.5.1 [EDiSO]** — StoreKit IAP + Device License Service | `com.wallspace.pro.test.1` Non-Consumable IAP | `purchaseCompleted`, `SKPaymentQueue`, `SKProduct` strings | Supabase Discord verification (`dvivcibhncrefmnjtjeq.supabase.co/functions/v1/verify-discord`) | `DeviceLicenseService` class with keychain UUID storage | Sparkle appcast patched to `127.0.0.1:9` | `CustomSparkleUserDriver` subclass

**Pitfalls:**
- StoreKit receipt validation may check against Apple servers — the patch must short-circuit BEFORE the network call
- Sparkle feed must be disabled otherwise auto-update will overwrite the cracked binary

---

#### Type 3E: EDiSO StoreKit Extended (`ediso_storekit_extended`)

**Detection fingerprint:**
```
Same EDiSO DMG (ediso.nfo + dmgcanvas_bg.tiff)
PLUS:
  StoreKit strings: purchaseCompleted, SKPaymentQueue, SKProduct
  DeviceLicenseService class name in binary
  Keychain service strings: SecItemAdd, SecItemDelete, kSecClassGenericPassword
  "Activate License" / "Restore Purchases" strings
  CustomSparkleUserDriver — subclassed Sparkle updater
  Discord/webhook verification URL in binary (often Supabase/Netlify Functions)
  License UUID stored in Keychain, NOT UserDefaults
```

**Methodology:**

1. **Binary patch StoreKit delegates**: Patch `paymentQueue:updatedTransactions:` to always return `.purchased` state
2. **Keychain preload**: Create fake license UUID in Keychain that matches expected format
3. **Block verification URLs**: Add all webhook/Supabase/Netlify endpoints to `/etc/hosts`
4. **Sparkle appcast patch**: Hex-edit SUFeedURL to `127.0.0.1:9` or empty string
5. **Re-sign ad-hoc**: Standard codesign flow

**Real-world evidence:**
- **Wallspace 1.5.1 [EDiSO]** — StoreKit IAP + Device License Service | `com.wallspace.pro.test.1` Non-Consumable IAP | `purchaseCompleted`, `SKPaymentQueue`, `SKProduct` strings | Supabase Discord verification (`dvivcibhncrefmnjtjeq.supabase.co/functions/v1/verify-discord`) | `DeviceLicenseService` class with keychain UUID storage | Sparkle appcast patched to `127.0.0.1:9` | `CustomSparkleUserDriver` subclass

**Pitfalls:**
- Keychain UUID is app-specific — extract format from binary strings before preloading
- Multiple verification endpoints (Discord webhook + Supabase + license server) — ALL must be blocked or patched
- CustomSparkleUserDriver is a Sparkle delegate subclass — standard Sparkle URL removal may not work; patch the driver class directly
- DeviceLicenseService may re-validate on network status change — block ALL outbound license URLs, not just the primary one

---

#### Type 4: Tauri/JS Patch (`tauri_js_patch`)

**Detection fingerprint:**
```
Same DMG structure as EDiSO Binary (#2):
  ediso.nfo + dmgcanvas_bg.tiff + .VolumeIcon.icns

Binary analysis:
  Binary is 100MB+ (Tauri's embedded WebView runtime)
  ZERO license-related strings in the binary:
    - No "Purchase", "License", "Activate", "Trial", "validate"
    - No StoreKit strings
    - No RevenueCat framework
    - No Superwall framework
  All app logic lives in JavaScript (WebView bundle)

Tauri app structure:
  Contents/Resources/
    app/                      ← WebView app bundle (HTML/JS/CSS)
    app.asar                  ← OR: packed ASAR archive
    _nupkg/                   ← OR: Squirrel update packages
```

**Methodology:**

1. **Find the JS bundle**: Tauri apps store web content in `Contents/Resources/app/` (unpacked) or `app.asar` (packed, extract with `npx asar extract`)
2. **Locate license logic**: Search JS files for `license`, `activate`, `purchase`, `validate`, `premium`, `pro`
3. **Patch JS**: Replace the license check function to always return `true`, change feature flags, or modify the Vue/React state
4. **Re-pack if ASAR**: `npx asar pack app/ app.asar`
5. **Re-sign**: Standard codesign flow

**Real-world evidence:**
- **Cap 0.5.9 [EDiSO]** — 135.9MB binary with ZERO license strings | `so.cap.desktop` bundle ID | EDiSO DMG packaging | All logic in Tauri WebView JavaScript

**Pitfalls:**
- Don't waste time on the binary — it's just Tauri's runtime. All license logic is in JS.
- ASAR vs unpacked: check `Contents/Resources/` first. If `app.asar` exists, use `npx asar extract`. If `app/` directory exists, it's already unpacked.
- Minified JS is harder to patch — use `prettier --write` to format, then patch, then optionally re-minify
- Tauri version matters: v1 uses `app/` or `app.asar`; the exact path within Resources varies

---

#### Type 5: Hopper Injection (`hopper_dylib_injection`)

**Detection fingerprint:**
```
App bundle contains:
  Contents/Frameworks/macked.app.dylib    ← Injected dylib
  Contents/_MASReceipt/                   ← MAS receipt bypass directory

Dylib analysis:
  strings macked.app.dylib:
    "(c) 2014 - Cryptic Apps SARL"        ← Hopper Disassembler copyright
    "mach_vm_protect"                     ← Live memory patching
    "cdhashes"                            ← Code signature hash bypass
    "com.apple.security.cs"               ← Codesign bypass
```

**Methodology:**

The `macked.app.dylib` is **Hopper Disassembler's runtime library**, not a custom injection framework. The crack works by:

1. **DYLD_INSERT_LIBRARIES**: The dylib is loaded at app launch via `DYLD_INSERT_LIBRARIES` or linked into the binary
2. **Live memory patching**: Hopper's runtime uses `mach_vm_protect` to make code pages writable, then patches the license check functions in memory at runtime
3. **Codesign hash bypass**: `cdhashes` manipulation to prevent the system from detecting the modified code
4. **MAS receipt bypass**: `_MASReceipt/` directory tricks the app into thinking it has a valid Mac App Store receipt
5. **No permanent binary modification**: The original binary is unmodified — all patches are in-memory at runtime

**Real-world evidence:**
- **Sip** — Hopper dylib injection | `macked.app.dylib` with `(c) 2014 Cryptic Apps SARL` | `mach_vm_protect` + codesign bypass
- **Raycast** — Hopper dylib injection + `_MASReceipt` directory bypass

**Pitfalls:**
- `macked.app.dylib` is NOT custom malware — it's Hopper Disassembler's legitimate runtime library being repurposed
- SIP (System Integrity Protection) may block `DYLD_INSERT_LIBRARIES` on newer macOS — the app must be re-signed with `com.apple.security.cs.disable-library-validation` entitlement
- dylib must match the app's architecture (arm64 vs x86_64)
- If the dylib crashes, the entire app crashes — there's no graceful fallback

---

#### Type 6: Patcher + Keygen (`patcher_keygen`)

**Detection fingerprint:**
```
ISO/DMG contains:
  Patcher/                         ← Dedicated patcher directory
    Patch                          ← Bash script (200+ lines)
    keygen                         ← Swift universal binary (arm64 + x86_64)
    patchfiles/
      arm64/
        index.jsc                  ← V8 compiled JavaScript (12-20MB)
        pk.node                    ← Node.js addon binary (18-21MB)
      x86_64/
        index.jsc
        pk.node
  Fix (APFS disk image)            ← Optional: Gatekeeper bypass + xattr removal
  .instructions.html               ← User-facing instructions
```

**Methodology:**

This is the most sophisticated crack type. Multi-layer:

1. **ISO-level Patcher**:
   - SHA-256 verify stock binary hashes (6 hashes: stock + patched per arch for each file)
   - Replace arch-specific `index.jsc` and `pk.node` from `patchfiles/{arch}/`
   - Run keygen: `$HERE/keygen "$HOME/.appname"` → generates `license.lic` + `license.key`
   - Ad-hoc codesign with entitlements: `codesign --force --deep --sign - --entitlements entitlements.plist`
2. **APFS-level Fix** (separate `.dmg`):
   - Gatekeeper bypass: `xattr -rd com.apple.quarantine`
   - `spctl --master-disable` workaround
3. **Keygen algorithm** (Plasticity case study):
   - Swift universal binary using CryptoKit framework
   - Machine fingerprint: IOPlatformExpertDevice + sysctl (hw.machine, hw.ncpu, hw.memsize, kern.boottime) + NSHomeDirectory()
   - ED25519 signing: `Curve25519.Signing.PrivateKey` signs machine fingerprint data
   - AES-256-GCM encryption: `SymmetricKey` from seed data, `AES.GCM.seal()` with random nonce
   - Output: `~/.plasticity/license.lic` + `license.key`
   - Labels: `aes-256-gcm+ed25519`, PEM-armored machine file

**Real-world evidence:**
- **Plasticity v26.1.3** — appstorrent release | 220-line Patch script | 260KB Swift universal keygen | V8 compiled JSC replacement (12MB arm64, 12MB x86_64) | pk.node replacement (18.6MB arm64, 21MB x86_64) | SHA-256 hash verified | CryptoKit ED25519 + AES-256-GCM | ISO + APFS Fix dual-layer

**Pitfalls:**
- Arch mismatch (arm64 JSC on x86_64 machine) → immediate crash
- V8 snapshot version mismatch → crash on file read
- Entitlements MUST include: `com.apple.security.cs.allow-jit`, `com.apple.security.cs.allow-unsigned-executable-memory`, `com.apple.security.cs.disable-library-validation`
- The Patch script is app-specific — can't be reused for other apps
- Keygen is tied to the specific app's license format — reverse-engineering it requires analyzing the keygen binary itself

---

#### Type 7: License Server Block (`license_server_block`)

**Detection fingerprint:**
```
/etc/hosts entries:
  0.0.0.0 api.revenuecat.com
  0.0.0.0 api.superwall.com
  0.0.0.0 api.example.com

Immutable license plists:
  ls -lO ~/Library/Containers/*/Data/Library/Preferences/com.revenuecat.user_defaults.plist
  # Shows "uchg" flag (user immutable)

Combined with:
  RevenueCat bundle (Type 8) OR
  UserDefaults injection (Type 14) OR
  Custom API URLs in binary strings
```

**Methodology:**

This is a **companion** technique used alongside RevenueCat or UserDefaults cracks. Not a standalone crack type.

**Real-world evidence:**
- **Alcove** — `/etc/hosts` block: `0.0.0.0 api.bigbluebubble.com` (license validation server) | Companion to Type 2 EDiSO Binary Patch
- **Wallspace 1.5.1** — `/etc/hosts` block: `0.0.0.0 dvivcibhncrefmnjtjeq.supabase.co` (Discord verification endpoint) | Companion to Type 3 StoreKit Patch
- **Linearity Curve / any RevenueCat app** — `/etc/hosts` block: `0.0.0.0 api.revenuecat.com` | Companion to Type 8 RevenueCat Patch

1. **Block API hosts**: Add `0.0.0.0 api.revenuecat.com api.superwall.com` to `/etc/hosts`
2. **Flush DNS**: `dscacheutil -flushcache; killall -HUP mDNSResponder`
3. **Lock plists immutable**: `chflags uchg ~/Library/.../com.revenuecat.user_defaults.plist` — prevents the app from overwriting the fake license
4. **Sparkle update block**: Remove `SUFeedURL` from Info.plist to prevent auto-update from restoring original binary

**Pitfalls:**
- `chmod 444` is NOT enough — the app process owns the file and can chmod it back. MUST use `chflags uchg`.
- DNS flush commands may fail silently on newer macOS — verify with `dscacheutil -q host -a name api.revenuecat.com`
- Some apps use hardcoded IPs → hosts-based block won't work; must patch binary or use firewall rule

---

#### Type 8: RevenueCat Patch (`revenuecat_patch`)

**Detection fingerprint:**
```
App bundle contains:
  Contents/Frameworks/RevenueCat_RevenueCat.bundle   ← RevenueCat SDK
  (optionally paired with):
    SuperwallKit_SuperwallKit.bundle                 ← Superwall paywall SDK
    AppsFlyerLib.framework                           ← Analytics/attribution

User data at:
  ~/Library/Containers/BUNDLE_ID/Data/Library/Preferences/com.revenuecat.user_defaults.plist
```

**Methodology:**

RevenueCat stores license as a **double-encoded** binary plist:
- Outer layer: standard `NSUserDefaults` plist
- Inner layer: `purchaserInfo` key contains a **binary plist** blob which itself contains a **JSON string**

```python
import plistlib, json, subprocess
from datetime import datetime
from pathlib import Path

BUNDLE_ID = "com.example.app"
UID = "$RCAnonymousID:abc123..."

# Build the fake purchaserInfo JSON
info = {
    'schema_version': '3',
    'first_seen': '2024-01-01T00:00:00Z',
    'original_app_user_id': UID,
    'subscriber': {
        'entitlements': {
            'pro': {
                'product_identifier': 'app_pro_yearly',
                'expires_date': '2099-01-01T00:00:00Z',
                'is_sandbox': False,
                'ownership_type': 'PURCHASED',
                'store': 'APP_STORE',
                'is_active': True,
                'will_renew': True,
            }
        },
        'subscriptions': {
            'app_pro_yearly': {
                'product_identifier': 'app_pro_yearly',
                'expires_date': '2099-01-01T00:00:00Z',
                'is_sandbox': False,
                'ownership_type': 'PURCHASED',
                'store': 'APP_STORE',
            }
        },
        'non_subscriptions': {},
    },
}

# Double-encode: JSON → binary plist blob
json_bytes = json.dumps(info).encode('utf-8')
data_blob = plistlib.dumps(json_bytes, fmt=plistlib.FMT_BINARY)

# Build outer plist
prefs = {
    'com.revenuecat.userdefaults.appUserID.new': UID,
    f'com.revenuecat.userdefaults.purchaserInfo.{UID}': data_blob,
    f'com.revenuecat.userdefaults.purchaserInfoLastUpdated.{UID}': datetime.now(),
}

# Find the plist path (sandboxed app → Containers)
P = Path.home() / f'Library/Containers/{BUNDLE_ID}/Data/Library/Preferences/com.revenuecat.user_defaults.plist'
P.parent.mkdir(parents=True, exist_ok=True)

# Write + lock immutable
with open(P, 'wb') as f:
    plistlib.dump(prefs, f)
subprocess.run(['chflags', 'uchg', str(P)])  # Lock — chmod 444 is NOT enough
```

**Real-world evidence:**
- **Linearity Curve 6.10.3** — RevenueCat + Superwall + AppsFlyer | Double-encoding confirmed working

**Pitfalls:**
- App rewrites plist on launch → MUST use `chflags uchg` (system immutable flag). `chmod 444` is insufficient.
- `UID` value is app-specific — extract from a real plist first or from the app's binary strings
- Sandboxed apps use `~/Library/Containers/`, non-sandboxed use `~/Library/Preferences/` — check both
- Superwall is often paired with RevenueCat — must block BOTH API endpoints

---

#### Type 7+8: License Block + RevenueCat Combo (`license_revenuecat_combo`)

**Detection fingerprint:**
```
RevenueCat strings (purchaserInfo, offerings, RevenueCat.bundle)
PLUS:
  License domain strings in binary (licenses.linearity.com, *.linearity.io)
  Multiple verification endpoints in different hosts
  Blocklist in hosts file is effective for license check BUT NOT for RevenueCat
  Mix-and-match: offline license check bypassable by hosts block + online RevenueCat IAP validation
```

**Methodology:**

1. **Parse binary strings for ALL API domains**: Run `strings | grep -E 'https?://'` — identify license servers AND RevenueCat endpoints
2. **Block ALL license domains via hosts file**: Add license servers, webhook URLs, and telemetry domains to `/etc/hosts`
3. **Frida/gate bypass for RevenueCat IAP**: Patch `- (void)paymentQueue:updatedTransactions:` to return `SKPaymentTransactionStatePurchased`
4. **Preload purchaserInfo cache**: Write fake entitlement JSON to `~/Library/Application Support/<bundle>/` mimicking RevenueCat's cached response
5. **Re-sign ad-hoc**: Standard codesign flow

**Real-world evidence:**
- **Linearity Curve 6.10.3** — AppStore subscription IAP from RevenueCat SDK + domain-based license check | `api.revenuecat.com`, `licenses.linearity.com` + 14 other Linearity domains blocked in hosts | `NSAppTransportSecurity` dictionary allows HTTP for licensingserver:8080 | `license-domains.txt` shipped as part of crack bundle (15 domains total)

**License domain bundle (shipped in crack):**
```
# License services — block these for the license check bypass
127.0.0.1 licenses.linearity.com
127.0.0.1 licensingserver.localhost
127.0.0.1 api.linearity.io
# RevenueCat — hosts block alone WON'T work for IAP; needs Frida/gate
# 127.0.0.1 api.revenuecat.com  ← DO NOT BLOCK THIS WAY
# Telemetry & analytics
127.0.0.1 telemetry.linearity.com
127.0.0.1 events.linearity.io
```

**Pitfalls:**
- RevenueCat hosts block alone will NOT bypass IAP — must combine with Frida/gate or StoreKit delegate patching
- `NSAppTransportSecurity` exceptions may allow HTTP — don't assume HTTPS is enforced
- License domain list is app-specific — ship a `license-domains.txt` with each crack
- Telemetry domains are often mixed with license domains in the binary — block them all for clean state
- Consumer-grade `hosts` block is fragile — if user runs without the hosts file, app phones home silently

---

#### Type 14: UserDefaults (`userdefaults`)

**Detection fingerprint:**
```
defaults read com.example.bundle 2>/dev/null | grep -iE "license|pro|premium|trial|purchase|subscri"
# Returns keys like:
#   License.hasLicense = 0
#   License.expiryDate = 2024-01-01
#   proUnlocked = 0
#   trialStartDate = 2024-06-01
```

**Methodology:**

Simplest crack type. License state stored in standard `NSUserDefaults`.

```bash
#!/bin/bash
BUNDLE_ID="com.example.bundle"
WHOAMI=$(logname 2>/dev/null || echo "$SUDO_USER" || stat -f%Su /dev/console)

# Read existing keys first
su - "$WHOAMI" -c "defaults read $BUNDLE_ID" 2>/dev/null

# Inject license flags
su - "$WHOAMI" -c "defaults write $BUNDLE_ID 'License.hasLicense' -bool true"
su - "$WHOAMI" -c "defaults write $BUNDLE_ID 'License.expiryDate' -string '2099-01-01'"
su - "$WHOAMI" -c "defaults write $BUNDLE_ID 'License.type' -string 'lifetime'"
su - "$WHOAMI" -c "defaults write $BUNDLE_ID 'proUnlocked' -bool true"
```

**Trial extension variant:**

```bash
# Set trial start to 100 years ago, expiry to 100 years from now
su - "$WHOAMI" -c "defaults write $BUNDLE_ID 'trialStartDate' -date '1926-01-01T00:00:00Z'"
su - "$WHOAMI" -c "defaults write $BUNDLE_ID 'trialExpiryDate' -date '2126-01-01T00:00:00Z'"
su - "$WHOAMI" -c "defaults write $BUNDLE_ID 'trialDaysRemaining' -int 36500"
su - "$WHOAMI" -c "defaults write $BUNDLE_ID 'firstLaunch' -bool false"
```

**Real-world evidence:**
- **Wallspace 1.5.1** — `trial_conversion` key in UserDefaults via `KVKStore` class | `defaults write com.wallspace.pro.Wallspace trial_conversion -bool true` bypasses trial check | Companion to Type 3 StoreKit Patch

**Common trial keys across apps:**

```
trialStartDate, trialExpiry, trialExpiryDate, trialDaysRemaining,
firstLaunch, installDate, launchCount, trialUsed, trialActive,
hasTrial, isTrial, trialEndDate, evaluationEnd, demoExpiry,
freeTrialUsed, trialPeriodEnd, daysLeft
```

**Pitfalls:**
- `defaults write` MUST run as the actual user, not root — use `su - "$WHOAMI"` in postinstall
- Some apps store dates as epoch timestamps, not date objects — check with `defaults read` first
- Multiple keys may need to be set — trial + license + pro flags
- App may validate the date server-side → hosts block also needed

---

#### Type 10: Cache File (`cache_file`)

**Detection fingerprint:**
```
find ~/Library -path "*com.example.bundle*" -name "*.plist" -o -name "*.json" 2>/dev/null
# Returns files like:
#   ~/Library/Application Support/AppName/license.json
#   ~/Library/Caches/com.example.bundle/license.plist
#   ~/Library/Preferences/com.example.bundle.license.plist
```

**Methodology:**

Some apps read license state from a dedicated cache file (JSON or plist) in Application Support or Caches.

```bash
#!/bin/bash
BUNDLE_ID="com.example.bundle"
WHOAMI=$(logname 2>/dev/null || echo "$SUDO_USER" || stat -f%Su /dev/console)

# JSON cache file
LICENSE_DIR="$HOME/Library/Application Support/AppName"
mkdir -p "$LICENSE_DIR"
cat > "$LICENSE_DIR/license.json" << 'EOF'
{
  "hasLicense": true,
  "type": "lifetime",
  "expiry": "2099-01-01",
  "email": "user@example.com",
  "plan": "pro",
  "features": ["all"]
}
EOF

# Binary plist cache file
su - "$WHOAMI" -c "defaults write $HOME/Library/Application\ Support/AppName/license.plist hasLicense -bool true"
su - "$WHOAMI" -c "defaults write $HOME/Library/Application\ Support/AppName/license.plist expiry -string '2099-01-01'"

# Lock immutable
chflags uchg "$LICENSE_DIR/license.json"
```

**Real-world evidence:**
- Generic technique — observed in apps that store license state in `~/Library/Application Support/<AppName>/` or `~/Library/Caches/<BundleID>/` as JSON/plist files | Not tied to any single analysis | Methodology: run app once → locate cache file with `find ~/Library -path "*BundleID*" ( -name "*.plist" -o -name "*.json" )` → inject fake license data → `chflags uchg` to prevent overwrite

**Pitfalls:**
- Cache paths are app-specific — find them by running the app once, then searching
- Some apps use a hash of the machine ID in the filename — harder to pre-generate
- App may overwrite cache on launch → `chflags uchg` needed
- Binary plist vs JSON — check existing file format; use matching format for injection

---

#### Type 11: Activation Tool (`activation_tool`) ⚠️ THEORETICAL ONLY

**Detection fingerprint:**
```
Separate file alongside .dmg:
  AppName Activator.tool      ← OR: AppName Activator.command
  AppName Patcher.tool
  AppName Crack.tool

App may require:
  Manual activation step (enter serial, run tool, reboot)
  Hardware ID-based activation
  Phone-home activation server
```

**Methodology:**

This crack type is **theoretical** — zero analyzed examples exist in the CRACKAPPS dataset. It is included for taxonomy completeness.

Hypothesized workflow:
1. The `.tool`/`.command` script performs some post-install activation
2. May patch the binary, inject a license file, or register with a license server
3. User must run the tool manually after install — it is NOT automatic

**Real-world evidence:**
- **None.** The one candidate (Adobe Illustrator) was a 5.4GB corrupt file (all zeros). Not analyzable.

**Pitfalls:**
- No real-world examples to validate methodology
- `.tool`/`.command` files are opaque — they could contain malware
- Manual step requirement = user friction, not suitable for automated `.pkg` packaging

---

### Phase 3: Design postinstall

Postinstall runs as root after `.pkg` install. Must handle **all 11 crack types**.

#### 3a. Universal postinstall skeleton

```bash
#!/bin/bash
set -e
APP_NAME="AppName"
BUNDLE_ID="com.example.bundle"
WHOAMI=$(logname 2>/dev/null || echo "$SUDO_USER" || stat -f%Su /dev/console)
CRACK_TYPE="revenuecat_patch"  # Set from analysis

# ─── 1. BLOCK API HOSTS ───
BLOCK_HOSTS=("api.revenuecat.com" "subscriptions-api.superwall.com")
for host in "${BLOCK_HOSTS[@]}"; do
    grep -q "0.0.0.0 $host" /etc/hosts || echo "0.0.0.0 $host" >> /etc/hosts
done
dscacheutil -flushcache 2>/dev/null || true
killall -HUP mDNSResponder 2>/dev/null || true

# ─── 2. CRACK TYPE DISPATCH ───
case "$CRACK_TYPE" in
    revenuecat_patch)     source ./inject_revenuecat.sh ;;
    userdefaults)         source ./inject_userdefaults.sh ;;
    cache_file)           source ./inject_cache_file.sh ;;
    tnt_gatekeeper)       source ./inject_tnt_gatekeeper.sh ;;
    ediso_binary_patch)   source ./inject_ediso_binary.sh ;;
    ediso_storekit_patch) source ./inject_ediso_storekit.sh ;;
    hopper_injection)     source ./inject_hopper.sh ;;
    patcher_keygen)       source ./inject_patcher_keygen.sh ;;
    license_server_block) source ./inject_license_block.sh ;;
    tauri_js_patch)       source ./inject_tauri_js.sh ;;
    *) echo "Unknown crack type: $CRACK_TYPE"; exit 1 ;;
esac

# ─── 3. RE-SIGN ───
codesign --remove-signature "/Applications/$APP_NAME.app" 2>/dev/null || true
xattr -cr "/Applications/$APP_NAME.app"
codesign --force --deep --sign - "/Applications/$APP_NAME.app"
```

#### 3b. RevenueCat injection (preserved from existing skill)

```python
# RevenueCat stores license as binary plist containing JSON blob
# Path: ~/Library/Containers/BUNDLE_ID/Data/Library/Preferences/com.revenuecat.user_defaults.plist
# The "purchaserInfo" key contains a binary-encoded JSON string

info = {
    'schema_version':'3','first_seen':'...','original_app_user_id':UID,
    'subscriber':{
        'entitlements':{'pro':{
            'product_identifier':'app_pro_yearly',
            'expires_date':'2099-01-01T00:00:00Z',
            'is_sandbox':False,'ownership_type':'PURCHASED',
            'store':'APP_STORE','is_active':True,'will_renew':True,
        }},
        'subscriptions':{...},
        'non_subscriptions':{},
    },
}

json_bytes = json.dumps(info).encode('utf-8')
data_blob = plistlib.dumps(json_bytes, fmt=plistlib.FMT_BINARY)

prefs = {
    'com.revenuecat.userdefaults.appUserID.new': UID,
    f'com.revenuecat.userdefaults.purchaserInfo.{UID}': data_blob,
    f'com.revenuecat.userdefaults.purchaserInfoLastUpdated.{UID}': datetime.now(),
}

with open(P,'wb') as f: plistlib.dump(prefs, f)
subprocess.run(['chflags','uchg',str(P)])  # Lock immutable
```

#### 3c. UserDefaults injection (preserved from existing skill)

```bash
# Read existing keys first:
defaults read com.example.bundle 2>/dev/null

# Inject:
defaults write com.example.bundle "License.hasLicense" -bool true
defaults write com.example.bundle "License.expiryDate" -string "2099-01-01"
defaults write com.example.bundle "License.type" -string "lifetime"
```

#### 3d. Cache file injection (preserved from existing skill)

```bash
# Some apps read license from disk:
mkdir -p "$HOME/Library/Application Support/AppName"
echo '{"hasLicense":true,"type":"lifetime","expiry":"2099-01-01"}' \
  > "$HOME/Library/Application Support/AppName/license.json"
```

#### 3e. Trial extension injection (new)

```bash
# Set trial to 100-year window
su - "$WHOAMI" -c "defaults write $BUNDLE_ID 'trialStartDate' -date '1926-01-01T00:00:00Z'"
su - "$WHOAMI" -c "defaults write $BUNDLE_ID 'trialExpiryDate' -date '2126-01-01T00:00:00Z'"
su - "$WHOAMI" -c "defaults write $BUNDLE_ID 'trialDaysRemaining' -int 36500"

# Common trial keys to try:
# trialStartDate, trialExpiry, trialExpiryDate, trialDaysRemaining,
# firstLaunch, installDate, launchCount, trialUsed, trialActive,
# hasTrial, isTrial, trialEndDate, evaluationEnd, demoExpiry
```

#### 3f. Serial/license key injection (new)

```bash
# Serial injection via defaults
su - "$WHOAMI" -c "defaults write $BUNDLE_ID 'LicenseKey' -string '$SERIAL'"
su - "$WHOAMI" -c "defaults write $BUNDLE_ID 'LicenseEmail' -string 'user@example.com'"
su - "$WHOAMI" -c "defaults write $BUNDLE_ID 'LicenseName' -string 'Licensed User'"

# Plist file injection (for apps using custom plist)
PLIST="$HOME/Library/Application Support/$APP_NAME/license.plist"
plutil -create xml1 "$PLIST" 2>/dev/null || true
plutil -replace hasLicense -bool true "$PLIST"
plutil -replace type -string "lifetime" "$PLIST"
plutil -replace email -string "user@example.com" "$PLIST"

# Common license key names:
# LicenseKey, SerialNumber, RegistrationCode, ActivationKey,
# LicenseEmail, LicenseName, LicenseCode, ProductKey
```

### Phase 4: Build builder script

```bash
#!/bin/bash
# build_pkg_dmg.sh — Builds .pkg + wraps in .dmg
# Takes app from /Applications/AppName.app (or mounts a .dmg)
# Output: AppName_VERSION_Cracked.dmg

# Steps:
# 1. Find source app (DMG mount or /Applications)
# 2. Copy to temp workspace
# 3. Strip signature
# 4. Optionally inject cache files into app bundle Resources/
# 5. Re-sign ad-hoc
# 6. Copy postinstall.sh → scripts_dir/postinstall (chmod +x)
# 7. pkgbuild --root root/ --install-location / --scripts scripts/ --identifier com.X --version X output.pkg
# 8. hdiutil create -volname "AppName Pro" -srcfolder pkg_dmg_workspace/ -ov -format UDZO output.dmg
# 9. Cleanup temp
```

### Phase 5: Execute on Mac

```bash
# 1. Upload scripts
sshpass -p 'PASS' scp build_pkg_dmg.sh postinstall.sh user@mac:~/Desktop/

# 2. Build
sshpass -p 'PASS' ssh user@mac "bash ~/Desktop/build_pkg_dmg.sh '' ~/Desktop"

# 3. Verify
sshpass -p 'PASS' ssh user@mac "hdiutil attach ~/Desktop/AppName_Cracked.dmg -mountpoint /tmp/v -nobrowse; ls /tmp/v; hdiutil detach /tmp/v -quiet"

# 4. Pull DMG
sshpass -p 'PASS' scp user@mac:~/Desktop/AppName_Cracked.dmg ./output/
```

## Windows Analysis Guide

All pre-Mac analysis runs on Windows:

```bash
# Extract DMG with 7-Zip (⚠️ rename brackets FIRST)
"C:\Program Files\7-Zip\7z.exe" x "file.dmg" -o"output/" -y
"C:\Program Files\7-Zip\7z.exe" l "file.dmg" 2>nul

# Check hex header (detect all-zeros corruption)
xxd -l 1024 "file.dmg"

# Python string extraction (strings.exe not on Windows PATH)
python3 -c "
import re
data = open('binary','rb').read()
text = data.decode('latin-1', errors='ignore')
for m in re.finditer(r'[\x20-\x7e]{6,}', text):
    s = m.group()
    if re.search(r'(?i)license|activate|trial|pro|premium|validate|purchase|subscript|receipt|tnt|ediso|cryptic', s):
        print(s)
"
```

## Pitfalls

### Existing (preserved)

1. **RevenueCat plist overwritten**: App rewrites plist on launch → use `chflags uchg` (immutable system flag). `chmod 444` NOT enough.
2. **Gatekeeper blocks app**: Always `xattr -cr` + `codesign --force --deep --sign -` after modification.
3. **postinstall runs as root**: Use `su - "$WHOAMI" -c "..."` for any UserDefaults/cache writes that must go to the user's home, not root's.
4. **pkgbuild permission warnings**: The "Permission denied" warnings during pkgbuild are harmless — it's the tool trying to read symlinks inside the app bundle.
5. **Multiple license layers**: Check ALL frameworks (RevenueCat + Superwall + AppsFlyer). Each needs its own fix.
6. **Cached data persists**: If testing on same Mac, delete the old plist/cache first: `rm -rf ~/Library/Containers/BUNDLE_ID/Data/Library/Preferences/com.revenuecat.*`
7. **wrong user**: Script jalan as root → `whoami` returns root. Store real user early with `WHOAMI=$(logname 2>/dev/null || echo "$SUDO_USER" || stat -f%Su /dev/console)`.

### New (TNT/EDiSO/Hopper/Patcher)

8. **TNT .nfo authenticity**: The PGP-signed `.nfo` is the authenticity proof. TNT releases without a valid PGP signature = fake/malware. Verify with `Extra/rhash -r Extra/tnt.sfv --sha256 --skip-ok -c`.
9. **TNT Gatekeeper**: Even after install, macOS may block the app. User must run `xattr -cr` or disable Gatekeeper. The `Help.txt` file in the DMG explains this.
10. **EDiSO protection labels**: `AES+ECC+SHA+B64+CTM` describes obfuscation, not a crypto challenge. Don't try to decrypt — patch AROUND the check in the binary.
11. **EDiSO binary size trap**: Tauri/Electron apps have 100MB+ binaries with NO license strings. Don't waste time binary-analyzing — the license logic is in JavaScript.
12. **Hopper dylib crash**: If `macked.app.dylib` is the wrong architecture (arm64 on x86_64 machine or vice versa), the dylib can't load → app crashes. Verify arch with `lipo -info`.
13. **Hopper SIP conflict**: `DYLD_INSERT_LIBRARIES` is blocked by SIP on newer macOS. The app must be re-signed with `com.apple.security.cs.disable-library-validation` entitlement.
14. **Patcher arch mismatch**: `patchfiles/arm64/` contents loaded on x86_64 machine → crash. The Patch script should auto-detect arch; if not, verify before running.
15. **Patcher V8 snapshot version**: `index.jsc` is V8 compiled JavaScript. The V8 snapshot format version must match the app's embedded V8 version. Mismatch = crash on startup.
16. **Adobe Illustrator / corrupt DMGs**: Some DMGs are corrupt (all zeros, truncated). Check with `xxd -l 1024 file.dmg` — if all zeros, the file is unrecoverable. Mark as UNANALYZABLE.
17. **7-Zip bracket bug**: 7-Zip on Windows crashes on filenames containing `[` or `]`. Rename to `_` before extraction.
18. **Sparkle auto-update**: If `SUFeedURL` exists in Info.plist, the app will auto-update and overwrite the crack. Remove or block the Sparkle feed URL.

## Verification

After install, verify per crack type:

### All types
```bash
# Check hosts block
grep "0.0.0.0" /etc/hosts

# Launch app and visually confirm
open /Applications/AppName.app
# Check: no trial popup, no paywall, Pro badge visible
```

### RevenueCat
```bash
# Check plist immutability
ls -lO ~/Library/Containers/com.example/Data/Library/Preferences/com.revenuecat.user_defaults.plist
# Should show "uchg" flag
```

### UserDefaults
```bash
# Check injected values
defaults read com.example.bundle License.hasLicense
```

### Cache File
```bash
# Check file exists + content
cat ~/Library/Application\ Support/AppName/license.json
```

### TNT Gatekeeper
```bash
# Verify checksums
cd "/Volumes/AppName/Extra"
./rhash -r tnt.sfv --sha256 --skip-ok -c
```

### Patcher + Keygen
```bash
# Verify license files generated
ls -la ~/.appname/license.lic ~/.appname/license.key

# Verify app launches without crash
open /Applications/AppName.app
```

## Tools Required

- `sshpass` (password-based SSH for automation)
- `pkgbuild` (built into macOS — no install needed)
- `hdiutil` (built into macOS)
- `codesign` (built into macOS)
- `plistlib` (built into Python 3 on macOS)
- `PlistBuddy` at `/usr/libexec/PlistBuddy` (built into macOS)
- `xar` (optional — for inspecting `.pkg` internals)
- `pkgutil` (optional — for expanding `.pkg` files)
- `7z` (Windows: 7-Zip for DMG extraction)
- `python3` (Windows: string extraction, binary analysis)
- `lipo` (macOS: check binary architecture)
- `nm` / `otool` (macOS: symbol discovery for binary patching)

## References

- [RevenueCat iOS SDK — PurchaserInfo format](https://github.com/RevenueCat/purchases-ios)
- [Apple pkgbuild manual](https://www.unix.com/man-page/osx/1/pkgbuild/)
- [Creating self-contained PKG installers](https://derflounder.wordpress.com/2014/05/24/packaging-with-pkgbuild-training-video/)
- **[CRACK_SITES.md](references/CRACK_SITES.md)** — Canonical list of 13 Mac crack websites + sourcing workflow + verification checklist
- **[REVENUECAT.md](references/REVENUECAT.md)** — Double-encoding plist internals + full `purchaserInfo` JSON schema + `chflags uchg` immutability lock
- **[TNT.md](references/TNT.md)** — TNT scene methodology: DMG structure, Gatekeeper bypass, binary patching (Swift name-mangled + RLM framework), PGP signing key, Easter eggs
- **[SCENE_RELEASES.md](references/SCENE_RELEASES.md)** — TNT vs EDiSO vs appstorrent taxonomy: DMG packaging patterns, .nfo structure comparison, protection label conventions
- **[BINARY_PATCHING.md](references/BINARY_PATCHING.md)** — Hopper dylib injection architecture, TNT binary patching, EDiSO binary patching, ad-hoc codesign + entitlements
- **[TAURI_ELECTRON.md](references/TAURI_ELECTRON.md)** — Tauri JS patch (Cap case study), Electron ASAR/unpacked bundle patching (Plasticity case study), keygen integration, V8 compiled JSC replacement

## Companion Files

### Templates (customize per app)
```
templates/postinstall.sh                     ← Universal postinstall (root, auto-dispatch)
templates/postinstall_trial_extension.sh     ← Trial date reset via UserDefaults + plist
templates/postinstall_serial.sh              ← Serial/license key injection
templates/build_pkg_dmg.sh                   ← Builder: source app → .pkg → .dmg
templates/classify_crack_type.sh             ← Auto-detect crack type from .app structure
```

### References (documentation)
```
references/CRACK_SITES.md                    ← 13-site list with status
references/REVENUECAT.md                     ← Double-encoding plist internals
references/TNT.md                            ← TNT scene methodology
references/SCENE_RELEASES.md                 ← Scene taxonomy (TNT/EDiSO/appstorrent)
references/BINARY_PATCHING.md                ← Binary-level crack methodology
references/TAURI_ELECTRON.md                 ← JavaScript-level crack methodology
```

### Scripts (utility)
```
scripts/analyze_app.sh                       ← Phase 1 analysis: detect crack type from .app
scripts/extract_dmg.sh                       ← Two-phase DMG extraction (Windows + Mac)
```