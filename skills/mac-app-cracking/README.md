# mac-app-cracking 🧰

> **LTX-QUASAR OMP Skill** — Universal Mac app reverse-engineering & self-contained DMG packager

[![Skill Type](https://img.shields.io/badge/OMP-Skill-crimson)](https://github.com/harezadmm/mac-app-cracking)
[![Category](https://img.shields.io/badge/Category-Security-informational)](https://github.com/harezadmm/mac-app-cracking)
[![License](https://img.shields.io/badge/License-Proprietary-red)](https://github.com/harezadmm/mac-app-cracking)
[![Works On](https://img.shields.io/badge/Works%20On-macOS%2014+-blue)](https://github.com/harezadmm/mac-app-cracking)

---

## 🧭 What It Does

Produces **self-contained, double-click-to-install `.dmg`** files for cracked Mac apps. No terminal. No scripts. No manual steps. Recipient mounts the DMG, double-clicks the `.pkg`, enters their password once — and the app is **fully unlocked, permanently**.

```
Source .app → Analyze → Postinstall (block + inject + re-sign) → .pkg → .dmg → DONE
```

## 🛡️ License Types Supported

| Type | Detection | Crack Method |
|---|---|---|
| **RevenueCat** | `RevenueCat_RevenueCat.bundle` | Inject `purchaserInfo` + `chflags uchg` lock |
| **Superwall** | `SuperwallKit_SuperwallKit.bundle` | Block `subscriptions-api.superwall.com` |
| **Custom API** | License server in binary strings | Block in `/etc/hosts` |
| **UserDefaults** | `defaults read \| grep license` | Inject fake values |
| **Cache File** | JSON/plist in `~/Library/App Support/` | Write fake license file |
| **Binary Check** | No network, no cache — logic in binary | `lldb`/Hopper/Ghidra patch |

## 📦 Quick Start

```bash
# 1. Copy the templates
cp templates/postinstall.sh ./
cp templates/build_pkg_dmg.sh ./

# 2. Customize postinstall.sh — change 3 things:
#    • APP_NAME, BUNDLE_ID
#    • BLOCK_HOSTS array (license API domains)
#    • Pick one: use_revenuecat / use_userdefaults / use_cache_file

# 3. Build on Mac (SSH or direct)
bash build_pkg_dmg.sh                    # from /Applications
bash build_pkg_dmg.sh /path/to/app.dmg   # from original DMG

# 4. Output → ~/Desktop/AppName_VERSION_Cracked.dmg
```

## 📁 Skill Structure

```
mac-app-cracking/
├── SKILL.md                     # Full OMP skill definition (9KB)
├── README.md                    # This file
├── templates/
│   ├── build_pkg_dmg.sh         # Builder: source → .pkg → .dmg
│   └── postinstall.sh           # 3 inject methods + API block + re-sign
├── scripts/
│   └── inject_revenuecat.py     # Standalone RevenueCat injector
└── references/
    └── REVENUECAT.md            # RevenueCat plist internals deep dive
```

## 🔪 The Kill Chain

### Phase 1 — SCOUT
Scan the installed app to identify the license mechanism:
```bash
find /Applications/AppName.app -name "RevenueCat*" -o -name "Superwall*"
strings /Applications/AppName.app/Contents/MacOS/AppName | grep -iE "api\.|license|activate"
defaults read com.bundle.id 2>/dev/null | grep -iE "license|pro|trial"
find ~/Library -path "*BundleID*" -name "*.plist" -o -name "*.json"
```

### Phase 2 — ARM
Pick the injection approach based on what SCOUT found:
- **RevenueCat**: UID + `purchaserInfo` JSON blob + `chflags uchg` immutable lock
- **UserDefaults**: `defaults write com.X License.hasLicense -bool true`
- **Cache file**: `mkdir -p ~/Library/Application Support/App && echo '{"hasLicense":true}' > license.json`
- **API block**: `BLOCK_HOSTS=( "api.example.com" "license.example.com" )`

### Phase 3 — STRIKE
`build_pkg_dmg.sh` executes the full pipeline:
1. Copy `.app` → temp workspace
2. Strip code signature (`codesign --remove-signature`)
3. Inject bundled cache files (optional)
4. Ad-hoc re-sign
5. `pkgbuild` with `postinstall` script
6. `hdiutil` create final `.dmg`

### Phase 4 — VERIFY
```bash
# Inspect the .pkg
pkgutil --expand AppName.pkg /tmp/extracted
ls /tmp/extracted/Scripts/postinstall   # must exist

# Test install
grep "0.0.0.0" /etc/hosts               # API blocked
defaults read com.X License.hasLicense  # → 1
ls -lO plist                             # → uchg flag (immutable)
open /Applications/AppName.app           # → No trial popup
```

## 🏆 Battle-Tested

| App | License Type | Complexity | Result |
|---|---|---|---|
| **Linearity Curve 6.10.3** | RevenueCat + Superwall + AppsFlyer (triple) | 🔴 Critical | 598MB DMG, Pro Lifetime |
| **Wallper 1.11.2** | Custom API + UserDefaults cache | 🟢 Simple | 15MB DMG, 99999-day trial |

## 🔑 Key Insights

### RevenueCat plist is NOT plaintext
The `com.revenuecat.user_defaults.plist` stores `purchaserInfo` as a **binary plist containing a JSON blob**. You can't just `defaults write` it — you need Python's `plistlib.dumps(data, fmt=FMT_BINARY)`.

### chmod 444 is NOT enough
RevenueCat's SDK **overwrites the plist even with read-only permissions**. Solution: `chflags uchg` (immutable system flag) — the app cannot modify it even with sandbox entitlements.

### postinstall runs as root
`.pkg` installers run scripts as root. Use `su - "$WHOAMI"` for any writes that must go to the user's home directory (UserDefaults, cache files).

### Triple license attacks
Linearity Curve uses RevenueCat + Superwall + AppsFlyer simultaneously. Block all three:
```
0.0.0.0 api.revenuecat.com
0.0.0.0 api.linearity.io
0.0.0.0 subscriptions-api.superwall.com
0.0.0.0 subscriptions-api.superwall.dev
```

## 🧩 Installation (OMP)

```bash
# Clone into OMP skills directory
git clone https://github.com/harezadmm/mac-app-cracking.git ~/.hermes/skills/mac-app-cracking

# Or just copy any of the templates out
cp ~/.hermes/skills/mac-app-cracking/templates/*.sh ./
```

Load in conversation:
```
/skill mac-app-cracking
```
Or it auto-triggers on: "crack this Mac app", "make a cracked DMG", "bypass license"

## ⚙️ Requirements

| Tool | Source |
|---|---|
| `pkgbuild` | Built into macOS |
| `hdiutil` | Built into macOS |
| `codesign` | Built into macOS |
| `plistlib` | Built into Python 3 on macOS |
| `PlistBuddy` | `/usr/libexec/PlistBuddy` (macOS) |
| `sshpass` | `brew install sshpass` (for remote builds) |

## 📝 License

Proprietary. This is licensed software. Contact the original seller for your own license.

---

*Cold protocol. Trail reads itself.*  
*LTX-QUASAR · mac-app-cracking v1.0*