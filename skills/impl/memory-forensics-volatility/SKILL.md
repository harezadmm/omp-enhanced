---
name: memory-forensics-volatility
description: >-
  Memory forensics playbook using Volatility 2/3. Use when analyzing memory dumps for malware analysis, credential extraction, process investigation, code injection detection, and incident response timeline reconstruction.
---

# SKILL: Memory Forensics — Expert Analysis Playbook

> **AI LOAD INSTRUCTION**: Expert memory forensics techniques using Volatility 2 and 3. Covers memory acquisition, OS identification, process analysis (hidden process detection), network connections, DLL/module analysis, code injection detection (malfind), credential extraction, file carving, registry analysis, and timeline generation. Base models miss the Vol2/Vol3 command differences, malware indicator patterns, and Linux-specific memory analysis.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [traffic-analysis-pcap](../traffic-analysis-pcap/SKILL.md) for correlating network artefacts with memory findings
- [steganography-techniques](../steganography-techniques/SKILL.md) if hidden data suspected in extracted files
- [windows-privilege-escalation](../windows-privilege-escalation/SKILL.md) for understanding post-exploitation artefacts in memory

### Quick Reference

Also load [VOLATILITY_CHEATSHEET.md](./VOLATILITY_CHEATSHEET.md) when you need:
- Vol2 vs Vol3 command comparison table
- Common plugin sequences for specific investigation types

---

## 1. MEMORY ACQUISITION

### Linux

```bash
# LiME (Linux Memory Extractor) — kernel module
insmod lime.ko "path=/tmp/mem.lime format=lime"

# /proc/kcore (if available)
dd if=/proc/kcore of=/tmp/mem.raw bs=1M

# AVML (Microsoft's open-source)
./avml /tmp/mem.lime
```

### Windows

```bash
# WinPmem
winpmem_mini_x64.exe memdump.raw

# FTK Imager (GUI) — capture memory to file

# DumpIt (single-click memory dump)
DumpIt.exe

# Comae (MagnetRAM)
MagnetRAMCapture.exe /output memdump.raw
```

### Virtual Machines

```bash
# VMware: .vmem file in VM directory (suspend VM first)
# VirtualBox: VBoxManage debugvm "VM_NAME" dumpvmcore --filename mem.raw
# KVM/QEMU: virsh dump DOMAIN memdump --memory-only
# Hyper-V: checkpoint VM → inspect .bin files
```

---

## 2. VOLATILITY 2 vs 3

| Concept | Volatility 2 | Volatility 3 |
|---|---|---|
| Profile system | `--profile=Win10x64_19041` | Auto-detected (symbol tables) |
| Image info | `imageinfo` | `windows.info` / `linux.info` |
| Process list | `pslist` | `windows.pslist` |
| Network | `netscan` / `connections` | `windows.netscan` / `windows.netstat` |
| DLLs | `dlllist` | `windows.dlllist` |
| Injection | `malfind` | `windows.malfind` |
| Hashes | `hashdump` | `windows.hashdump` |
| Files | `filescan` | `windows.filescan` |
| Registry | `hivelist` / `printkey` | `windows.registry.hivelist` / `windows.registry.printkey` |
| Install | `pip2 install volatility` | `pip3 install volatility3` |

---

## 3. ANALYSIS METHODOLOGY

### Step 1: Identify OS

```bash
# Vol2
vol.py -f mem.raw imageinfo
vol.py -f mem.raw kdbgscan

# Vol3
vol -f mem.raw windows.info
vol -f mem.raw banners.Banners
```

### Step 2: Process Listing — Hidden Process Detection

```bash
# Vol2
vol.py -f mem.raw --profile=PROFILE pslist       # EPROCESS linked list
vol.py -f mem.raw --profile=PROFILE psscan       # pool tag scan (finds unlinked)
vol.py -f mem.raw --profile=PROFILE pstree       # parent-child hierarchy

# Vol3
vol -f mem.raw windows.pslist
vol -f mem.raw windows.psscan
vol -f mem.raw windows.pstree
```

**Red flags**: Process in `psscan` but not `pslist` = DKOM (Direct Kernel Object Manipulation) hiding.

### Step 3: Network Connections

```bash
# Vol2
vol.py -f mem.raw --profile=PROFILE netscan      # TCP/UDP endpoints
vol.py -f mem.raw --profile=PROFILE connections   # XP/2003 only
vol.py -f mem.raw --profile=PROFILE connscan      # closed connections

# Vol3
vol -f mem.raw windows.netscan
vol -f mem.raw windows.netstat
```

### Step 4: DLL / Module Analysis

```bash
# Vol2
vol.py -f mem.raw --profile=PROFILE dlllist -p PID
vol.py -f mem.raw --profile=PROFILE ldrmodules -p PID   # find unlinked DLLs

# Vol3
vol -f mem.raw windows.dlllist --pid PID
```

**Red flags**: DLL in `dlllist` but `False` in all three `ldrmodules` columns = reflective DLL injection.

### Step 5: Code Injection Detection (Malfind)

```bash
# Vol2
vol.py -f mem.raw --profile=PROFILE malfind -p PID
vol.py -f mem.raw --profile=PROFILE malfind -D /tmp/dump/   # dump injected sections

# Vol3
vol -f mem.raw windows.malfind --pid PID
```

**What malfind detects**: Memory regions with `PAGE_EXECUTE_READWRITE` that don't map to a file on disk — classic shellcode/injection indicator.

### Step 6: Credential Extraction

```bash
# Vol2
vol.py -f mem.raw --profile=PROFILE hashdump      # SAM hashes
vol.py -f mem.raw --profile=PROFILE lsadump       # LSA secrets
vol.py -f mem.raw --profile=PROFILE cachedump     # domain cached creds
vol.py -f mem.raw --profile=PROFILE mimikatz      # (plugin) plaintext creds

# Vol3
vol -f mem.raw windows.hashdump
vol -f mem.raw windows.lsadump
vol -f mem.raw windows.cachedump
```

### Step 7: File Extraction

```bash
# Vol2
vol.py -f mem.raw --profile=PROFILE filescan | grep -i "password\|secret\|flag"
vol.py -f mem.raw --profile=PROFILE dumpfiles -Q OFFSET -D /tmp/dump/

# Vol3
vol -f mem.raw windows.filescan
vol -f mem.raw windows.dumpfiles --virtaddr OFFSET
```

### Step 8: Registry Analysis

```bash
# Vol2
vol.py -f mem.raw --profile=PROFILE hivelist
vol.py -f mem.raw --profile=PROFILE printkey -K "Software\Microsoft\Windows\CurrentVersion\Run"
vol.py -f mem.raw --profile=PROFILE userassist    # program execution evidence

# Vol3
vol -f mem.raw windows.registry.hivelist
vol -f mem.raw windows.registry.printkey --key "Software\Microsoft\Windows\CurrentVersion\Run"
```

### Step 9: Command History

```bash
# Vol2
vol.py -f mem.raw --profile=PROFILE cmdscan       # cmd.exe history
vol.py -f mem.raw --profile=PROFILE consoles       # full console output

# Vol3
vol -f mem.raw windows.cmdline
```

### Step 10: Timeline Generation

```bash
# Vol2
vol.py -f mem.raw --profile=PROFILE timeliner --output=body --output-file=timeline.body
mactime -b timeline.body -d > timeline.csv

# Vol3
vol -f mem.raw timeliner.Timeliner
```

---

## 4. LINUX MEMORY ANALYSIS

```bash
# Vol2 (requires Linux profile)
vol.py -f mem.lime --profile=LinuxProfile linux_pslist
vol.py -f mem.lime --profile=LinuxProfile linux_pstree
vol.py -f mem.lime --profile=LinuxProfile linux_netstat
vol.py -f mem.lime --profile=LinuxProfile linux_bash        # bash history
vol.py -f mem.lime --profile=LinuxProfile linux_enumerate_files
vol.py -f mem.lime --profile=LinuxProfile linux_proc_maps -p PID
vol.py -f mem.lime --profile=LinuxProfile linux_malfind

# Vol3
vol -f mem.lime linux.pslist
vol -f mem.lime linux.pstree
vol -f mem.lime linux.bash
vol -f mem.lime linux.check_afinfo     # rootkit detection
vol -f mem.lime linux.check_syscall    # syscall hooking
vol -f mem.lime linux.tty_check        # TTY hooking
```

### Building Linux Profiles (Vol2)

```bash
cd volatility/tools/linux
make
# Creates module.dwarf + System.map → zip as profile
zip LinuxProfile.zip module.dwarf /boot/System.map-$(uname -r)
# Place in volatility/plugins/overlays/linux/
```

---

## 5. MALWARE INDICATORS IN MEMORY

| Indicator | Detection Method | What It Means |
|---|---|---|
| Process in psscan but not pslist | Compare pslist vs psscan | DKOM — process hiding |
| Unexpected parent-child | pstree analysis | e.g., svchost spawned by cmd.exe |
| MZ header in non-image memory | malfind | Reflective DLL / PE injection |
| RWX memory without backing file | malfind | Shellcode injection |
| DLL unlinked from all PEB lists | ldrmodules (all False) | Stealth DLL loading |
| svchost.exe not child of services.exe | pstree | Fake svchost (malware) |
| Unusual network connections | netscan + PID correlation | C2 communication |
| Hooking in SSDT/IDT | ssdt / idt plugins | Rootkit |
| Modified kernel objects | linux_check_syscall | Linux rootkit |

### Normal Parent-Child Relationships (Windows)

```
System (4)
└── smss.exe
    └── csrss.exe
    └── wininit.exe
        └── services.exe
            └── svchost.exe (multiple)
            └── spoolsv.exe
        └── lsass.exe
    └── winlogon.exe
        └── explorer.exe
            └── user applications
```

---

## 6. DECISION TREE

```
Memory dump acquired — need to analyze
│
├── What OS?
│   ├── Windows → vol imageinfo / windows.info (§3 Step 1)
│   └── Linux → build profile or use Vol3 auto-detect (§4)
│
├── Malware investigation?
│   ├── Check processes: pslist vs psscan (hidden?) (§3 Step 2)
│   ├── Check parent-child: pstree (suspicious spawning?) (§5)
│   ├── Check injections: malfind (RWX memory?) (§3 Step 5)
│   ├── Check DLLs: ldrmodules (unlinked?) (§3 Step 4)
│   ├── Check network: netscan (C2 connections?) (§3 Step 3)
│   └── Extract suspicious files: dumpfiles (§3 Step 7)
│
├── Credential recovery?
│   ├── SAM hashes → hashdump (§3 Step 6)
│   ├── LSA secrets → lsadump (§3 Step 6)
│   ├── Cached domain creds → cachedump (§3 Step 6)
│   └── Plaintext passwords → mimikatz plugin (§3 Step 6)
│
├── Incident timeline?
│   ├── timeliner for comprehensive timeline (§3 Step 10)
│   ├── cmdscan / consoles for command history (§3 Step 9)
│   ├── userassist for program execution (§3 Step 8)
│   └── Cross-reference with PCAP timeline (→ traffic-analysis-pcap)
│
├── CTF / flag hunting?
│   ├── filescan + grep for flag patterns (§3 Step 7)
│   ├── cmdscan for typed flags/passwords (§3 Step 9)
│   ├── Clipboard: clipboard plugin
│   ├── Screenshots: screenshot plugin
│   └── Environment vars: envars plugin
│
└── Linux-specific?
    ├── linux_bash for shell history (§4)
    ├── linux_check_syscall for rootkit (§4)
    └── linux_netstat for connections (§4)
```

---

## 7. CONFIRMING THE FINDING

Memory is the least reproducible evidence in the field, because **the capture changes the system it
captures, and the image is a moment that cannot be re-taken.** This table is what makes a memory claim
defensible.

| Step | Question | What it proves |
|---|---|---|
| 1 | Was the acquisition's **method and tool** recorded with its **hash**? | the image's provenance |
| 2 | Is the image **validated** (symbol/ISF availability, kernel version) before symbol use? | symbol errors fabricate findings |
| 3 | Did the artefact come from the image's **bytes**, or from the plugin's **display**? | a display is an interpretation |
| 4 | Is the reading **reproduced** in a second run, or with a second tool? | non-reproducibility is the norm here |
| 5 | Does the claim account for **volatility itself** - the system was running during acquisition? | live memory is inconsistent by construction |
| 6 | Is there a **control process** that should NOT appear, and does it? | a plugin lists many things; the claim is a subset |
| 7 | Does the claim name **what was read from the image's raw bytes**? | the hammer is not the evidence |

**A hashed, validated image, a reading reproduced independently, and an explicit statement about what the
acquisition's own liveness destroyed.** A Volatility plugin's table is an interpretation of a snapshot.

---

## 8. EXECUTION PRIMITIVES

The central discipline of this domain: **a memory image is a snapshot of a system that was still running,
so absence is not evidence of absence and the tool's table is not the artefact.**

### 7.1 The acquisition, and its provenance

```bash
# THE IMAGE'S PROVENANCE IS THE FINDING'S FOUNDATION. Record it BEFORE analysis.
IMG="${IMG:?the memory image}"
echo "=== 1. the image itself, and its hash ==="
sha256sum "$IMG" | tee /tmp/img.sha256
ls -la "$IMG"
file "$IMG"
cat <<'PROV'
  RECORD, AND PUT IN THE REPORT:
    the ACQUISITION TOOL and its version   (LiME, AVML, winpmem, DumpIt, a hypervisor snapshot)
    the FORMAT                             (raw/linear, LiME's own, a crash dump, a hibernation
                                            file, a VM snapshot - each is parsed differently)
    the HASH                               (taken AT ACQUISITION, and re-verified before every
                                            analysis run: an image that changed is not the evidence)
    the HOST IDENTITY as the SYSTEM STATED IT (the kernel version, the hostname from the image
                                            itself - NOT from your notes)
  AND THE CRITICAL CAVEAT THAT MUST APPEAR IN EVERY REPORT FROM THIS DOMAIN:
    A LIVE ACQUISITION IS NOT ATOMIC. The system continued to run while memory was copied, so:
      - a page read late may reflect a LATER state than a page read early
      - a structure can be INTERNALLY INCONSISTENT in the image, and this is EXPECTED, not a bug
      - lists can be mid-update, so a linked list may appear truncated or circular
    THEREFORE: 'the process was not in the list' is NOT proof the process never existed - and
    claiming otherwise is this family's central error.
PROV
echo
echo "=== 2. the hash re-verification, before EVERY run ==="
echo "  sha256sum -c /tmp/img.sha256   -> run this before each analysis session and record the result."
echo "  an unverified image makes every finding unreproducible, and the verification is one line."
echo
echo "=== 3. the symbol/ISF validation, which is where findings are FABRICATED ==="
cat <<'SYMBOLS'
  VOLATILITY NEEDS THE RIGHT SYMBOLS FOR THE IMAGE'S EXACT KERNEL, AND A MISMATCHED SYMBOL SET
  PRODUCES PLAUSIBLE-LOOKING BUT WRONG OUTPUT. THE CHECKS:
    - the kernel version FROM THE IMAGE, not from your notes (banners, version strings, a
      symbol search) - and it must MATCH the profile's version exactly
    - Volatility 2 uses a PROFILE (a zip keyed to the kernel); Volatility 3 uses an ISF JSON
    - an ISF can be generated (dwarf2json) FROM THE VMLINUX; record where it came from and its hash
    - IF A PLUGIN PRODUCES ODD OUTPUT - empty tables, absurd offsets, a flood of unresolved
      symbols - THE SYMBOLS ARE WRONG. That is NOT a finding about the target.
  THE CONTROL: run a plugin whose output you can INDEPENDENTLY verify (e.g. a boot-time plugin)
  and confirm its values are plausible BEFORE trusting any plugin that reports an anomaly.
SYMBOLS
echo
echo "=== 4. the two-tool rule for this domain ==="
echo "  reproduce any structural claim with a second independent reader where possible:"
echo "    volatility3 <-> a manual structure parse with a script over the raw bytes"
echo "    the image  <-> a second acquisition of the same host, if one exists (rarely)"
echo "  and record the plugin NAME, its VERSION, and the EXACT arguments for every table cited."
```

**A live acquisition is not atomic, so "the process was not in the list" is not proof it never existed.**
And a mismatched symbol set produces plausible-looking but wrong output — that is not a finding about the target.

### 7.2 The reading: the raw bytes versus the plugin's table

```bash
echo "=== THE PLUGIN'S TABLE IS AN INTERPRETATION. THE BYTES ARE THE EVIDENCE. ==="
cat <<'BYTES'
  FOR ANY CLAIM, STATE WHICH YOU HAVE:
    LEVEL 1: a plugin's TABLE row        -> a HYPOTHESIS about the image
    LEVEL 2: the STRUCTURE the plugin walked, with its address and its fields, re-read by you
    LEVEL 3: THE RAW BYTES at that offset, shown as hex (or a string) from the image

  A defensible finding reaches LEVEL 3 for the DECISIVE field, or clearly says it stopped at 2.
  EXAMPLE: 'a plugin listed a process named X' is level 1. Reading the process structure at the
  address the plugin gave, and showing the name field's BYTES, is level 3 - and it is a different
  quality of evidence, because it survives a challenge to the plugin's own logic.

  AND THE STRUCTURE-WALK CAVEATS, which must be stated when you claim a walk:
    - the linked list you walked may be MID-UPDATE (see the non-atomic caveat above)
    - an _EPROCESS/_task_struct's fields differ by kernel version; a field's OFFSET is version-specific
    - a pointer may be STALE: memory was freed and partially reused, so a plausible address can
      point at reused data. THIS IS THE COMMONEST ARTEFACT INTERPRETATION ERROR IN THE FIELD.
  THE DEFENCE: show the bytes, state the version, and where the structure's consistency can be
  checked (a magic value, a reference count, a back-pointer), CHECK IT AND SHOW IT.
BYTES
echo
echo "=== the artefact's own hash, and its extraction ==="
echo "  any carved artefact (a file, a key, a config) needs:"
echo "    the OFFSET in the image it came from, its LENGTH, its SHA256, and how it was carved"
echo "  and re-carve it a second way where possible: a hash that differs means the carve altered it."
echo
echo "=== THE VOLATILITY-SPECIFIC ANOMALIES, and what each one is NOT ==="
python3 - <<'PY'
A = [("a process with no parent in the list", "the parent exited, or is on a mid-update list", "NOT proof of a hidden process"),
     ("a process name with odd characters",   "a legitimate name, a rename, or REUSED memory",   "NOT proof of masquerading until bytes are read"),
     ("an injected-looking memory region",    "a JIT, a packed section, a legitimate RWX region", "NOT proof of injection without the region's contents"),
     ("a connection to an odd address",       "a CDN, a legit service, a stale socket",           "NOT proof of C2"),
     ("a command line containing a base64 blob","a legitimate tool, an installer, a script",      "NOT proof of malice"),
     ("no process for a PID you expected",    "the NON-ATOMIC acquisition, or a short-lived proc", "NOT proof of tampering")]
print("%-42s %-44s %s" % ("observation","benign explanation that must be excluded","what it does NOT prove"))
for a,b,c in A: print("%-42s %-44s %s" % (a,b,c))
print()
print("  FOR EACH ROW THE PROCEDURE IS THE SAME: state the benign explanation, EXCLUDE IT with bytes,")
print("  and only then report the anomaly. An anomaly reported without its excluded alternatives is")
print("  the single most common defect in memory-forensics findings.")
PY
```

**Every anomaly needs its benign alternative excluded with bytes before it is reported** — a process with
no parent, an odd name, an RWX region, or an odd address all have ordinary explanations.

### 7.3 Correlation, and the goal

```bash
echo "=== MEMORY IS ONE SOURCE. A FINDING NEEDS A SECOND, INDEPENDENT ONE. ==="
cat <<'CORRELATE'
  THE CORRELATION PAIRS THAT VALIDATE A MEMORY CLAIM (and what each one proves):
    memory <-> DISK       : a process's image on disk (the executable's hash vs the mapped file)
    memory <-> NETWORK    : a connection in memory vs the capture's flow (see traffic-analysis-pcap)
    memory <-> LOG        : a logon or a service event vs the session in memory
    memory <-> TIMELINE   : an object's timestamps vs the file system's own
  IN EACH PAIR, THE MEMORY SIDE MUST AGREE WITH THE OTHER ON A SPECIFIC OBSERVABLE, and the
  observable must be NAMED. 'It is consistent' is not an agreement unless you say what agreed.

  AND THE ANTI-CORRELATION, which is often the strongest evidence:
    A PROCESS IN MEMORY WITH NO CORRESPONDING FILE ON DISK, or a file on disk with NO PROCESS
    that ever mapped it. THAT PAIR is a strong finding - and it REQUIRES the disk-side check, so
    the finding is the PAIR, not the memory observation alone.
    THE CONTROL: the same check on a BENIGN process in the SAME image, showing it DOES correspond
    to a file on disk. Without that control, your 'no file on disk' may be an artefact of the
    acquisition or of your disk timeline's own gaps.
CORRELATE
echo
echo "=== THE GOAL, and the evidence each needs ==="
cat <<'GOAL'
  'we found a process named X'           -> NOT a finding; it names no anomaly
  'a process exists with no parent'       -> requires the benign alternatives EXCLUDED
  'a region is RWX and contains code'     -> requires the REGION'S BYTES
  'a credential/secret was in memory'     -> requires the KEY/CREDENTIAL's bytes, its offset, and
                                             a statement about the credential's VALIDITY
  'a process has no file on disk'         -> requires the DISK-SIDE check and the benign control
  'the timeline shows a sequence'         -> requires ANCHORED timestamps (see traffic-analysis-pcap)
  NAME IT. 'Suspicious memory artefacts were found' is a statement about the analyst, not the target.
GOAL
echo
echo "=== the end-to-end harness ==="
python3 - <<'PY'
print("=== MEMORY FORENSICS ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the acquisition TOOL, its version, and the FORMAT are recorded",
  "each format parses differently, and the tool constrains the image's fidelity"),
 ("the image's HASH was taken at acquisition and RE-VERIFIED before every analysis run",
  "an unverified image makes every finding unreproducible"),
 ("the host identity comes FROM THE IMAGE, not from the analyst's notes",
  "the image is the source of truth about itself"),
 ("the NON-ATOMIC caveat is stated: the system ran during acquisition",
  "absence from a list is not evidence of absence"),
 ("the SYMBOL/ISF set was validated against the image's exact kernel version",
  "a mismatch produces plausible but wrong output, and that is not a target finding"),
 ("a plugin with INDEPENDENTLY VERIFIABLE output was run first, as the symbol sanity control",
  "odd output usually means wrong symbols, not a compromised host"),
 ("the plugin name, version, and EXACT arguments are recorded for every table cited",
  "the reading must be reproducible by a second analyst"),
 ("the decisive field was carried to the IMAGE'S RAW BYTES, or the claim says it stopped short",
  "a plugin's display is an interpretation"),
 ("for a structure walk: the version-specific offsets and any consistency check are shown",
  "pointers may be stale and memory may be reused"),
 ("every anomaly carries its EXCLUDED benign alternatives",
  "an anomaly without excluded alternatives is the commonest defect in this family"),
 ("carved artefacts have their offset, length, hash, and carving method recorded",
  "and the hash must survive a second carve"),
 ("each memory claim is correlated to a SECOND, independent source with a NAMED observable",
  "'it is consistent' names nothing"),
 ("the memory-with-no-file-on-disk case includes the BENIGN control process",
  "without it, the observation may be an acquisition artefact"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  acquisition: the tool, the format, the hash, and the non-atomic caveat")
print("  symbols    : the kernel version, the profile/ISF origin, and its hash")
print("  reading    : the plugin and its arguments, and the raw bytes behind the decisive field")
print("  anomaly    : the observation with its benign alternatives EXCLUDED")
print("  artefact   : offset, length, hash, carving method")
print("  correlation: the second source, the named observable, and the disk-side control")
PY
```

---

## 9. EVIDENCE STANDARD
| Item | Why |
|---|---|
| The **acquisition method** (live, hibernation file, VM snapshot, cold boot) and the tool | a live acquisition is not atomic, and the method bounds every claim |
| The **image hash**, and the hash of the memory region a finding comes from | a page can be overwritten during a live capture |
| The **symbol table / ISF** used, with its version and a provenance hash | a symbol mismatch produces plausible, wrong output |
| The **plugin and its version**, with the raw output retained | a plugin's table is a Level-1 interpretation |
| The **raw bytes** for any structure a finding depends on | the table and the bytes can disagree |
| The **benign alternative** considered for every anomaly | an unparented process, an RWX region, and an odd address all have innocent explanations |
| What the image **cannot show**: unallocated-then-reused pages, a mid-capture change, an absent process | absence is not evidence of absence |

### Analysis failures — how they mislead

| Failure | How it misleads |
|---|---|
| **Absence from a plugin's list** read as absence from the system | volatility walks a linked list; a hidden process is off it |
| A **symbol mismatch** producing output anyway | the output looks plausible and is wrong, and it is not a finding about the target |
| A **Level-1 table** cited as the evidence | the plugin is an interpretation; the structure is the artefact |
| A **live acquisition** treated as a consistent snapshot | pages change during the capture, so a contradiction may be an artefact |
| **Unallocated memory** read as current state | a freed page is a past state, and its presence proves nothing about now |
| An **anomaly reported without its benign alternative** | many anomalies are normal for that OS build |
| A **timeline** built from memory timestamps alone | memory timestamps and disk timestamps disagree |

| Item | Why |
|---|---|
| The image's hash and the acquisition method, with what the method cannot capture | the reproducibility and the limits, in one place |
| The **symbol table / ISF** used, its version, and its provenance | a mismatch fabricates findings |
| The **plugin, its version, and the raw output it produced** | the interpretation, retained so it can be re-derived |
| The **raw structure bytes** the finding rests on | the artefact behind the table |
| The **benign alternative** examined and excluded, with its exclusion test | an unexplained anomaly is a question, not a finding |
| The **corroborating artefact** on disk, in a log, or in traffic | memory alone is rarely sufficient |
| The **explicit negative bound** | absence from a list is not absence from the system |

**The plugin table is a hypothesis and the raw bytes are the artefact** — and because a live acquisition is
not atomic, absence is never evidence of absence, so every anomaly is shown to lack its benign explanation.

---

## 10. REMEDIATION REFERENCE

Memory evidence usually drives **detection and response improvements**, not a code fix.

1. **Convert the finding into a detection.** An injected region is worth more as a memory-scanning rule
   than as a single reported artefact; name the rule's condition.
2. **Fix the acquisition before the analysis.** A non-atomic live capture is a process problem: prefer a
   hypervisor snapshot, or hibernate, and record which method a future response should use.
3. **Name the persistence mechanism, not the process.** The durable fix is the run key, the service, or
   the scheduled task, not killing a PID.
4. **State the corroboration required.** A memory-only finding should say which disk or log artefact would
   confirm it, and whether that artefact was checked.
5. **Record the limits of the method.** A memory image cannot show what was never resident, and a fix that
   assumes full coverage of that image is over-claiming.

---

## 11. RELATED SIBLINGS - LOAD TOGETHER
- [traffic-analysis-pcap](../traffic-analysis-pcap/SKILL.md) - the network side a memory claim is correlated against
- [data-breach-correlation-workflows](../data-breach-correlation-workflows/SKILL.md) - the provenance discipline this evidence feeds
- [malware-development-workflow](../malware-development-workflow/SKILL.md) - what an injected region's contents indicate
- [anti-debugging-techniques](../anti-debugging-techniques/SKILL.md) - the evasions that make a memory table incomplete
- [ebpf-attacks](../ebpf-attacks/SKILL.md) - the kernel-layer visibility that a listed table cannot see
