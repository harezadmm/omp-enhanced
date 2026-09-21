# Scene Release Taxonomy

> Comparing TNT, EDiSO, and appstorrent macOS crack scene releases — packaging, signing, protection conventions, and release metadata.

---

## Scene Comparison Matrix

| Attribute | TNT | EDiSO | appstorrent |
|---|---|---|---|
| **Active since** | ~2015 | 2020 | ~2016 |
| **Signature** | PGP-signed `.nfo` | Unsigned ASCII-art `.nfo` | None (HTML instruction page) |
| **DMG background** | Optional `.background/` | **Always** `dmgcanvas_bg.tiff` | ISO-based (no DMG decor) |
| **Inner format** | `.app` directly in DMG | `.app` directly in DMG | ISO mounted inside DMG → `.app` extracted |
| **Binary patch** | Swift name-mangled or RLM bypass | Hex-edit with protection label | V8 JSC swap + keygen (for Electron apps) |
| **Verification** | `rhash` tool + `.sfv` | None (trust-based) | SHA-256 in Patch script |
| **Gatekeeper** | "Gatekeeper friendly" DMG | Standard DMG (quarantine expected) | ISO mount bypasses quarantine |
| **Protection label** | None | Embedded in `.nfo` (e.g. "AES+ECC+SHA+B64+CTM") | None |
| **Update blocking** | Documented; not enforced | Sparkle `SUFeedURL` removed/blocked | `settings.json` toggle + codesign |
| **Contact** | `tnt4mac@tuta.io` | None in `.nfo` | `appstorrent.ru` website |
| **Philosophy** | "Educational only, buy if you like" | "Persistence. Perfection. Passion." | Paid help service offered |

---

## DMG Packaging Patterns

### TNT DMG

```
AppName.dmg
├── AppName.app/            ← Pre-patched, original bundle
├── Help.txt                ← Gatekeeper instructions
├── Extra/
│   ├── tnt.nfo             ← PGP-signed
│   ├── tnt.sfv             ← rhash checksums
│   └── rhash               ← Known-good binary
├── .VolumeIcon.icns
└── .background/            ← Optional
```

**Key characteristic**: The DMG contains everything. No inner DMG/ISO. The `.app` is the original, patched in-place. The `Help.txt` tells users how to bypass Gatekeeper.

**Build method**: `hdiutil create -srcfolder` with shadow mount for modifications.

### EDiSO DMG

```
AppName [EDiSO].dmg
├── .background/
│   └── dmgcanvas_bg.tiff   ← Always present (DMG Canvas)
├── .VolumeIcon.icns
├── ediso.nfo               ← Unsigned ASCII art
└── AppName.app/            ← Patched app bundle
```

**Key characteristic**: Always uses **DMG Canvas** (the `dmgcanvas_bg.tiff` is the tell). The `.nfo` file is always named `ediso.nfo` and contains large ASCII art. No verification tools. No inner DMG.

**The DMG Canvas background is the single most reliable EDiSO fingerprint.** If you see `dmgcanvas_bg.tiff` in a DMG's `.background/` folder, it's EDiSO.

### appstorrent DMG

```
AppName [appstorrent].dmg
├── DMG/                    ← Inner ISO or APFS image
│   └── AppName.app/
├── Patcher/                ← Crack tool folder
│   ├── Patch               ← Bash patch script
│   ├── keygen              ← Swift license generator
│   └── patchfiles/
│       ├── arm64/
│       │   ├── pk.node
│       │   └── index.jsc
│       └── x86_64/
│           ├── pk.node
│           └── index.jsc
├── 0. Инструкция (instruction).html  ← Russian/English bilingual guide
└── Fix                     ← Optional gatekeeper fix tool
```

**Key characteristic**: ISO-based. The `.app` is inside an inner ISO that gets mounted, then the Patcher script runs from outside. Two-level extraction: DMG → ISO → .app. The Patch script handles everything: backup, swap, verify, codesign, keygen.

---

## .nfo File Comparison

### TNT .nfo (ForkLift 4.7.5)

**Format**: PGP-signed plaintext
**Art**: Text-based border art (not full ASCII art), single-color
**Structure**:
```
-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA256

[Title banner in text-art box]
  Title:      ForkLift
  Category:   Utilities
  Source:     SIP
  Version:    4.7.5
  Requires:   macOS 27031.0 (Intel 64)
  Date:       2026-09-01
  Protection: Custom

[Checksum section]
  tnt.sfv digest (SHA-256): ...
  rhash digest (SHA-256):   ...
  You could verify files by running: ...

[Motto]
  Why join the navy if you can be a pirate?

[Contact]
  Reach us at tnt4mac@tuta.io
  Key fingerprint: 9D4B 00AE 65EC 2E79 F8AE 9B2D 3E42 3DD4 CF0A 7487

-----BEGIN PGP SIGNATURE-----
[signature]
-----END PGP SIGNATURE-----
```

**Key features**:
- PGP signed — cryptographically verifiable authenticity
- Clean, minimal layout
- No cracker credits (team release, not individual)
- Source field ("SIP" = Scene Internal Provider)
- Educational disclaimer

### EDiSO .nfo (Alcove 1.7.9)

**Format**: Full ASCII art with box drawing
**Art**: Elaborate multi-line 3D-style ASCII art, team logo, decorative borders
**Structure**:
```
[Elaborate ASCII art header spanning ~30 lines]

[Release info box]
  Alcove v1.7.9 (c) Henrik Ruscon
  Retail Date: 01.07.2026  | Protection: AES+ECC+SHA+B64+CTM
  Crack Date:  17.08.2026  | Cracker: eD! / TEAM EDiSO
  App Size:    25 MB       | Supplier: eD! / TEAM EDiSO
  Architecture: U2B        | Packer:   eD! / TEAM EDiSO

[App description paragraph]

[Installation instructions (3 steps)]
  1. Mount DMG
  2. Drag .app to Applications folder
  3. Profit.

[Greetings to other scene groups]

[Footer]
  Since 2020  ❤  Persistence. Perfection. Passion.  ❤  NFO by eD!
```

**Key features**:
- **NOT cryptographically signed** — no PGP, no hash verification
- Full individual credits (eD! is credited as cracker, supplier, AND packer)
- Protection label is part of the release metadata
- App description is marketing copy from the official website
- "Since 2020" — EDiSO has been active since 2020

### EDiSO .nfo (Cap 0.5.9)

**Format**: Identical template to Alcove — same header art, same layout
**Differences**:
- Protection: "Custom" (not a specific label like "AES+ECC+SHA+B64+CTM")
- App Size: 463.1 MB (Tauri app — much larger than native)
- Architecture: U2B (Intel & ARM)
- Retail/Crack Date both 03.09.2026 (day-0 crack — same day as retail release)

---

## Inner Format Comparison

| Scene | Inner Format | How the .app is delivered |
|---|---|---|
| **TNT** | None | `.app` is directly in the DMG root |
| **EDiSO** | None | `.app` is directly in the DMG root |
| **appstorrent** | ISO (HFS+/APFS) | `.app` is inside an inner ISO image nested in the DMG |

### Why appstorrent uses ISO

ISO images mounted via `hdiutil attach` bypass macOS Gatekeeper checks that apply to `.app` bundles inside `.dmg` files. The inner ISO acts as a quarantine bypass layer — when you mount the ISO, the `.app` inside has never been through the quarantine attribution pipeline.

This is also why appstorrent releases include a `Fix` tool — sometimes the bypass doesn't work on newer macOS versions and Gatekeeper needs manual intervention.

---

## Protection Labeling Conventions

### EDiSO Protection Labels

EDiSO labels the protection method in their `.nfo` files. These labels describe the obfuscation/DRM technique, not the crack method:

| Label | Meaning | Example |
|---|---|---|
| `AES+ECC+SHA+B64+CTM` | Multi-layer obfuscation: AES encryption, ECC keys, SHA hashing, Base64 encoding, Custom Transform Method | Alcove |
| `Custom` | Proprietary protection, no standard label applies | Cap |
| `Polar` | Polar framework-based DRM | Other EDiSO releases |

**Important**: These labels describe the **protection**, not the crack. When you see `AES+ECC+SHA+B64+CTM`, it means the app's license validation uses these techniques — you don't need to reverse them; you patch the binary AROUND them.

### TNT Protection Labels

TNT uses simple labels in their `.nfo`:
- `Custom` — proprietary serial/key validation
- `RLM` — Reprise License Manager
- TNT does NOT label the obfuscation technique, only the DRM framework

---

## Release Naming Conventions

### TNT
```
AppName 4.7.5.dmg                  ← Version only in filename
AppName 4.7.5 [TNT].dmg            ← Occasionally with [TNT] tag
```

### EDiSO
```
AppName 1.7.9 [EDiSO].dmg          ← Always with [EDiSO] tag
Cap 0.5.9 [EDiSO].dmg
```

### appstorrent
```
AppName v26.1.3 macOS/
├── AppName v26.1.3 macOS.dmg      ← Main DMG with version
├── 0. Инструкция (instruction).html
├── 1. Installer/
├── 2. Patcher/
└── Fix
```

---

## Scene Trust Model

| Scene | Trust Model | Verification | Risk |
|---|---|---|---|
| **TNT** | Cryptographic (PGP) | `gpg --verify` + `rhash` checksums | Low — verifiable |
| **EDiSO** | Reputation-based | None (trust the source) | Medium — no cryptographic verification |
| **appstorrent** | Community + SHA-256 in Patch | Patch script auto-verifies before applying | Low-Medium — SHA verified, but trust the supplier |