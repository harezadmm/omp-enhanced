# TNT Scene Reference

> **Scope**: The TNT macOS cracking scene — DMG packaging, Gatekeeper bypass, binary patching, and release verification protocol.

---

## Who is TNT?

TNT (Team TNT) is the most prolific macOS cracking group active since ~2015. They release **original unmodified app bundles** packaged inside Gatekeeper-friendly DMGs with pre-applied binary patches. Their releases are cryptographically signed (PGP) and include verification tools.

**Identity:**
- PGP key fingerprint: `9D4B 00AE 65EC 2E79 F8AE  9B2D 3E42 3DD4 CF0A 7487`
- Contact: `tnt4mac@tuta.io`

**Philosophy** (from their .nfo files):
> "All TNT releases are provided free of charge for educational and uncommercial reasons. Support the software developers. If you like this app, BUY IT!"
> "Why join the navy if you can be a pirate?"

---

## DMG Structure

```
ForkLift 4.7.5.dmg (mounted)
├── ForkLift.app/           ← Original app, binary-patched
├── Help.txt                ← "Open Gatekeeper friendly" instructions
├── Extra/
│   ├── tnt.nfo             ← PGP-signed ASCII art release info
│   ├── tnt.sfv             ← rhash-compatible SHA-256 checksums
│   └── rhash               ← Verification tool binary (known-good)
├── .VolumeIcon.icns        ← Custom DMG icon
└── .background/            ← DMG background image (optional)
```

### Key Design Decisions

1. **The app itself is the original, not a repack**: TNT patches the app binary directly, then ships the whole `.app` bundle inside the DMG. No wrapper scripts, no installer packages — just drag to `/Applications`.

2. **hdiutil shadow mount**: When building the DMG, TNT uses `hdiutil attach -shadow` to mount the read-only DMG image read-write without modifying the original. The shadow file stores all modifications (including the binary patch).

3. **No scene labeling on the binary**: Unlike EDiSO who embeds protection label strings, TNT does not mark the patched binary with any identifier string. The crack is purely functional.

---

## Gatekeeper Bypass

TNT releases are **"Gatekeeper friendly"** — the DMG can be opened without triggering the "unidentified developer" dialog. However, post-installation, users must still clear quarantine:

```
xattr -rd com.apple.quarantine /Applications/ForkLift.app
```

Or for the nuclear option (not recommended by TNT but works):
```
sudo spctl --master-disable
```

The `Help.txt` file inside the DMG explains this to end users.

---

## Binary Patching Approach

TNT applies one of two strategies depending on the app architecture:

### Strategy A: Swift Apps (ForkLift, Pixelmator, etc.)

Swift uses **name mangling** — function names in the compiled binary are mangled into long strings encoding module, class, method, argument types, and return type.

**Discovery:**
```bash
nm -gU ForkLift.app/Contents/MacOS/ForkLift | grep -i license
nm -gU ForkLift.app/Contents/MacOS/ForkLift | grep -i valid
nm -gU ForkLift.app/Contents/MacOS/ForkLift | grep -i check
```

**Real ForkLift example:**
The target was `LicenseValidator.checkSignature(_,serial:)` — discovered via `nm -gU` output. This Swift method name mangles to something like:
```
_$s9ForkLift17LicenseValidatorC15checkSignature_6serialSbSS_SStF
```

**Patch:** The binary is hex-edited at the function offset to immediately return `true` (Swift `Bool` = 1). On ARM64 this is `MOV W0, #1 ; RET`. On x86_64 this is `MOV EAX, 1 ; RET`.

### Strategy B: RLM Apps (SketchUp, Autodesk products, etc.)

RLM (Reprise License Manager) is an enterprise DRM framework used by professional CAD/3D tools. RLM-managed apps communicate with a license server to validate floating/concurrent licenses.

**TNT's RLM bypass involves:**
1. **Return cached license as always valid** — find the RLM license cache check and force it to return `RLM_EL_NORMAL` (valid) regardless of expiry
2. **Block license server communication** — NOP out the network calls to the RLM server, making the app think it's in "offline mode" with a valid cached license
3. **Disable subscription expiry check** — Find the date comparison that says "license expired on X" and force it to always return "not expired"

**Real-world evidence:**
- **SketchUp 2026.3** — 35MB C++ binary containing the full RLM library statically linked. TNT patched the RLM validation functions directly. The release includes a TNT Easter egg (hidden in the DMG as a joke).

### Generic Patch Patterns

| Architecture | Bypass Technique | Hex Pattern |
|---|---|---|
| ARM64 | Return true | `20 00 80 D2 C0 03 5F D6` (MOV W0, #1; RET) |
| x86_64 | Return true | `B8 01 00 00 00 C3` (MOV EAX, 1; RET) |
| ARM64 | NOP conditional jump | Replace `B.NE` with `NOP` (1F 20 03 D5) |
| x86_64 | JNE → JMP | Replace `0F 85 XX XX XX XX` with `E9 XX XX XX XX` |

---

## PGP Signature Verification

Every TNT release ships a PGP-signed `.nfo` file. The signature can be verified:

```bash
gpg --verify Extra/tnt.nfo
```

**Unsigned `.nfo` = FAKE/MALWARE.** This is the single most important authenticity check for TNT releases. If a "TNT" release has no PGP signature or the signature doesn't verify, it is not an authentic TNT release.

---

## RHash Verification

TNT uses `rhash` (not `shasum`, not `md5`) for checksum verification:

```bash
cd /Volumes/ForkLift\ 4.7.5/
Extra/rhash -r Extra/tnt.sfv --sha256 --skip-ok -c
```

The `tnt.sfv` file is in RHash's native `.sfv` format with SHA-256 hashes. The `rhash` binary bundled in `Extra/` is the known-good official build — **never replace it** with a system-installed version.

Example `.sfv` content:
```
; tnt.sfv — SHA-256 checksums for ForkLift 4.7.5
ForkLift.app/Contents/MacOS/ForkLift e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
ForkLift.app/Contents/Info.plist 88f68531f38551bfbac210161bf16c1c2008092eb09eb2f89c17b7585029791b
...
```

---

## Case Study: ForkLift 4.7.5

**App metadata:**
- Bundle ID: `com.binarynights.ForkLift`
- Version: 4.7.5 (build 484)
- Architecture: Intel 64-bit (x86_64 only in this release)
- Minimum OS: macOS 14.6
- Protection: Custom (serial + license server validation)
- Sparkle feed: `https://updates.binarynights.com/ForkLift/update.xml`
- Sparkle public key: `1l1N21ETqGfz1kJ8u9/vNN9aMbfInc7tCCPbUSQ656g=`

**Crack technique:**
1. TNT identified `LicenseValidator.checkSignature(_,serial:)` via `nm -gU`
2. Binary patched to return `true` for any serial input
3. RLM framework functions patched to return cached-license-valid
4. Sparkle `SUFeedURL` blocked to prevent auto-update overwriting the crack
5. DMG assembled with hdiutil shadow mount, preserving original app signature metadata

**TNT .nfo excerpt (PGP-signed):**
```
-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA256

  ___________________________________________________________________________
 /  _____  _   _  _____   _                               _   _  ___   ___   \
|| |_   _|| \ | ||_   _| | |_   ___   __ _  _ __ ___     | \ | ||  _| / _ \  ||
||   | |  |  \| |  | |   | __| / _ \ / _` || '_ ` _ \    |  \| || |_ | | | | ||
...
||   Title:      ForkLift                                                    ||
||   Category:   Utilities                                                   ||
||   Source:     SIP                                                         ||
||   Version:    4.7.5                                                       ||
||   Requires:   macOS 27031.0 (Intel 64)                                    ||
||   Date:       2026-09-01                                                  ||
||   Protection: Custom                                                      ||
...
||                 Why join the navy if you can be a pirate?                 ||
||                        Reach us at tnt4mac@tuta.io                        ||
||    Key fingerprint: 9D4B 00AE 65EC 2E79 F8AE  9B2D 3E42 3DD4 CF0A 7487    ||
 \___________________________________________________________________________/

-----BEGIN PGP SIGNATURE-----
[Base64 signature block]
-----END PGP SIGNATURE-----
```

---

## Case Study: SketchUp 2026.3

**App metadata:**
- Architecture: Universal 2 (Intel + ARM64)
- Protection: RLM (Reprise License Manager)
- Binary size: 35MB (C++, statically linked RLM)

**Crack technique:**
1. Full RLM framework bypass — no serial key needed
2. Patched RLM license cache to always return valid
3. Patched RLM license server communication to no-op
4. Patched subscription expiry check to never expire
5. TNT Easter egg hidden in DMG (varies per release; not documented further)

---

## Sparkle Update Blocking

Most TNT releases ship with `SUFeedURL` still present in `Info.plist` — the app WILL auto-update and overwrite the crack if the user has internet access. TNT's approach:

1. **Document it**: The `Help.txt` warns users not to update
2. **Don't remove it**: Removing `SUFeedURL` changes the Info.plist signature, complicating DMG signing
3. **Trust users**: The user base is expected to know not to update cracked apps

For self-built redistributable DMGs, we SHOULD remove or block `SUFeedURL` in our postinstall script.

---

## Quick Reference

```bash
# Verify TNT release authenticity
gpg --verify Extra/tnt.nfo

# Verify file integrity
cd /Volumes/AppName/
Extra/rhash -r Extra/tnt.sfv --sha256 --skip-ok -c

# Install (Gatekeeper bypass)
xattr -rd com.apple.quarantine /Applications/AppName.app

# Discover Swift license symbols
nm -gU AppName.app/Contents/MacOS/AppName | grep -iE "license|valid|check|activate"
```