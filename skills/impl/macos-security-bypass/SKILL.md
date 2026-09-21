---
name: macos-security-bypass
description: >-
  macOS security bypass playbook. Use when targeting macOS endpoints and need to bypass TCC, Gatekeeper, SIP, sandbox, code signing, or entitlement-based protections during authorized red team or pentest engagements.
---

# SKILL: macOS Security Bypass — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert macOS security bypass techniques. Covers TCC bypass, Gatekeeper evasion, SIP restrictions, sandbox escape, and entitlement abuse. Base models miss version-specific bypass nuances and protection interaction effects.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [macos-process-injection](../macos-process-injection/SKILL.md) when you need dylib injection, XPC exploitation, or Electron abuse after achieving initial access
- [linux-privilege-escalation](../linux-privilege-escalation/SKILL.md) for Unix-layer privesc techniques that also apply to macOS (SUID, cron, writable paths)
- [linux-security-bypass](../linux-security-bypass/SKILL.md) for shared Unix security bypass concepts

### Advanced Reference

Also load [TCC_BYPASS_MATRIX.md](./TCC_BYPASS_MATRIX.md) when you need:
- Per-macOS-version TCC bypass mapping
- Protection-type-specific techniques (Camera, Microphone, FDA, Automation)
- MDM/configuration profile abuse patterns

---

## 1. TCC (TRANSPARENCY, CONSENT, CONTROL) OVERVIEW

TCC is macOS's permission framework controlling access to sensitive resources (camera, microphone, contacts, full disk access, etc.).

### 1.1 TCC Database Locations

| Database | Path | Controls | Protection |
|---|---|---|---|
| User-level | `~/Library/Application Support/com.apple.TCC/TCC.db` | Per-user consent decisions | SIP-protected since Catalina |
| System-level | `/Library/Application Support/com.apple.TCC/TCC.db` | System-wide consent decisions | SIP-protected |
| MDM-managed | Via configuration profiles | Push PPPC (Privacy Preferences Policy Control) | Device management |

```sql
-- Query TCC database (requires FDA or SIP off)
sqlite3 ~/Library/Application\ Support/com.apple.TCC/TCC.db \
  "SELECT service, client, allowed FROM access;"
```

### 1.2 TCC Bypass Categories

| Category | Mechanism | Typical Prerequisite |
|---|---|---|
| FDA app exploitation | Piggyback on apps already granted Full Disk Access | Write access to FDA app's bundle or plugin dir |
| Direct DB modification | Edit TCC.db to grant consent | SIP disabled or FDA |
| Inherited permissions | Child process inherits parent's TCC grants | Code execution in context of FDA-granted app |
| Automation abuse | Apple Events / osascript to control TCC-granted app | Automation permission (lower bar than direct TCC) |
| Mounting tricks | Mount a crafted disk image containing modified TCC.db | Local access, pre-Ventura |
| SQL injection in TCC | Malformed bundle IDs triggering SQL injection in TCC subsystem | CVE-2023-32364 and similar |

### 1.3 Known TCC Bypass Patterns

**Terminal / iTerm FDA inheritance**: Terminal.app granted FDA → any command run inherits FDA → read any file.

```bash
# If Terminal has FDA, this reads protected files directly
cat ~/Library/Mail/V*/MailData/Envelope\ Index
cat ~/Library/Messages/chat.db
```

**Finder automation**: Automate Finder (lower permission bar) to access files in protected locations.

```applescript
tell application "Finder"
  set f to POSIX file "/Users/target/Library/Mail/V9/MailData/Envelope Index"
  duplicate f to desktop
end tell
```

**System Preferences / System Settings injection**: Inject into a process that already has TCC permissions by writing to its Application Scripts folder.

**MDM profile abuse**: PPPC profiles can pre-approve TCC permissions. Rogue MDM enrollment or compromised MDM server → push PPPC payload.

---

## 2. GATEKEEPER BYPASS

Gatekeeper blocks unsigned or unnotarized apps from executing. Core enforcement depends on the `com.apple.quarantine` extended attribute.

### 2.1 Quarantine Attribute Removal

```bash
# Check quarantine attribute
xattr -l /path/to/app
# Output: com.apple.quarantine: 0083;...

# Remove quarantine (requires write access)
xattr -d com.apple.quarantine /path/to/app
# Recursive for app bundles
xattr -rd com.apple.quarantine /path/to/MyApp.app
```

### 2.2 Bypass Techniques

| Technique | How It Works | macOS Version |
|---|---|---|
| `xattr -d` removal | Remove quarantine before execution | All (requires local access) |
| App translocation bypass | Apps in certain locations skip translocation | Pre-Catalina |
| Archive tools that strip quarantine | Some unarchiver apps don't propagate quarantine | Varies by tool |
| Unsigned code in signed bundle | Notarized app bundles with unsigned nested helpers | Pre-Ventura (CVE-2022-42821) |
| Safari auto-extract + open | Downloaded ZIP auto-extracted, app opened before quarantine fully applied | Safari-specific, patched |
| ACL abuse | `com.apple.quarantine` can be blocked by ACLs set before download | Requires pre-positioning |
| Disk image (DMG) tricks | DMG mounted from network share may not carry quarantine | Network share context |
| BOM (Bill of Materials) bypass | Crafted BOM in pkg skips quarantine for extracted files | CVE-2022-22616 |

### 2.3 Gatekeeper Check Flow

```
App launched
│
├── com.apple.quarantine attribute present?
│   ├── No → execute (no Gatekeeper check)
│   └── Yes ↓
│
├── Code signature valid?
│   ├── No → block
│   └── Yes ↓
│
├── Notarized (stapled ticket or online check)?
│   ├── No → block (Catalina+)
│   └── Yes → execute
│
└── User override? (right-click → Open → confirm)
    └── Bypasses Gatekeeper once for this app
```

---

## 3. SIP (SYSTEM INTEGRITY PROTECTION)

SIP restricts root from modifying protected system locations, loading unsigned kernel extensions, and debugging system processes.

### 3.1 SIP-Protected Locations

```
/System/
/usr/ (except /usr/local/)
/bin/
/sbin/
/var/ (selected subdirs)
/Applications/ (pre-installed Apple apps)
```

### 3.2 SIP Status & Configuration

```bash
csrutil status              # Check SIP status
csrutil disable             # Recovery Mode only
csrutil enable --without fs # Partial disable (risky)
```

### 3.3 Entitlements That Bypass SIP

| Entitlement | Effect |
|---|---|
| `com.apple.rootless.install` | Write to SIP-protected paths |
| `com.apple.rootless.install.heritable` | Child processes inherit SIP bypass |
| `com.apple.security.cs.allow-unsigned-executable-memory` | JIT/unsigned code in memory |
| `com.apple.private.security.clear-library-validation` | Load unsigned libraries |

### 3.4 Historical SIP Bypasses

| CVE | macOS | Technique |
|---|---|---|
| CVE-2021-30892 (Shrootless) | Monterey pre-12.0.1 | `system_installd` + post-install script in signed pkg |
| CVE-2022-22583 | Monterey pre-12.2 | `packagekit` + mount point manipulation |
| CVE-2022-46689 (MacDirtyCow) | Ventura pre-13.1 | Race condition on copy-on-write, overwrite SIP files |
| CVE-2023-32369 (Migraine) | Ventura pre-13.4 | Migration Assistant TCC/SIP bypass via systemmigrationd |
| CVE-2024-44243 | Sequoia pre-15.2 | StorageKit daemon exploitation |

---

## 4. SANDBOX ESCAPE

macOS sandboxing (App Sandbox, via `sandbox-exec` or entitlements) restricts app access to filesystem, network, and IPC.

### 4.1 Office Sandbox Escape Patterns

| Vector | Description |
|---|---|
| Open/Save dialog abuse | User grants file access via dialog → macro reads/writes beyond sandbox |
| `~/Library/LaunchAgents/` persistence | Some sandbox profiles allow writing LaunchAgent plists |
| Login Items manipulation | Add login item pointing to payload outside sandbox |
| Shared container exploitation | Multiple apps sharing the same App Group container |

### 4.2 IPC-Based Escape

| IPC Mechanism | Escape Vector |
|---|---|
| XPC Services | Connect to privileged XPC service with insufficient client validation |
| Mach Ports | Obtain send right to privileged task port |
| Apple Events | Automate unsandboxed app to perform actions |
| Distributed Notifications | Signal unsandboxed helper to execute payload |
| Pasteboard | Write payload to pasteboard, have unsandboxed app consume it |

### 4.3 Browser Sandbox

- Chromium: Multi-process model, renderer is sandboxed, browser process is not
- Safari: WebContent process sandboxed, parent Safari process has more privileges
- Exploit chain: renderer RCE → sandbox escape (via IPC bug to browser process) → system access

---

## 5. CODE SIGNING & ENTITLEMENTS

### 5.1 Inspecting Signatures and Entitlements

```bash
codesign -dv --verbose=4 /path/to/app       # Signature details
codesign -d --entitlements :- /path/to/app   # Dump entitlements
security cms -D -i /path/to/mobileprovision  # Provisioning profile

# Verify signature validity
codesign --verify --deep --strict /path/to/app
spctl --assess --type execute /path/to/app   # Gatekeeper assessment
```

### 5.2 Entitlement Abuse for Privilege Escalation

| Entitlement | Abuse Scenario |
|---|---|
| `com.apple.security.cs.disable-library-validation` | Load attacker dylib into entitled process |
| `com.apple.security.cs.allow-dyld-environment-variables` | DYLD_INSERT_LIBRARIES injection |
| `com.apple.security.get-task-allow` | Attach debugger, inject code |
| `com.apple.security.cs.debugger` | Debug any process |
| `com.apple.private.apfs.revert-to-snapshot` | Revert APFS snapshots, bypass modifications |

### 5.3 Hardened Runtime Bypass

Hardened Runtime prevents: DYLD env vars, debugging, unsigned memory execution. Bypasses:
- Find entitled apps that weaken Hardened Runtime (`disable-library-validation`)
- Exploit JIT-entitled apps (browsers, VMs) for unsigned code execution
- Use `get-task-allow` entitled debug builds left in production

### 5.4 Library Validation Bypass

Library validation ensures only Apple-signed or same-team-signed dylibs load.

```bash
# Find apps with library validation disabled
codesign -d --entitlements :- /Applications/*.app/Contents/MacOS/* 2>/dev/null | \
  grep -l "disable-library-validation"
```

---

## 6. PERSISTENCE AFTER BYPASS

| Method | Location | Survives Reboot | Notes |
|---|---|---|---|
| LaunchAgent | `~/Library/LaunchAgents/` | Yes | User-level, runs at login |
| LaunchDaemon | `/Library/LaunchDaemons/` | Yes | Root-level, runs at boot |
| Login Items | `~/Library/Application Support/com.apple.backgroundtaskmanagementagent/` | Yes | Visible in System Settings |
| Cron | `crontab -e` | Yes | Often overlooked by defenders |
| Dylib hijack | Writable dylib search path | Yes | Triggered when target app launches |
| Folder Action | `~/Library/Scripts/Folder Action Scripts/` | Yes | Triggers on folder events |

---

## 7. macOS SECURITY BYPASS DECISION TREE

```
Target is macOS endpoint
│
├── Need to execute untrusted binary?
│   ├── Quarantine attribute present?
│   │   ├── Yes → xattr -d com.apple.quarantine (§2.1)
│   │   └── No → execute directly
│   └── Gatekeeper still blocks?
│       ├── Signed but not notarized → right-click → Open override
│       └── Unsigned → embed in signed bundle or use archive tricks (§2.2)
│
├── Need access to TCC-protected resources?
│   ├── FDA-granted app available?
│   │   ├── Yes → exploit FDA app context (§1.3)
│   │   └── No ↓
│   ├── Automation permission obtainable?
│   │   ├── Yes → Apple Events to TCC-granted app (§1.3)
│   │   └── No ↓
│   ├── SIP disabled?
│   │   ├── Yes → direct TCC.db modification (§1.2)
│   │   └── No → check version-specific TCC bypass (→ TCC_BYPASS_MATRIX.md)
│   └── MDM present?
│       └── Compromised MDM → push PPPC profile (§1.3)
│
├── Need to bypass SIP?
│   ├── Check macOS version → historical SIP CVE? (§3.4)
│   ├── Find entitled Apple binary → piggyback SIP-bypass entitlement (§3.3)
│   └── Recovery Mode access? → csrutil disable (§3.2)
│
├── Need sandbox escape?
│   ├── Office macro context → dialog/LaunchAgent tricks (§4.1)
│   ├── XPC service with weak validation → IPC escape (§4.2)
│   └── Browser context → renderer → sandbox escape chain (§4.3)
│
├── Need to inject into signed process?
│   ├── disable-library-validation entitlement? → dylib injection
│   ├── allow-dyld-environment-variables? → DYLD_INSERT_LIBRARIES
│   ├── get-task-allow? → debugger attach
│   └── None → check macos-process-injection SKILL.md
│
└── Need persistence?
    └── Choose method by access level (§6)
```

---

## 8. QUICK REFERENCE: TOOL COMMANDS

```bash
# Enumerate TCC permissions
tccutil reset All                              # Reset all TCC (admin)
sqlite3 TCC.db "SELECT * FROM access;"         # Read TCC DB

# Gatekeeper status
spctl --status                                 # Gatekeeper enabled?
spctl --assess -v /path/to/app                 # Check app assessment

# SIP status
csrutil status

# Find interesting entitlements across system
find /System/Applications /Applications -name "*.app" -exec sh -c \
  'codesign -d --entitlements :- "$1" 2>/dev/null | grep -q "disable-library-validation" && echo "$1"' _ {} \;

# List loaded kexts (kernel extensions)
kextstat | grep -v com.apple

# Sandbox profile inspection
sandbox-exec -p "(version 1)(allow default)" /bin/ls  # Test sandbox rules
```

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Which **mechanism** was abused - TCC, Gatekeeper, SIP, sandbox, entitlement - and at what version? | the finding is a mechanism, not a state |
| 2 | What is the **stock behaviour**: does the action FAIL on a clean host under the same conditions? | the control that makes the bypass a bypass |
| 3 | Did the action **succeed**, observed as its effect rather than a reported code? | an exit status is not a bypass |
| 4 | Is the target host's **security state** recorded - SIP, SSV, TCC database, notarisation? | severity and validity are version-dependent |
| 5 | What **privilege or data** did the bypass actually reach? | the impact |
| 6 | Is it **persistent** after a reboot or a re-login? | a session artefact vs an installed change |
| 7 | Was the mechanism **patched in a later macOS build**? | scope, and the honest reach of the finding |

**A recorded stock-failure control plus the observed effect.** A command that "worked" on a host whose
security state you did not record is not a finding.

---

## 10. EXECUTION PRIMITIVES

A macOS bypass is proven by **a stock-host control failure, the same action's observed effect, and the
exact OS build and security state recorded**. A tool exiting `0` is not a bypass.

### 9.1 The environmental baseline, which every claim depends on

```bash
# RUN THIS FIRST. Every finding in this file is conditional on these values.
echo "=== the OS build, which decides whether the mechanism still applies ==="
sw_vers
uname -a
echo
echo "=== SIP: the state, not just 'enabled' ==="
csrutil status
# the DECODED flags; 'enabled' with undocumented bits set behaves differently
csrutil status --verbose 2>/dev/null | head -5
nvram -p 2>/dev/null | grep -i csr-active-config || echo "  (read csr-active-config via ioreg/nvram on Intel; N/A on Apple silicon)"
echo
echo "=== SSV (Sealed System Volume): the modern gate on /System modification ==="
csrutil authenticated-root status 2>/dev/null || echo "  authenticated-root unsupported on this build"
mount | grep -E ' / | /System/Volumes/Data ' | head -3
echo "  -> a SEALED root means /System writes are refused at the volume layer, not by SIP alone."
echo
echo "=== Gatekeeper and notarisation policy, as the system sees it ==="
spctl --status
spctl --list 2>/dev/null | head -5
echo
echo "=== TCC: the SCHEMA version decides which paths exist in the database ==="
sqlite3 "$HOME/Library/Application Support/com.apple.TCC/TCC.db" \
  "select service, client, auth_value from access where client like '%' limit 5;" 2>&1 | head -8
echo "  -> the user-level TCC.db is version-independent; the SYSTEM-level one needs root."
echo
echo "=== RECORD ALL OF THE ABOVE IN THE REPORT. A bypass claimed without them is unreproducible. ==="
```

**The OS build, SIP, SSV, Gatekeeper policy, and TCC schema version are the finding's preconditions.** A
bypass without them cannot be reproduced or scoped.

### 9.2 The control-then-effect pattern, which is the whole method

```bash
# THE PATTERN: run the action STOCK, record the refusal, then apply the mechanism and re-run.
# A single successful run proves nothing - it may be a host where the protection never applied.
echo "=== PHASE 1: THE CONTROL - the stock refusal, recorded verbatim ==="
TARGET="$HOME/Library/Application Support/SomeApp/secret.db"
cp /dev/null /tmp/control.out 2>/dev/null
"${TARGET_APP:-/bin/echo}" 2>&1 | tee /tmp/control.out
echo "  control exit=$?  output=$(wc -c < /tmp/control.out)B"
echo "  RECORD: the exact error string. 'Operation not permitted' is TCC/sandbox;"
echo "  'code signature invalid' is Gatekeeper; 'Operation not permitted' on /System is SSV."
echo
echo "=== PHASE 2: the mechanism, applied with its own precondition ==="
case "${MECH:-tcc}" in
  tcc)
    echo "  TCC requires either the user's consent, an authorised client, or a path that does not"
    echo "  consult TCC (a different service's semantics, a non-Apple-signed tool, a symlink target)"
    echo "  RECORD: which of these is the mechanism. 'sqlite3 TCC.db' as the mechanism means the"
    echo "  target host was already compromised - say so."
    ;;
  gatekeeper)
    echo "  Gatekeeper consults the quarantine xattr and the notarisation ticket."
    echo "  RECORD: the xattr state BEFORE (xattr -l) and whether the bundle's signature validates."
    echo "  A binary that never had com.apple.quarantine is not a Gatekeeper bypass, it is a"
    echo "  binary that arrived without the attribute - STATE WHICH."
    ;;
  sip)
    echo "  SIP protects specific paths. RECORD the exact path you wrote and whether it is on SIP's"
    echo "  protected list, or merely root-owned. Writing to a root-owned UNPROTECTED path is not"
    echo "  a SIP bypass."
    ;;
esac
echo
echo "=== PHASE 3: the effect, observed as the EFFECT ==="
echo "  not 'the command succeeded' but: the file's content changed, the process ran, the data"
echo "  was read, the persistence item exists after a reboot."
echo
echo "=== PHASE 4: THE SECOND CONTROL - revert and confirm the stock behaviour returns ==="
echo "  undo the mechanism and re-run phase 1. The refusal must come back. Without this, the"
echo "  effect may be unrelated to the mechanism you think you used."
echo
echo "=== PHASE 5: persistence, tested by actually rebooting or re-logging in ==="
ls -la "$HOME/Library/LaunchAgents/" 2>/dev/null | head -5
launchctl list 2>/dev/null | grep -c . || true
sudo launchctl list 2>/dev/null | grep -c . || true
echo "  -> a LaunchAgent present BEFORE the reboot and absent after is not persistence."
```

**Phase 4 is the second control and the one most often skipped.** Reverting the mechanism must bring the
refusal back; if it does not, the effect and the mechanism are unrelated.

### 9.3 The version-conditional checks, which decide whether the finding stands

```bash
cat <<'GATES'
TCC            schema changed across macOS releases (service names and client requirements moved).
               A path that works on 12.x may not exist on 14.x. STATE THE BUILD, always.
               The 'granted by consent' path and the 'path not consulted' path are DIFFERENT findings
               and must not be merged: the second is not a permission bypass at all.

GATEKEEPER     the notary service and the first-launch flow are server-side and change silently.
               A Gatekeeper 'bypass' verified in an OFFLINE environment has not been tested against
               the live notary service. Say which environment you tested in.

SIP            protected-path lists change between releases, and Apple silicon adds the sealed
               system volume. csrutil status alone is insufficient - record SSV too.
               A boot-arg or recovery-mode change to SIP is NOT a bypass, it is a configuration
               change made with physical access. Do not report it as a bypass.

SANDBOX        the profile language is undocumented and version-dependent; a container escape that
               works in one profile may be blocked in another. NAME THE PROFILE'S SOURCE
               (an app's entitlements, a compiled .sb file) rather than saying 'the sandbox'.

ENTITLEMENTS   an entitlement is only enforced if the code is signed with it AND the kernel's
               policy accepts that signature. A binary carrying an entitlement string without a
               valid signature demonstrates nothing. CHECK the signature, not the plist.
GATES
echo
echo "=== THE CONTROL for every one of the above: run the SAME test on a SECOND macOS build ==="
echo "  one build is a data point; two builds with a difference is a version-scoped finding."
```

**Name the build and the profile's source.** A configuration change made with recovery-mode access is not
a bypass, and a version-dependent mechanism must be reported as version-scoped.

### 9.4 The end-to-end harness

```bash
python3 - <<'PY'
print("=== macOS SECURITY BYPASS ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the OS build, architecture, and sw_vers output are recorded",
  "every mechanism here is version-conditional"),
 ("SIP AND SSV/authenticated-root states are both recorded",
  "'csrutil status: enabled' alone does not describe the modern gate"),
 ("the Gatekeeper policy and the quarantine xattr state are recorded",
  "a binary that never had the attribute is not a Gatekeeper bypass"),
 ("the TCC database's schema and the specific service are named",
  "TCC semantics moved between releases; 'TCC was bypassed' is not a mechanism"),
 ("the STOCK CONTROL failure is recorded verbatim, with its error string",
  "the error string identifies the layer; without it there is no bypass"),
 ("the effect was observed as the EFFECT, not as an exit code",
  "the file changed, the process ran, the data was read"),
 ("the MECHANISM was reverted and the stock refusal RETURNED",
  "the second control; without it the effect may be unrelated to the mechanism"),
 ("persistence was tested across a real reboot or re-login",
  "a LaunchAgent present before a reboot and gone after is not persistence"),
 ("the test was repeated on a SECOND macOS build",
  "one build is a data point; two make it version-scoped"),
 ("the privileges actually reached are stated",
  "root, a TCC service, a specific data set - name what was reached"),
 ("configuration changes made with recovery-mode or boot-arg access are labelled as such",
  "that is a configuration change, not a bypass, and must not be reported as one"),
]
for n, how in CHECKS: print("  [ ] %-62s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  environment : macOS build, arch, SIP, SSV, Gatekeeper policy, TCC schema")
print("  mechanism   : TCC / Gatekeeper / SIP / sandbox / entitlement, named precisely")
print("  control     : the stock refusal, verbatim, with its error string")
print("  effect      : the observable change")
print("  revert      : the mechanism undone, and the refusal returning")
print("  persistence : the reboot test's result")
print("  scope       : which builds the mechanism applies to, from the second-build test")
PY
```

**Environment, mechanism, control, effect, revert, persistence, scope.** The revert line is what makes the
causal claim, and it is the one that gets skipped.

---

## 11. EVIDENCE STANDARD — MACOS BYPASS ARTEFACTS

| Item | Why |
|---|---|
| The **macOS build**, architecture, and `sw_vers` output | every mechanism here is version-conditional |
| **SIP** and **SSV/authenticated-root** states, both | the modern gate is the volume seal, not SIP alone |
| The **Gatekeeper policy** and the **quarantine xattr** state | distinguishes a bypass from an attribute that was never present |
| The **TCC schema** and the **specific service** named | TCC semantics moved between releases |
| The **stock refusal**, verbatim, with its **error string** | the error string identifies the layer |
| The **effect**, observed as the effect | an exit code is not a bypass |
| The **revert result**: the mechanism undone and the refusal returning | the causal control |
| The **persistence test** across a real reboot or re-login | a session artefact is not persistence |
| The **second build's** result | makes the finding version-scoped rather than anecdotal |
| The **privileges or data actually reached** | the impact |
| Whether **physical access** (recovery mode, boot args) was a precondition | that is a configuration change, not a bypass |

Report the **build, the control, and the effect**: "on macOS `14.5` (`23F79`) on Apple silicon with
`csrutil status: System Integrity Protection status: enabled.` and authenticated-root enabled, the target
app's attempt to read `~/Library/Application Support/OtherApp/secret.db` failed with `Operation not
permitted` and `tccd` logged a denial for the `kTCCServiceSystemPolicyAllFiles` service against client
`com.example.reader`, which is the control. The mechanism was the app's own `com.apple.security.
files.user-selected.read-write` entitlement combined with a user-selected file dialog, which returns a
security-scoped bookmark covering the parent directory, so the subsequent read succeeded without a
`kTCCServiceSystemPolicyAllFiles` grant, and the file's contents were observed. Reverting the bookmark
and re-running the read reproduced the original refusal, which is the second control. The same test on
macOS `13.6` (`22G120`) behaved identically, so the mechanism is not version-specific across those two
builds. The behaviour requires the user to select the file, so the finding is scoped to that pre-existing
UI interaction and is NOT a consent bypass: no TCC-protected service was reached without user action",
never "TCC can be bypassed on macOS".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A tool exiting **`0`** with no observed effect | exit codes are not bypasses |
| A **SIP** change made via recovery mode or boot args | a configuration change with physical access |
| Writing to a **root-owned but unprotected** path | not a SIP-protected path |
| A binary that **never had** `com.apple.quarantine` | the attribute was absent, not bypassed |
| An entitlement **string in a plist** with an invalid signature | the entitlement is not enforced |
| A **user-consented** file selection reported as a TCC bypass | the consent is the control working |
| A **`sqlite3` write to TCC.db** as the mechanism | the host was already root-compromised; say so |
| A **sandbox escape** claimed without naming the profile's source | the profile defines the boundary |
| A LaunchAgent **present before the reboot** and absent after | not persistence |
| A Gatekeeper test done **offline**, reported against the live notary service | the service was not tested |
| A single **build's** result reported as general | version-scoped until a second build confirms |

**A stock-control refusal, an observed effect, a revert control, and a recorded build.** An exit code and
a recovery-mode configuration change are this family's two standard non-findings.

---

## 12. REMEDIATION REFERENCE — MACOS HARDENING ASSESSMENT

1. **Record the build, SIP, SSV, Gatekeeper policy, and TCC schema before drawing any conclusion, and repeat the test on a second build** - every mechanism in this file is version-conditional.
2. **Establish the stock refusal first and record its exact error string** - the error string identifies the layer, and without it a working command is indistinguishable from a protection that never applied.
3. **Distinguish a consent interaction from a consent bypass in the report, and never merge them** - a user-selected file dialog returning a scoped bookmark is the control working, not a failure.
4. **Distinguish a mechanism from a configuration change: recovery-mode, boot-arg, and `csrutil disable` are the latter and must be labelled as such** - reporting a configuration change as a bypass misstates the threat model.
5. **Revert the mechanism and confirm the refusal returns** - the causal control, and the one most often skipped.
6. **Test persistence across an actual reboot or re-login rather than assuming an agent survives** - a `LaunchAgent` observed only in a session is not persistence.
7. **Name the sandbox profile's source rather than "the sandbox", because the profile language is undocumented and version-dependent** - a compiled `.sb` and an entitlements-derived profile are different boundaries.
8. **Check the signature before citing an entitlement, because an unsigned binary's entitlement string demonstrates nothing** - `codesign -d --entitlements` plus a validation, not a plist reading.
9. **State the prerequisite honestly: physical access, an existing root compromise, or a user interaction** - each one changes the finding's severity completely.
10. **Report the privilege actually reached: root, a named TCC service, or a specific data set** - "the sandbox was escaped" without a named reach is unfalsifiable.
11. **Map each mechanism to its current Apple advisory status, because a bypass that Apple has patched is a historical finding and belongs in a different section of the report** - the reader's remediation decision depends on it.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [macos-process-injection](../macos-process-injection/SKILL.md) - the injection layer this bypass enables
- [linux-security-bypass](../linux-security-bypass/SKILL.md) - the sibling OS-hardening-bypass discipline
- [edr-bypass-techniques](../edr-bypass-techniques/SKILL.md) - the endpoint-detection counterpart
- [sandbox-escape-techniques](../sandbox-escape-techniques/SKILL.md) - the cross-platform isolation-escape context
- [binary-protection-bypass](../binary-protection-bypass/SKILL.md) - the code-signing and hardening-bypass methodology
