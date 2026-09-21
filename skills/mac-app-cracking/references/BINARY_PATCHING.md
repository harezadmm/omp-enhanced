# Binary Patching Reference

> Three distinct binary patching techniques used across macOS crack scenes: Hopper dylib injection, TNT Swift/RLM patching, and EDiSO hex-edit patching.

---

## Technique A: Hopper Dylib Injection

### Architecture

The `macked.app.dylib` is **Hopper Disassembler's own runtime library** (`(c) 2014 Cryptic Apps SARL`), not a custom injection framework. It provides Hopper's runtime code analysis capabilities. When injected into another app, it can manipulate the target process's memory at runtime.

### How It Works

```
App Launch
  ↓
dyld loads macked.app.dylib (via DYLD_INSERT_LIBRARIES or LC_LOAD_DYLIB)
  ↓
dylib constructor runs (_init / +load)
  ↓
locates the license validation function in host binary
  ↓
calls mach_vm_protect() to make code page writable
  ↓
patches the validation function in-memory (live patch)
  ↓
bypasses codesign hash check (cdhashes bypass)
  ↓
App continues execution — license validated as "success"
```

### Dylib String Analysis

```
$ strings macked.app.dylib | head -20
(c) 2014 - Cryptic Apps SARL        ← Copyright — confirms Hopper origin
mach_vm_protect                      ← Makes read-only pages writable
vm_protect                           ← Fallback for older macOS
cdhashes                             ← Code signature hash verification
com.apple.security.cs                ← Codesign framework identifier
_dyld_register_func_for_add_image    ← Image load callback
_dyld_register_func_for_remove_image ← Image unload callback
```

### Detection in the Wild

- **Raycast** (productivity launcher): `macked.app.dylib` in `Contents/Frameworks/` + `_MASReceipt/` directory
- **Sip** (color picker): Same pattern — dylib + MAS receipt bypass

### How the MAS Receipt Bypass Works

The `_MASReceipt/` directory contains a fake Mac App Store receipt. Many apps check for the presence of a valid MAS receipt to determine if they were purchased. The Hopper crack:
1. Places a valid (but not user-specific) receipt in `_MASReceipt/`
2. The dylib hooks `SecCodeCheckValidity` to bypass signature verification of the fake receipt
3. The app sees the receipt, validates "successfully" (bypassed), and unlocks

### Pitfalls

- **SIP must be disabled or partially disabled** — `mach_vm_protect` on code pages requires `csrutil disable` or `csrutil enable --without debug` on modern macOS
- **Architecture mismatch**: The dylib must match the host app's architecture (arm64 dylib won't load into x86_64 process)
- **macOS version**: `mach_vm_protect` behavior changed in macOS 13+; patches that work on Monterey may fail on Ventura/Sonoma/Sequoia

---

## Technique B: TNT Binary Patching

### Approach

TNT patches the compiled binary **directly** at the Mach-O level, not at runtime. The patch is applied during DMG assembly (via hdiutil shadow mount) and the modified binary is what ships in the DMG.

### Swift Name-Mangled Symbol Discovery

Swift uses **name mangling** to encode function signatures into unique symbol names. To find the license validation function:

```bash
# List all global symbols, filter for license-related
nm -gU AppName.app/Contents/MacOS/AppName | grep -iE "license|valid|check|activate|purchase|verify"

# Demangle Swift symbols for readability (Xcode tools required)
nm -gU AppName.app/Contents/MacOS/AppName | xcrun swift-demangle

# Find ALL symbols in a specific module
nm -gU AppName.app/Contents/MacOS/AppName | grep "AppName\." | xcrun swift-demangle
```

**Real ForkLift example:**
```
Raw:  _$s9ForkLift17LicenseValidatorC15checkSignature_6serialSbSS_SStF
Demangled: ForkLift.LicenseValidator.checkSignature(_:serial:) -> Swift.Bool
```

The function `checkSignature(_:serial:)` on `LicenseValidator` returns `Bool`. TNT patches this to always return `true`.

### ARM64 Patch

```asm
; Original (checks serial and returns Bool)
STP  X29, X30, [SP, #-16]!
MOV  X29, SP
... license validation logic ...
LDP  X29, X30, [SP], #16
RET

; Patched (always return true)
MOV  W0, #1       ; W0 = 1 (Swift Bool true)
RET                ; Return immediately
```

**Hex**: `20 00 80 D2  C0 03 5F D6`

### x86_64 Patch

```asm
; Patched (always return true)
MOV  EAX, 1       ; EAX = 1 (Swift Bool true — but x86_64 Swift actually uses AL)
RET               ; Return immediately
```

**Hex**: `B8 01 00 00 00  C3`

### RLM Framework Bypass (SketchUp, Autodesk)

RLM (Reprise License Manager) is a commercial DRM framework. TNT's approach:

1. **Locate RLM functions**: Search for `rlm_` prefixed symbols in the binary
2. **Patch license status check**: `rlm_license_stat()` → always return `RLM_EL_NORMAL` (1)
3. **Patch expiry check**: `rlm_license_exp()` → skip date comparison, always return future date
4. **Patch server check**: Functions that call `rlm_client_connect()` → NOP the call, return cached result
5. **Patch heartbeat**: `rlm_heartbeat()` → NOP (some RLM apps phone home periodically)

### Generic Conditional Jump Bypass

```asm
; ARM64 — B.NE (branch if not equal) → NOP
; Original: 41 00 00 54 (B.NE +0x8)
; Patched:  1F 20 03 D5 (NOP)

; ARM64 — B.EQ (branch if equal) → B (unconditional)
; Original: 40 00 00 54 (B.EQ +0x8)
; Patched:  04 00 00 14 (B +0x10)

; x86_64 — JNE → JMP
; Original: 0F 85 XX XX XX XX (JNE rel32)
; Patched:  E9 XX XX XX XX    (JMP rel32)
```

---

## Technique C: EDiSO Binary Patching

### Approach

EDiSO uses **hex-editing** of the compiled binary rather than runtime injection. The protection label in the `.nfo` (e.g., `AES+ECC+SHA+B64+CTM`) describes the original protection, not the crack.

### Protection Label Decoder

| Component | What it means in the binary | How EDiSO cracks it |
|---|---|---|
| **AES** | License data is AES-encrypted at rest | Patch AROUND the decryption — don't need to decrypt, just change the "is decryption successful?" check |
| **ECC** | Elliptic curve key validation (license file signed with ECC private key) | Patch the signature verification function to always return "valid" |
| **SHA** | Hash checks on license data integrity | Patch the hash comparison — always match |
| **B64** | License key is Base64-encoded | Not cracked — just the transport encoding |
| **CTM** | Custom Transform Method (proprietary obfuscation) | Find the final validation gate and NOP/bypass it |

### Real Example: Alcove (AES+ECC+SHA+B64+CTM)

```bash
# On Mac (for analysis only; patching is on Windows)
strings Alcove.app/Contents/MacOS/Alcove | grep -iE "license|valid|http"

# Typical findings:
# https://api.tryalcove.com/v1/license/validate
# License validation failed
# License is valid until
# Activate License
```

**EDiSO crack method:**
1. Locate the license server URL string in the binary → block via `/etc/hosts` (secondary)
2. Find the function that calls the URL → hex-edit to skip the network call (primary)
3. Find the return-value check after validation → force to return "valid"
4. `NSLocalNetworkUsageDescription` = "license validation" in Info.plist is the tell that this app uses network-based license checks

### EDiSO StoreKit Variant

When the app uses StoreKit instead of a custom license server:

```bash
strings AppName.app/Contents/MacOS/AppName | grep -i "purchaseCompleted\|SKPayment\|SKProduct\|addTransactionObserver"
```

The patch targets:
1. `paymentQueue(_:updatedTransactions:)` — the StoreKit delegate callback — force all transactions to `.purchased` or `.restored`
2. Receipt validation: if the app calls Apple's `verifyReceipt` endpoint, patch BEFORE the network call
3. Sparkle auto-update: remove `SUFeedURL` from Info.plist

---

## Codesign After Patching

Any binary modification invalidates the code signature. The app must be re-signed **ad-hoc** (not with a Developer ID, which would require an Apple Developer account):

```bash
# Remove existing signature
codesign --remove-signature /Applications/AppName.app

# Deep re-sign (handles nested bundles, frameworks, dylibs)
codesign --force --deep --sign - /Applications/AppName.app

# With entitlements (required for some apps)
codesign --force --deep --options runtime \
  --entitlements entitlements.plist \
  -s - /Applications/AppName.app
```

### Standard Entitlements Template (`entitlements.plist`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
```

These three entitlements are **critical** for cracked apps:
- `allow-jit`: Allows JavaScript JIT compilation (needed for Electron/WebView apps)
- `allow-unsigned-executable-memory`: Allows `mach_vm_protect` to mark pages executable
- `disable-library-validation`: Allows loading unsigned dylibs (needed for DYLD_INSERT_LIBRARIES)

### xattr Cleanup

```bash
# Remove quarantine attribute (required after any modification)
xattr -cr /Applications/AppName.app

# Verify quarantine is gone
xattr -l /Applications/AppName.app
# Should return nothing
```

---

## Quick Reference

| Task | Command |
|---|---|
| List Swift symbols | `nm -gU AppName.app/Contents/MacOS/AppName \| xcrun swift-demangle` |
| Find license strings | `strings AppName.app/Contents/MacOS/AppName \| grep -iE "license\|valid\|check"` |
| ARM64 return true | Hex: `20 00 80 D2 C0 03 5F D6` |
| x86_64 return true | Hex: `B8 01 00 00 00 C3` |
| Re-sign ad-hoc | `codesign --force --deep --sign - /Applications/AppName.app` |
| Re-sign with entitlements | `codesign --force --deep --options runtime --entitlements ent.plist -s - /Applications/AppName.app` |
| Clear quarantine | `xattr -cr /Applications/AppName.app` |
| Check binary architecture | `file AppName.app/Contents/MacOS/AppName` |