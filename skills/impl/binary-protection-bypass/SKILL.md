---
name: binary-protection-bypass
description: >-
  Binary protection bypass playbook. Use when identifying and bypassing ASLR, PIE, NX/DEP, stack canary, RELRO, FORTIFY_SOURCE, CET, and MTE protections in ELF binaries to enable exploitation.
---

# SKILL: Binary Protection Bypass — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert binary protection identification and bypass techniques. Covers ASLR, PIE, NX, RELRO, canary, FORTIFY_SOURCE, stack clash, CET shadow stack, and ARM MTE. Each protection is paired with its bypass methods and required primitives. Distilled from ctf-wiki mitigation sections and real-world exploitation. Base models often confuse which protections block which attacks and miss the combinatorial effect of multiple protections.

## 0. RELATED ROUTING

- [stack-overflow-and-rop](../stack-overflow-and-rop/SKILL.md) — ROP chains to bypass NX, ret2libc for ASLR bypass
- [format-string-exploitation](../format-string-exploitation/SKILL.md) — primary method for leaking canary, PIE, libc addresses
- [heap-exploitation](../heap-exploitation/SKILL.md) — heap attacks for RELRO bypass (when GOT is read-only)
- [arbitrary-write-to-rce](../arbitrary-write-to-rce/SKILL.md) — what to overwrite when GOT is protected by RELRO

### Advanced Reference

Load [PROTECTION_BYPASS_MATRIX.md](./PROTECTION_BYPASS_MATRIX.md) for comprehensive protection × bypass × primitive matrix.

---

## 1. PROTECTION IDENTIFICATION

```bash
$ checksec ./binary
[*] '/path/to/binary'
    Arch:     amd64-64-little
    RELRO:    Full RELRO          ← GOT read-only
    Stack:    Canary found        ← stack canary enabled
    NX:       NX enabled          ← stack not executable
    PIE:      PIE enabled         ← position-independent code
    FORTIFY:  Enabled             ← fortified libc functions
```

### Quick Identification Table

| Protection | Check Command | Binary Indicator |
|---|---|---|
| ASLR | `cat /proc/sys/kernel/randomize_va_space` | OS-level (0=off, 1=partial, 2=full) |
| PIE | `checksec` or `readelf -h` (Type: DYN) | Binary compiled with `-pie` |
| NX | `checksec` or `readelf -l` (no RWE segment) | `gcc -z noexecstack` (default on) |
| Canary | `checksec` or look for `__stack_chk_fail@plt` | `gcc -fstack-protector-all` |
| Partial RELRO | `readelf -l` (GNU_RELRO segment, `.got.plt` writable) | `gcc -Wl,-z,relro` |
| Full RELRO | `readelf -l` + `.got` section read-only | `gcc -Wl,-z,relro,-z,now` |
| FORTIFY | Presence of `__printf_chk`, `__memcpy_chk` etc. | `gcc -D_FORTIFY_SOURCE=2` |

---

## 2. ASLR BYPASS

ASLR randomizes base addresses of stack, heap, libc, and mmap regions at each execution.

| Bypass Method | Required Primitive | Notes |
|---|---|---|
| Information leak | Any read primitive (format string, OOB read, UAF) | Leak libc/stack/heap address → calculate base |
| Partial overwrite | Write primitive (limited length) | Overwrite last 1-2 bytes (page offset fixed) |
| Brute force (32-bit) | Ability to reconnect/retry | ~256–4096 attempts (8-12 bits entropy) |
| Return-to-PLT | Stack overflow | PLT addresses are at fixed offset from binary base (if no PIE) |
| ret2dlresolve | Stack overflow + write primitive | Resolve arbitrary function without knowing libc base |
| Format string leak | Format string vulnerability | `%N$p` for stack/libc/heap addresses |
| Stack reading | Byte-by-byte (fork server) | Read stack byte-by-byte via crash oracle |

### ASLR Entropy (x86-64 Linux)

| Region | Entropy (bits) | Positions |
|---|---|---|
| Stack | 22 | ~4M |
| mmap / libc | 28 | ~256M |
| Heap (brk) | 13 | ~8K |
| PIE binary | 28 | ~256M |

---

## 3. PIE BYPASS

PIE (Position Independent Executable) randomizes the binary's own code/data base address.

| Bypass Method | Required Primitive | Notes |
|---|---|---|
| Information leak | Read return address from stack | PIE base = leaked_addr - known_offset |
| Partial overwrite | One-byte or two-byte write | Last 12 bits of page offset are fixed |
| Format string leak | Format string vulnerability | `%N$p` where N points to .text return address |
| Relative addressing | Knowledge of binary layout | If you know relative offsets, only need one leak |

### Partial Overwrite Details

```
PIE binary loaded at: 0x555555554000 (example)
Function at offset 0x1234: 0x555555555234

Overwrite return address last 2 bytes: 0x?234 → 0x?XXX
Unknown: bits 12-15 (one nibble = 4 bits = 16 possibilities)
Success rate: 1/16 per attempt
```

---

## 4. NX / DEP BYPASS

NX (No-eXecute) / DEP (Data Execution Prevention) prevents execution of code on the stack/heap.

| Bypass Method | Detail |
|---|---|
| ROP (Return-Oriented Programming) | Chain existing code gadgets ending in `ret` |
| ret2libc | Call libc functions (system, execve) directly |
| ret2csu | Use `__libc_csu_init` gadgets for controlled function calls |
| ret2dlresolve | Forge dynamic linker structures to resolve arbitrary functions |
| SROP | Use sigreturn to set all registers from fake signal frame |
| mprotect ROP | Chain mprotect(addr, size, PROT_RWX) → make page executable → jump to shellcode |
| JIT spray | In JIT environments (V8, etc.), create executable code via JIT compiler |

### mprotect Chain

```python
# Make stack executable, then jump to shellcode
rop = b'A' * offset
rop += p64(pop_rdi) + p64(stack_page)     # page-aligned address
rop += p64(pop_rsi) + p64(0x1000)         # size
rop += p64(pop_rdx) + p64(7)              # PROT_READ|PROT_WRITE|PROT_EXEC
rop += p64(mprotect_addr)
rop += p64(shellcode_addr)                 # jump to shellcode on now-executable stack
```

---

## 5. RELRO BYPASS

| RELRO Level | GOT Status | Bypass |
|---|---|---|
| No RELRO | GOT fully writable | Direct GOT overwrite |
| Partial RELRO | `.got.plt` writable (lazy binding) | GOT overwrite still works |
| Full RELRO | All GOT entries resolved at load, GOT read-only | Cannot write GOT → target other structures |

### Full RELRO Alternative Targets

| Target | When | How |
|---|---|---|
| `__malloc_hook` | glibc < 2.34 | Overwrite with one_gadget |
| `__free_hook` | glibc < 2.34 | Overwrite with `system`, trigger `free("/bin/sh")` |
| `_IO_FILE vtable` | Any glibc | FSOP / vtable hijack |
| `__exit_funcs` | Any glibc | Overwrite exit handler list |
| `TLS_dtor_list` | glibc ≥ 2.34 | Thread-local destructor list (needs pointer guard) |
| `.fini_array` | If writable | Overwrite destructor function pointers |
| Stack return address | Direct stack write | Overwrite return address for ROP |

See [arbitrary-write-to-rce](../arbitrary-write-to-rce/SKILL.md) for comprehensive target list.

---

## 6. CANARY BYPASS

| Method | Condition | Detail |
|---|---|---|
| Format string leak | printf(user_input) | `%N$p` to read canary from stack |
| Brute-force | fork() server (canary persists in child) | Byte-by-byte: 256 × (canary_size-1) attempts |
| Stack reading | Partial overwrite / info leak | Overwrite canary's null byte, leak via output |
| Thread canary overwrite | Overflow reaches TLS | Canary at `fs:[0x28]`; overflow past buffer to TLS → overwrite canary with known value |
| Canary-relative overwrite | Overflow after canary but before return addr | Skip canary, only overwrite return address (rare layout) |
| Heap-based | Vulnerability is on heap, not stack | Canary only protects stack |
| __stack_chk_fail GOT overwrite | Partial RELRO | Overwrite `__stack_chk_fail@GOT` to point to harmless function → canary check passes |

### Canary Format

```
x86:    0x00XXXXXX (4 bytes, leading null byte)
x86-64: 0x00XXXXXXXXXXXXXX (8 bytes, leading null byte)
```

The leading `\x00` prevents string operations from accidentally reading the canary.

---

## 7. FORTIFY_SOURCE BYPASS

`_FORTIFY_SOURCE=2` adds buffer size checking and restricts format string operations.

| Fortified Function | Restriction | Bypass |
|---|---|---|
| `__printf_chk` | `%n` with positional args (`%N$n`) forbidden | Use non-positional `%n` or `%hn` chain |
| `__memcpy_chk` | Destination buffer size checked | Use heap overflow instead of stack |
| `__strcpy_chk` | Same | |
| `__read_chk` | Read size checked against buffer | |

### Format String with FORTIFY_SOURCE

```python
# %1$n is blocked by __printf_chk
# But sequential (non-positional) %n may still work:
# Print exact byte count, then %hn — must be very precise
# Or: find unfortified printf in binary/libc via ROP
```

---

## 8. CET (Control-flow Enforcement Technology)

Intel CET adds two mechanisms:

### Shadow Stack

- Hardware-maintained copy of return addresses
- On `ret`, CPU checks shadow stack matches actual stack
- Mismatch → `#CP` fault (control protection exception)

| Impact | Detail |
|---|---|
| ROP blocked | Return address overwrite detected on `ret` |
| JOP possible | `jmp [reg]` not checked by shadow stack |
| COP possible | `call [reg]` pushes to shadow stack but target validated by IBT |

### Indirect Branch Tracking (IBT)

- Indirect `jmp`/`call` must land on `ENDBR64` instruction
- Non-ENDBR landing → `#CP` fault

**Bypass**: 
- Data-only attacks (don't change control flow)
- Find valid ENDBR gadgets that chain into useful operations
- JOP with ENDBR-prefixed gadgets
- Target structures outside CFI scope (modprobe_path, function pointer arrays)

---

## 9. MTE (Memory Tagging Extension, ARM)

ARM MTE assigns 4-bit tags to memory pointers and allocations. Tag mismatch = fault.

| Aspect | Detail |
|---|---|
| Tag bits | 4 bits in pointer (bits 56-59) = 16 possible tags |
| Granule | 16 bytes (each 16-byte granule has one tag) |
| Check | Load/store: pointer tag must match memory tag |
| Probabilistic | Random tag → 1/16 chance attacker guesses correctly |

### Bypass Approaches

| Method | Success Rate |
|---|---|
| Brute-force | 1/16 per attempt (6.25%) |
| Tag oracle | Side-channel to determine tag (timing, error messages) |
| In-bounds exploit | Stay within same tagged region (use relative offsets) |
| Tag bypass gadget | Use `LDGM`/`STGM` instructions if accessible |
| Speculative execution | Spectre-style bypass of tag check |

---

## 10. DECISION TREE

```
Binary analysis: checksec output
├── NX disabled?
│   └── Shellcode on stack/heap (simplest path)
│
├── NX enabled (standard modern binary)?
│   ├── Need code execution → ROP/ret2libc
│   │
│   ├── Canary enabled?
│   │   ├── fork server? → byte-by-byte brute-force
│   │   ├── Format string? → leak canary via %p
│   │   ├── Heap vuln? → canary doesn't protect heap
│   │   └── Partial RELRO? → overwrite __stack_chk_fail@GOT
│   │
│   ├── PIE enabled?
│   │   ├── Format string? → leak .text address → PIE base
│   │   ├── Partial overwrite → last 12 bits fixed (1/16 brute-force)
│   │   └── OOB read? → leak code pointer
│   │
│   ├── ASLR enabled?
│   │   ├── Info leak available → leak libc base
│   │   ├── No leak → ret2dlresolve or SROP
│   │   ├── 32-bit? → brute-force feasible (~4096 attempts)
│   │   └── Return-to-PLT (no libc base needed for PLT calls)
│   │
│   ├── RELRO level?
│   │   ├── None/Partial → GOT overwrite
│   │   └── Full → alternative targets:
│   │       ├── glibc < 2.34 → __malloc_hook / __free_hook
│   │       ├── glibc ≥ 2.34 → _IO_FILE / exit_funcs / TLS_dtor_list
│   │       ├── .fini_array (if writable)
│   │       └── Stack return address
│   │
│   └── FORTIFY_SOURCE?
│       ├── Blocks positional %n → use sequential %n or heap exploit
│       └── Blocks buffer overflows in fortified functions → use unfortified paths
│
├── CET (shadow stack)?
│   ├── ROP blocked → data-only attack or JOP
│   └── ENDBR-gadget chaining
│
└── MTE (ARM)?
    ├── 1/16 brute-force
    └── Stay in-bounds for relative corruption
```

---

## 11. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Which mitigations are **actually on**, read from the binary and the kernel, not assumed? | the ledger |
| 2 | Which did you **bypass**, and with what **artefact** (a leak, a value, a writable target)? | an unartefacted bypass is an overstatement |
| 3 | Was the bypass demonstrated on the **same build** the report names? | build-specific |
| 4 | Was there a **control**: the same payload against a build where the mitigation IS enforced? | the mitigation's own control |
| 5 | Did the bypass reach a **goal** - a captured output? | a bypass is intermediate |
| 6 | Does the technique **transfer** to the deployed configuration, or only to your dev build? | scope |

**A mitigation ledger, an artefact per claimed bypass, and a goal.** "Bypassed ASLR" without a leaked
address is an unsupported claim, and this is the family's most common overstatement.

---

## 12. EXECUTION PRIMITIVES

A bypass finding is proven by **a per-mitigation ledger, an artefact attached to each claimed bypass, and
an enforced-control run where the mitigation actually stops you**. A claim without its artefact is an
overstatement.

### 11.1 The ledger, read from the artefacts rather than assumed

```bash
# THE LEDGER COMES FROM THE FILE AND THE KERNEL, not from memory.
BIN="${1:-./target}"
echo "=== 1. THE BINARY-LEVEL LEDGER, from checksec and the ELF itself ==="
checksec --file="$BIN" 2>/dev/null || pwn checksec "$BIN"
echo
echo "=== 2. THE ELF-LEVEL CONFIRMATION, read directly, so nothing is assumed ==="
readelf -h "$BIN" | grep -E 'Type:|Machine:'
echo "  Type: DYN with an INTERP segment = PIE. Type: EXEC = no PIE."
readelf -l "$BIN" | grep -E 'GNU_STACK|GNU_RELRO'
echo "  GNU_STACK RWE = executable stack. GNU_RELRO present = RELRO at least partial."
readelf -d "$BIN" | grep -E 'BIND_NOW|FLAGS' | head -5
echo "  BIND_NOW = FULL RELRO. Its absence with GNU_RELRO = PARTIAL RELRO."
echo
echo "=== 3. THE SYMBOLS THAT REVEAL THE COMPILER FLAGS ==="
for s in __stack_chk_fail __stack_chk_guard __fortify_fail _chk; do
  printf '  %-24s ' "$s"
  nm -D "$BIN" 2>/dev/null | grep -q "$s" && echo "PRESENT -> the corresponding protection is ON" || echo "absent"
done
echo
echo "=== 4. THE KERNEL-LEVEL LEDGER, which checksec does not show ==="
cat /proc/sys/kernel/randomize_va_space | sed 's/^/  randomize_va_space: /'
grep -o -m1 -E 'smep|smap|ibt|shstk' /proc/cpuinfo | sort -u | tr '\n' ' '; echo "  <- CPU features"
cat /sys/devices/system/cpu/vulnerabilities/* 2>/dev/null | head -3
echo
echo "=== THE LEDGER TABLE THE REPORT SHOULD CONTAIN ==="
cat <<'TABLE'
  mitigation    | state                                   | how to read it
  --------------|-----------------------------------------|--------------------------------
  NX            | GNU_STACK flags, RWE vs RW             | readelf -l
  Canary        | __stack_chk_fail present                | nm -D
  PIE           | ELF type DYN + INTERP                  | readelf -h/-l
  RELRO         | GNU_RELRO + BIND_NOW                    | readelf -l/-d
  FORTIFY       | _chk symbols, __fortify_fail            | nm -D
  ASLR          | /proc/sys/kernel/randomize_va_space     | cat
  CET           | ibt/shstk in cpuinfo + GNU_PROPERTY     | cpuinfo, readelf -n
  MTE (ARM)     | the HWCAP and the build's tag support   | /proc/cpuinfo, readelf -n
TABLE
echo
echo "=== THE CONTROL: A DELIBERATELY UNPROTECTED BUILD ==="
echo "  build the same source with -fno-stack-protector -no-pie -Wl,-z,norelro and run BOTH."
echo "  a bypass that works on both proves nothing about the mitigation. The DIFFERENCE is the finding."
```

**The unprotected control build is what isolates a bypass.** A technique that works on both builds proves
nothing about the mitigation, and the difference between them is the finding.

### 11.2 ASLR and PIE: the leak is the artefact

```python
from pwn import *
context.log_level = 'error'
context.arch = 'amd64'
elf = ELF('./target')

def leak_code_and_libc(addr_that_echoes):
    """ASLR and PIE bypasses are the SAME question: did you obtain and RESOLVE an address?"""
    p = process('./target')
    # stage 1: leak a code address (defeats PIE)
    p.sendline(b'%7$p')                      # the offset is measured elsewhere; this is the shape
    line = p.recvline().strip()
    code_leak = int(line, 16)
    elf.address = code_leak - elf.symbols['the_leaking_function']
    assert elf.address & 0xfff == 0, "the code base is not page-aligned - the leak did not resolve"
    print(f"  code leak {hex(code_leak)} -> elf base {hex(elf.address)} (page-aligned)")
    p.close()

print("=== THE ARTEFACT FOR AN ASLR/PIE CLAIM ===")
print("  1. the LEAKED ADDRESS, printed")
print("  2. the RESOLVED BASE, asserted PAGE-ALIGNED")
print("  3. the base DIFFERING across process restarts (proving ASLR is on) ")
print("  all three, or 'bypassed ASLR' is unsupported.")
print()
print("=== THE CONTROL ===")
print("  run with `setarch -R ./target` (ASLR off): the base must be CONSTANT across runs.")
print("  if the base is constant WITH ASLR on, then either ASLR is off or your leak is fake.")
print()
print("=== THE RELIABILITY QUESTION, which ASLR makes mandatory ===")
print("  a leaked base is 100% reliable BECAUSE the leak reads the actual runtime value.")
print("  an UNLEAKED brute-force is not: report the N of M and the guesses-per-success.")
```

**A leak is the artefact for both ASLR and PIE, and it needs the resolved base asserted page-aligned plus
a base that differs across restarts.** An unleaked brute-force needs its N of M and guesses-per-success.

### 11.3 NX, RELRO, canary, and FORTIFY: each has its own artefact

```bash
cat <<'ARTEFACTS'
NX / DEP
  the artefact  : a chain that uses CODE the process already maps, not injected shellcode
  the control   : the same payload as SHELLCODE on the stack must fault. If it does NOT fault, NX is
                  OFF for that mapping and the 'bypass' is unnecessary - say so.
  the trap      : an RWE stack (GNU_STACK RWE) means no NX to bypass at all.

CANARY
  the artefact  : the LEAKED CANARY VALUE, printed, with its source (a format string, a partial
                  overflow that stops before the canary, or a fork-server brute force)
  the control   : an overflow that overwrites the canary with a WRONG value must abort at
                  __stack_chk_fail. That abort IS the control that the canary is on.
  the trap      : a 'canary bypass' via a partial overwrite changes the canary's LOW BYTES only;
                  report WHICH bytes you controlled and why it did not trip.
  the fork trap : a fork-server brute force is only viable because the parent's canary is INHERITED.
                  Verify with `strace -f` that the child does not re-randomise it.

RELRO
  the artefact  : the target you wrote instead, e.g. __free_hook or an _IO_FILE field, with its read-back
  the control   : the SAME write to .got.plt on a FULL-RELRO build must FAULT. That fault is the control.
  the trap      : partial RELRO leaves .got.plt writable BEFORE the first call resolves the slot;
                  CONFIRM the slot is unresolved at the time of your write.

FORTIFY_SOURCE
  the artefact  : a build with -D_FORTIFY_SOURCE=2 where the OVERFLOW IS COMPILED AWAY (a __chk call)
  the control   : the SAME source without FORTIFY must overflow. The DIFFERENCE is the finding's scope.
  the trap      : FORTIFY is a COMPILE-TIME mitigation. Its 'bypass' is mostly 'the call site that
                  exists is a different, unchecked one'. Report the unchecked call site.
ARTEFACTS
echo
echo "=== each of these is a MEASUREMENT. Run the control listed for the one you claim. ==="
```

**Each mitigation has its own artefact and its own control, and each control is an observation of the
mitigation working.** The canary's control is the abort at `__stack_chk_fail`; RELRO's is the fault on a
full-RELRO GOT write.

### 11.4 CET and MTE: the modern constraints

```bash
echo "=== CET (x86) — the shadow stack and the indirect-branch tracker ==="
cat <<'CET'
  IBT  (indirect branch tracking) constrains INDIRECT CALL/JMP targets: the target must begin with
       ENDBR64. A ROP/JOP chain that jumps to a mid-function gadget FAULTS under IBT.
  SHSTK (shadow stack) means a RETURN address is verified against a second, protected stack. A plain
       ret-based ROP chain FAULTS under SHSTK.

HOW TO SEE WHETHER IT IS ACTIVE:
  readelf -n ./target | grep -A2 'GNU_PROPERTY'      -> the binary's CET declaration
  grep -o -m1 -E 'ibt|shstk' /proc/cpuinfo           -> the CPU's support
  grep -i shadow /proc/cpuinfo                       -> often listed as 'user_shstk'
  dmesg | grep -i -E 'cet|shstk'                     -> whether the kernel enabled it
  ACTIVE requires BOTH the binary's declaration AND the CPU's support AND the kernel's enablement.

BYPASSES, and their artefacts:
  IBT       : target a gadget that STARTS with ENDBR64, or land on a legitimate ENDBR64 sequence,
              or use a CALL-oriented chain. The artefact is the gadget list, with each entry shown
              to be ENDBR64-prefixed or reached by a permitted branch.
  SHSTK     : a return-address write is checked. Bypass routes are: a non-RET control-flow transfer
              (a CALL or an indirect JMP), or a legitimate unwinding path that writes the shadow
              stack itself. The artefact is the shadow-stack value you caused, read back.

THE CONTROL: on a build or host WITHOUT CET, the same payload must succeed but with the SAME final
goal. If the payload only works on the CET-off host, the finding is host-configuration-scoped.
CET
echo
echo "=== MTE (ARM) ==="
cat <<'MTE'
  MTE tags every allocation; a pointer whose tag does not match its memory faults. The classic
  heap-overflow exploitation is therefore often blocked at the moment of the out-of-bounds access.

  HOW TO SEE IT: readelf -n on an Android binary, and /proc/cpuinfo's 'mte' HWCAP on Linux.
  BYPASSES: a tag disclosure (a use-after-free that keeps the tag valid), a tag-0/zero-tag region
  (the stack and some globals are untagged), or a non-tagged allocator path.
  THE ARTEFACT: the value whose tag you obtained, and the fault message with and without it.
  THE CONTROL: the SAME access with a WRONG tag must fault with 'SEGV_MTEAERR' or similar.
MTE
```

**For CET and MTE, active requires the binary's declaration AND the CPU's support AND the kernel's
enablement.** A payload working only on a CET-off host is host-configuration-scoped.

### 11.5 The end-to-end harness

```bash
python3 - <<'PY'
print("=== PROTECTION BYPASS ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the ledger was read from readelf/nm/checksec, not assumed, and includes the KERNEL-level rows",
  "checksec alone misses ASLR, CET, and MTE"),
 ("a DELIBERATELY UNPROTECTED build of the same source was built and run as the control",
  "a technique working on both proves nothing about the mitigation"),
 ("for an ASLR/PIE claim: the LEAK address AND the page-aligned resolved base are printed",
  "an unartefacted claim is an overstatement"),
 ("the base was shown DIFFERING across restarts, with setarch -R as the control",
  "otherwise ASLR may simply be off"),
 ("for a canary claim: the LEAKED VALUE is printed, and the wrong-value abort is the control",
  "the abort is the observation that the canary is on"),
 ("for a RELRO claim: the alternative target is named with its read-back, and the full-RELRO fault is the control",
  "the fault is the mitigation working"),
 ("for an NX claim: the payload uses existing code, and the stack-shellcode fault is the control",
  "the fault is the observation"),
 ("for a FORTIFY claim: the fortified build and the unfortified control differ, and the difference is stated",
  "FORTIFY is compile-time; the scope follows"),
 ("for a CET claim: the binary's GNU_PROPERTY, the CPU's support, AND the kernel's enablement were all checked",
  "ACTIVE requires all three"),
 ("for an MTE claim: the wrong-tag fault is the control",
  "the fault proves the tag check is active"),
 ("the GOAL was proven by a captured command output, and the finding's SCOPE is stated",
  "a bypass is intermediate, and its scope decides who must act"),
]
for n, how in CHECKS: print("  [ ] %-72s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  ledger    : the table of mitigations, read from artefacts, including kernel-level rows")
print("  bypassed  : which ones, each with its ARTEFACT and its CONTROL observation")
print("  goal      : the captured output")
print("  scope     : the build and host configuration on which the bypass applies")
print("  transfer  : whether the deployed configuration matches")
PY
```

**Ledger, bypassed-with-artefact, goal, scope, transfer.** The transfer line decides whether the reader
must act, and the artefact-per-claim rule is what makes the ledger reviewable.

---

## 13. EVIDENCE STANDARD — MITIGATION BYPASS ARTEFACTS

| Item | Why |
|---|---|
| The **ledger read from `readelf`/`nm`/`checksec`**, including kernel-level rows | `checksec` alone misses ASLR, CET, and MTE |
| The **unprotected control build** of the same source, and both runs | isolates the mitigation from the technique |
| For ASLR/PIE: the **leaked address** and the **page-aligned resolved base** | the artefact for the claim |
| The base **differing across restarts**, with `setarch -R` as the control | otherwise ASLR may be off |
| For the canary: the **leaked value** and the **wrong-value abort** | the abort is the observation |
| For RELRO: the **alternative target with its read-back**, and the **full-RELRO fault** | the fault is the mitigation working |
| For NX: the **existing-code payload** and the **stack-shellcode fault** | the fault is the observation |
| For FORTIFY: the **fortified and unfortified builds' difference** | FORTIFY is compile-time and scoped |
| For CET: the **GNU_PROPERTY**, the **CPU support**, and the **kernel enablement** | ACTIVE requires all three |
| For MTE: the **wrong-tag fault** | the fault proves the check is active |
| The **goal's captured output** and the finding's **scope and transfer** | a bypass is intermediate |

Report the **ledger and the artefacts**: "`readelf -h` shows Type `DYN` with an INTERP segment, so PIE is
on; `readelf -l` shows both `GNU_STACK RW` and `GNU_RELRO`, and `readelf -d` shows no `BIND_NOW`, so RELRO
is partial and the GOT is writable only before the first resolution; `nm -D` shows `__stack_chk_fail`
present, so the canary is on; `cat /proc/sys/kernel/randomize_va_space` is `2`; `readelf -n` shows no CET
GNU_PROPERTY and `grep -o ibt /proc/cpuinfo` returns nothing, so CET is not active. A control build of the
same source with `-fno-stack-protector -no-pie -Wl,-z,norelro` was compiled so that each technique could
be compared. The PIE bypass's artefact is a leaked code address of `0x55f1a3c04a10` which resolved
`elf.address` to `0x55f1a3c04000`, asserted page-aligned, and the base differed on each of five restarts,
while under `setarch -R` it was constant, which is the control. The canary bypass's artefact is the leaked
value `0x3f8a1c9d2b00`, and an overflow writing a wrong canary aborted at `__stack_chk_fail`, which is the
control that the canary is on. The RELRO bypass did not use the GOT: a write to `__free_hook` was read back
as the value written, and the same GOT write on the full-RELRO control build faulted. The goal is the
captured output of `id` returned as `uid=1000 gid=1000`. Scope: the finding applies to the partial-RELRO
non-CET build as deployed, and would not transfer to a full-RELRO CET build", never "the binary's
protections were bypassed".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| "**Bypassed ASLR**" with no leaked address and no resolved base | unsupported; the leak is the artefact |
| A base that does **not differ across restarts** | ASLR may simply be off |
| "**Bypassed the canary**" with no leaked value | there is no canary leak |
| A **fork-server brute force** from one success | the rate and the inherited-canary check are the evidence |
| A **RELRO bypass** where the full-RELRO control did not fault | the control was not run |
| A **GOT write** on a slot that was already resolved | partial RELRO only leaves it writable before resolution |
| "**Bypassed NX**" while the stack was **RWE** | there was no NX to bypass |
| "**Bypassed FORTIFY**" without an unfortified control | the compile-time scope is the finding |
| A **CET bypass** on a host where CET was never active | nothing was bypassed |
| A **technique working on both** the protected and unprotected control build | it does not depend on the mitigation |
| "**Bypassed protections**" with no stated **goal** | a bypass is intermediate, not a compromise |

**An artefact per claim, a control observation per mitigation, and a stated scope.** An unartefacted ASLR
claim and a bypass that also works on the unprotected build are this family's two standard non-findings.

---

## 14. REMEDIATION REFERENCE — PROTECTION BYPASS ASSESSMENT

1. **Build the ledger from `readelf`, `nm`, `checksec`, and the kernel's own files rather than from memory, and include the kernel-level rows** - `checksec` alone misses ASLR, CET, and MTE.
2. **Compile and run a deliberately unprotected control build of the same source** - a technique that works on both builds proves nothing about the mitigation, and the difference between them is the finding.
3. **Attach an artefact to every claimed bypass: the leaked address and page-aligned base for ASLR and PIE, the leaked value for the canary, the alternative target and its read-back for RELRO, the fault for NX** - an unartefacted claim is the family's most common overstatement.
4. **Record each mitigation's own control observation, because the control is the observation that the mitigation is active** - the canary's abort at `__stack_chk_fail`, the fault on a full-RELRO GOT write, the fault on stack shellcode.
5. **For CET, check the binary's `GNU_PROPERTY`, the CPU's support, and the kernel's enablement, and require all three before claiming it is active** - CET is not active on a host that supports it but does not enable it.
6. **For MTE, use the wrong-tag fault as the control** - the fault proves the tag check is active, and a bypass on an untagged path proves nothing about MTE.
7. **State the build and host configuration the bypass applies to, and whether the deployed configuration matches** - the transfer question decides whether the reader must act.
8. **Treat FORTIFY as compile-time, and report the unchecked call site rather than a "FORTIFY bypass"** - the scope is the call site's presence or absence.
9. **For a fork-server brute force, report the guesses-per-success and verify with `strace -f` that the canary is inherited** - one success is not a rate, and the inheritance is what makes the technique viable.
10. **Confirm that a partial-RELRO GOT slot is still unresolved at the time of the write** - after the first call the slot holds a resolved address and the technique's premise is gone.
11. **State the goal reached, because a bypass with no goal is an intermediate result rather than a compromise** - the distinction decides the severity.

---

## 15. RELATED SIBLINGS - LOAD TOGETHER

- [stack-overflow-and-rop](../stack-overflow-and-rop/SKILL.md) - the primitive most of these bypasses serve
- [heap-exploitation](../heap-exploitation/SKILL.md) - glibc's own mitigations, a parallel ledger
- [arbitrary-write-to-rce](../arbitrary-write-to-rce/SKILL.md) - the targets available after RELRO is bypassed
- [browser-exploitation-v8](../browser-exploitation-v8/SKILL.md) - the same ledger logic at the browser's layer
- [kernel-exploitation](../kernel-exploitation/SKILL.md) - the kernel-level counterpart of this ledger
