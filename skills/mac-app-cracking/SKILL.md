# mac-app-cracking

Universal Mac app reverse-engineering & crack packaging skill. Produces self-contained `.dmg` with `.pkg` installer — user double-clicks `.pkg`, app is cracked automatically. No terminal, no scripts, no extra steps.

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
- License type: RevenueCat, Superwall, custom API validation, UserDefaults-based, plist-based

## Workflow

### Phase 1: Analysis — What kind of license?

```
1. SSH into Mac with the app installed
2. Identify license method:
   - RUN the app, check what happens (trial popup? paywall? "activate"?)
   - Check bundle ID: /usr/libexec/PlistBuddy -c "Print CFBundleIdentifier" /Applications/AppName.app/Contents/Info.plist
   - Search for license frameworks:
     find /Applications/AppName.app -name "RevenueCat*" -o -name "Superwall*" -o -name "AppsFlyer*" -o -name "Purchases*"
   - Check UserDefaults for license keys:
     defaults read com.example.bundle 2>/dev/null | grep -iE "license|pro|premium|trial|purchase|subscri"
   - Check for cache files:
     find ~/Library -path "*com.example.bundle*" -name "*.plist" -o -name "*.json" 2>/dev/null
   - Check Info.plist for LSEnvironment / custom keys
   - Run strings on binary:
     strings /Applications/AppName.app/Contents/MacOS/AppName | grep -iE "license|activate|trial|pro|premium|validate|api\."
```

### Phase 2: Classify crack type

| License Type | Detection | Crack Method |
|---|---|---|
| **RevenueCat** | `RevenueCat_RevenueCat.bundle`, `com.revenuecat.user_defaults.plist` | Inject fake `purchaserInfo` + block `api.revenuecat.com` |
| **Superwall** | `SuperwallKit_SuperwallKit.bundle` | Block `subscriptions-api.superwall.com` |
| **Custom API** | `strings App | grep "api."` returns license server URL | Block API in `/etc/hosts` |
| **UserDefaults** | `defaults read com.X | grep -i license` returns keys like `License.cachedHasLicense` | Inject fake values into UserDefaults |
| **Cache file** | License JSON/plist in `~/Library/Application Support/` | Write fake license file |
| **Binary check** | No network, no UserDefaults — license logic in binary itself | Need `lldb`/hopper/ghidra to patch. Advanced. |

### Phase 3: Design postinstall

Postinstall runs as root after `.pkg` install. Three mandatory parts:

```bash
#!/bin/bash
set -e
APP_NAME="AppName"
BUNDLE_ID="com.example.bundle"
WHOAMI=$(whoami)

# ─── 1. BLOCK API HOSTS ───
# Add to /etc/hosts: 0.0.0.0 api.example.com
# Flush DNS: dscacheutil -flushcache; killall -HUP mDNSResponder

# ─── 2. INJECT LICENSE ───
# If RevenueCat: su - "$WHOAMI" -c "python3 -c '...'" (writes to ~/Library/Containers/...)
# If UserDefaults: su - "$WHOAMI" -c "defaults write $BUNDLE_ID key value"
# If cache file: su - "$WHOAMI" -c "echo 'JSON' > ~/Library/Application Support/AppName/license.json"

# ─── 3. RE-SIGN ───
# codesign --remove-signature /Applications/AppName.app
# xattr -cr /Applications/AppName.app
# codesign --force --deep --sign - /Applications/AppName.app
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

## Critical Patterns

### RevenueCat injection (the hard one)

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

### UserDefaults injection (the easy one)

```bash
# Read existing keys first:
defaults read com.example.bundle 2>/dev/null

# Inject:
defaults write com.example.bundle "License.hasLicense" -bool true
defaults write com.example.bundle "License.expiryDate" -string "2099-01-01"
defaults write com.example.bundle "License.type" -string "lifetime"
```

### Cache file injection

```bash
# Some apps read license from disk:
mkdir -p "$HOME/Library/Application Support/AppName"
echo '{"hasLicense":true,"type":"lifetime","expiry":"2099-01-01"}' \
  > "$HOME/Library/Application Support/AppName/license.json"
```

## Pitfalls

1. **RevenueCat plist overwritten**: App rewrites plist on launch → use `chflags uchg` (immutable system flag). `chmod 444` NOT enough.

2. **Gatekeeper blocks app**: Always `xattr -cr` + `codesign --force --deep --sign -` after modification.

3. **postinstall runs as root**: Use `su - "$WHOAMI" -c "..."` for any UserDefaults/cache writes that must go to the user's home, not root's.

4. **pkgbuild permission warnings**: The "Permission denied" warnings during pkgbuild are harmless — it's the tool trying to read symlinks inside the app bundle.

5. **Multiple license layers**: Check ALL frameworks (RevenueCat + Superwall + AppsFlyer). Each needs its own fix.

6. **Cached data persists**: If testing on same Mac, delete the old plist/cache first: `rm -rf ~/Library/Containers/BUNDLE_ID/Data/Library/Preferences/com.revenuecat.*`

7. **wrong user**: Script jalan as root → `whoami` returns root. Store real user early with `WHOAMI=$(logname 2>/dev/null || echo "$SUDO_USER" || stat -f%Su /dev/console)`.

## Verification

After install, verify:

```bash
# Check hosts block
grep "0.0.0.0" /etc/hosts

# Check UserDefaults (if applicable)
defaults read com.example.bundle License.hasLicense

# Check cache file (if applicable)
cat ~/Library/Application\ Support/AppName/license.json

# Check plist immutability (RevenueCat)
ls -lO ~/Library/Containers/com.example/Data/Library/Preferences/com.revenuecat.user_defaults.plist
# Should show "uchg" flag

# Launch app and visually confirm
open /Applications/AppName.app
# Check: no trial popup, no paywall, Pro badge visible
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

## References

- [RevenueCat iOS SDK — PurchaserInfo format](https://github.com/RevenueCat/purchases-ios)
- [Apple pkgbuild manual](https://www.unix.com/man-page/osx/1/pkgbuild/)
- [Creating self-contained PKG installers](https://derflounder.wordpress.com/2014/05/24/packaging-with-pkgbuild-training-video/)

## Companion Files

This skill works with these scripts (copy from linearity-crack or wallper-crack as templates):

```
build_pkg_dmg.sh    — Builder: source app → .pkg → .dmg
postinstall.sh      — Runs after .pkg install (as root)
```

For each new app, customize:
- `APP_NAME`, `BUNDLE_ID`, `BLOCK_HOSTS` array
- License injection method (RevenueCat / UserDefaults / cache file)
- Version string