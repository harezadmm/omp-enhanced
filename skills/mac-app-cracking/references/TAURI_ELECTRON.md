# Tauri & Electron Cracking Reference

> Cracking Tauri and Electron-based macOS apps — JavaScript-level patching, V8 snapshot replacement, and keygen integration.

---

## Overview

Tauri and Electron apps bundle a **Chromium/WebKit WebView** with JavaScript frontend logic. The native binary is just the runtime — all application logic (including license checks) lives in JavaScript. This makes the crack fundamentally different from native app cracking:

- **Native apps**: Patch the binary's license validation function
- **Tauri/Electron apps**: Patch the JavaScript that checks the license

---

## Case Study 1: Cap (Tauri) — JS-Level Crack

### App Metadata
- **App**: Cap 0.5.9
- **Bundle ID**: `so.cap.desktop`
- **Scene**: EDiSO
- **Framework**: Tauri (Rust backend + WebView frontend)
- **Binary size**: 135.9 MB
- **Architecture**: Universal 2 (Intel + ARM)

### Detection: The "Zero License Strings" Tell

The single biggest detection signal for a Tauri app is the **binary size trap**:

```bash
# Binary is HUGE (100MB+) but has ZERO license-related strings
python3 -c "
import re
data = open('Cap.app/Contents/MacOS/Cap','rb').read()
text = data.decode('latin-1', errors='ignore')
matches = [m.group() for m in re.finditer(r'[\x20-\x7e]{6,}', text)
           if re.search(r'(?i)license|activate|trial|pro|premium|purchase', m.group())]
print(f'License strings found: {len(matches)}')
# Output: License strings found: 0
"
```

**Why?** The 135.9MB binary is Tauri's Rust-based WebView runtime — it contains the window management, IPC bridge, and system tray logic. All license checks are in the JavaScript that runs inside the WebView. The native binary has NO idea what "license" means.

### Tauri App Structure

```
Cap.app/
└── Contents/
    ├── MacOS/
    │   └── Cap                    ← 135.9MB Tauri runtime (DO NOT WASTE TIME HERE)
    ├── Resources/
    │   ├── app/                   ← WebView frontend (HTML/JS/CSS) — YOUR TARGET
    │   │   ├── index.html
    │   │   ├── assets/
    │   │   │   ├── index-abc123.js    ← Main bundle (minified)
    │   │   │   ├── vendor-def456.js   ← Third-party libraries
    │   │   │   └── ...
    │   │   └── ...
    │   ├── app.asar               ← ALTERNATIVE: packed ASAR archive
    │   └── _nupkg/                ← ALTERNATIVE: Squirrel update packages
    └── Info.plist
```

### Method

1. **Locate the JS bundle**:
```bash
# Check if unpacked
ls Cap.app/Contents/Resources/app/

# If app.asar exists instead, extract it
npx asar extract Cap.app/Contents/Resources/app.asar Cap.app/Contents/Resources/app/
```

2. **Find the license logic in JS**:
```bash
grep -r "license\|purchase\|premium\|pro\|activate\|trial" Cap.app/Contents/Resources/app/ | head -20
```

3. **Patch the JS**: Common patterns in Tauri apps:
   - Replace `isSubscribed: false` → `isSubscribed: true`
   - Replace `plan: "free"` → `plan: "pro"`
   - Replace `trialEnds: Date` → `trialEnds: null`
   - NOP out the license validation API call
   - Change `features: { pro: false }` → `features: { pro: true }`

4. **Re-pack if ASAR**:
```bash
npx asar pack Cap.app/Contents/Resources/app/ Cap.app/Contents/Resources/app.asar
```

5. **Re-sign**:
```bash
codesign --force --deep --sign - /Applications/Cap.app
xattr -cr /Applications/Cap.app
```

### Pitfalls

| Pitfall | Why it happens | Fix |
|---|---|---|
| **Binary size trap** | 100MB+ binary tricks you into thinking it's the target — it's just Tauri runtime | Check `Resources/` first; binary is irrelevant |
| **Minified JS** | `index-abc123.js` is 2MB of single-line minified code | Use `prettier --write` to format, then patch, then optionally re-minify |
| **ASAR packaging** | `app.asar` is a single archive file, not a directory | `npx asar extract` before patching, `npx asar pack` after |
| **Source maps** | `.js.map` files reveal original variable names | Check for `.map` files — they make patching MUCH easier |
| **Tauri v1 vs v2** | Different Resources layout between versions | v1: `app/` or `app.asar`; exact path varies |

---

## Case Study 2: Plasticity (Electron) — V8 JSC Replacement + Keygen

### App Metadata
- **App**: Plasticity 26.1.3
- **Scene**: appstorrent
- **Framework**: Electron (Chromium + Node.js)
- **Protection**: V8 compiled JavaScript (`.jsc`) + native Node addon (`pk.node`)
- **Architecture**: Universal 2 (separate payloads per arch)

### Detection

```bash
# appstorrent release structure
ls Plasticity\ v26.1.3\ macOS/
# 0. Инструкция (instruction).html
# 1. Installer/          ← Contains the ISO + .app
# 2. Patcher/            ← Crack tools
#    ├── Patch            ← Bash patch script (220 lines)
#    ├── keygen           ← Swift Universal Binary
#    └── patchfiles/
#        ├── arm64/
#        │   ├── pk.node      ← Patched Node addon (17.8MB)
#        │   └── index.jsc    ← Patched V8 compiled JS (11.4MB)
#        └── x86_64/
#            ├── pk.node      ← Patched Node addon (20.1MB)
#            └── index.jsc    ← Patched V8 compiled JS (11.4MB)
```

### How the Plasticity Crack Works

#### Layer 1: pk.node Replacement

`pk.node` is a **native Node.js addon** (compiled C++ → `.node` binary) that handles license validation. The patched version bypasses all hardware-ID checks, signature verification, and online validation.

**Architecture-specific swap:**
```bash
# The Patch script auto-detects arch from the main Mach-O
file Plasticity.app/Contents/MacOS/Plasticity
# Mach-O universal binary with 2 architectures: [x86_64] [arm64]

# Swaps the correct pk.node for the detected arch
cp patchfiles/arm64/pk.node Plasticity.app/.../pk.node    # On Apple Silicon
cp patchfiles/x86_64/pk.node Plasticity.app/.../pk.node   # On Intel
```

Both the stock and patched `pk.node` files have SHA-256 hashes embedded in the Patch script for verification — the script verifies the stock files match expected hashes BEFORE patching, and verifies the patched files match AFTER swapping.

#### Layer 2: index.jsc Replacement

`.jsc` files are **V8 compiled JavaScript** — not human-readable, not debuggable, and architecture-specific. The V8 snapshot format is tied to the V8 version bundled with Electron, so `.jsc` files from one Electron version won't work with another.

**This is why the crack ships TWO `.jsc` files per architecture:**
- `patchfiles/arm64/index.jsc` — compiled for V8 on ARM64
- `patchfiles/x86_64/index.jsc` — compiled for V8 on x86_64

The stock `index.jsc` contains the compiled license validation logic. The patched version has the license check replaced with a bypass.

#### Layer 3: Keygen (Swift CryptoKit)

After the binary swap, the **keygen** generates a valid machine-bound license:

```bash
./keygen ~/.plasticity
```

**Keygen internals:**
- **Language**: Swift (compiled as Universal Binary for ARM64 + x86_64)
- **Algorithm**: 
  1. **Fingerprint collection**: Gathers machine identifiers:
     - `IOPlatformExpertDevice` (hardware UUID)
     - `sysctl hw.machine` (Mac model identifier)
     - `sysctl hw.ncpu` (CPU core count)
     - `sysctl hw.memsize` (RAM size)
     - `sysctl kern.boottime` (boot timestamp — not used for uniqueness, just for metadata)
     - `NSHomeDirectory()` (user home path)
  2. **Key generation**: `Curve25519.Signing.PrivateKey` → ED25519 signature
  3. **Encryption**: `SymmetricKey` + `AES.GCM.seal()` → encrypt the license payload
  4. **Output**: Two files:
     - `~/.plasticity/license.lic` — AES-256-GCM encrypted license data
     - `~/.plasticity/license.key` — PEM-armored ED25519 public key

**Labels found in keygen binary:**
- `aes-256-gcm+ed25519` — the encryption + signing scheme
- PEM header/footer — the key file is PEM-armored
- `Account UUID: 6b653527-980a-44be-91dd-9f3d33f13a2e` — hardcoded account identifier

#### Layer 4: Auto-Update Disable

```bash
# Patcher toggles checkForUpdates in settings.json
# Before: { "General": { "checkForUpdates": true } }
# After:  { "General": { "checkForUpdates": false } }
```

This prevents Electron's auto-updater from silently replacing the patched `pk.node` and `index.jsc`.

#### Layer 5: Codesign

```bash
# Ad-hoc codesign with entitlements for JIT + unsigned native addons
codesign --remove-signature pk.node
codesign --force -s - pk.node
codesign --force --deep --options runtime --entitlements entitlements.plist -s - Plasticity.app
```

### The Patch Script Architecture

The Plasticity Patch script (220 lines of Bash) has a clear architecture:

```
Lines 1-20:   Header, color scheme, help text, action dispatch (install/restore)
Lines 21-40:  SHA-256 hashes — 6 per arch (stock+patched for pk.node and index.jsc each)
Lines 41-60:  sha() helper, preflight checks, xattr cleanup
Lines 61-80:  App validation, file existence checks, architecture detection from Mach-O
Lines 81-100: resign() function with entitlements plist generation
Lines 101-120: set_updates() function to toggle checkForUpdates in settings.json
Lines 121-160: install action — backup, stock hash verify, file swap, payload verify, codesign
Lines 161-220: keygen execution, settings update, completion message, restore action
```

**Error handling**: Every step has a `trap on_err ERR` handler that provides bilingual (English/Russian) fix instructions for the specific failure.

### Why Plasticity Doesn't Use UserDefaults

Plasticity's license lives in `~/.plasticity/`, NOT in `~/Library/Preferences/`. This is common for Electron apps — they maintain their own data directory rather than using macOS UserDefaults.

---

## Keygen Algorithm Reference (CryptoKit)

```swift
// Pseudocode of Plasticity-style keygen (Swift CryptoKit)
import CryptoKit
import IOKit

// 1. Collect machine fingerprint
let platformExpert = IOServiceGetMatchingService(...)
let machineID = IORegistryEntryCreateCFProperty(platformExpert, "IOPlatformUUID")
let machineModel = sysctl("hw.machine")
let cpuCount = sysctl("hw.ncpu")
let memorySize = sysctl("hw.memsize")

// 2. Create fingerprint string
let fingerprint = "\(machineID)|\(machinemodel)|\(cpuCount)|\(memorySize)"

// 3. Sign with ED25519 private key (embedded in keygen)
let privateKey = Curve25519.Signing.PrivateKey()
let signature = try privateKey.signature(for: Data(fingerprint.utf8))

// 4. Create license payload
let payload = [
    "machine": fingerprint,
    "signature": signature.rawRepresentation.base64EncodedString(),
    "timestamp": Int(Date().timeIntervalSince1970),
    "features": ["studio", "offline", "unlimited"]
] as [String : Any]

// 5. Encrypt with AES-256-GCM
let symmetricKey = SymmetricKey(size: .bits256)
let sealedBox = try AES.GCM.seal(JSONEncoder().encode(payload), using: symmetricKey)

// 6. Write output files
write(sealedBox.combined!, to: "~/.plasticity/license.lic")
write(symmetricKey.rawRepresentation, to: "~/.plasticity/license.key")
```

---

## V8 Snapshot Format Warning

**`.jsc` files are NOT portable across V8 versions.** The V8 snapshot format changes between major versions. This means:

1. A `.jsc` compiled for Electron 28 (V8 12.0) will NOT work on Electron 30 (V8 12.4)
2. You MUST match the Electron version exactly — the Patch script verifies SHA-256 hashes of stock files to ensure version match before patching
3. Cross-architecture `.jsc` files are also incompatible (ARM64 `.jsc` ≠ x86_64 `.jsc`)
4. There is no public tool to decompile `.jsc` back to JavaScript — you must patch the original source and recompile

---

## Generic Tauri/Electron Crack Flow

```
1. Identify the JS bundle location
   ├── Tauri:  Contents/Resources/app/ or app.asar
   └── Electron: Contents/Resources/app/ or app.asar

2. Extract if packed (ASAR)
   └── npx asar extract app.asar app/

3. Search for license logic
   └── grep -r "license\|purchase\|premium\|activate\|trial\|validate"

4. Identify the pattern
   ├── isSubscribed / isPro / hasLicense variable
   ├── Feature flag check
   ├── Trial expiry date check
   ├── API call to license server
   └── V8 compiled .jsc (Electron only)

5. Patch
   ├── JS edit: change variable, delete condition, force true
   ├── ASAR re-pack: npx asar pack app/ app.asar
   └── JSC swap (Electron only): replace with pre-patched .jsc + pk.node

6. Re-sign
   └── codesign --force --deep --sign - AppName.app
   └── xattr -cr AppName.app
```

---

## Quick Reference

| Check | Tauri | Electron |
|---|---|---|
| Binary size | 100MB+ (Rust WebView runtime) | 50-80MB (Chromium + Node.js) |
| JS location | `Contents/Resources/app/` or `.asar` | `Contents/Resources/app/` or `.asar` |
| Packed format | `.asar` (npm asar) | `.asar` (npm asar) |
| Compiled JS | Rare | `.jsc` (V8 snapshot) — **not portable** |
| Native addons | Rare (Rust via Tauri API) | `.node` files possible (C++ addons) |
| License storage | Varies (JS logic) | Varies (JS logic or native addon) |
| Keygen needed? | Usually not (just patch JS) | Sometimes (if native addon validates license file) |