---
name: code-obfuscation-deobfuscation
description: >-
  Code obfuscation analysis and deobfuscation playbook. Use when reversing
  binaries protected by junk code, opaque predicates, self-modifying code,
  control flow flattening, VM protection, or string encryption.
---

# SKILL: Code Obfuscation & Deobfuscation — Expert Analysis Playbook

> **AI LOAD INSTRUCTION**: Expert techniques for identifying, classifying, and defeating code obfuscation in native binaries. Covers junk code, opaque predicates, SMC, control flow flattening, movfuscator, VM protectors (VMProtect/Themida/Code Virtualizer), string encryption, import hiding, and anti-disassembly tricks. Base models often conflate packing with obfuscation and miss the distinction between static and dynamic deobfuscation strategies.

## 0. RELATED ROUTING

- [anti-debugging-techniques](../anti-debugging-techniques/SKILL.md) when the obfuscated binary also has anti-debug layers
- [symbolic-execution-tools](../symbolic-execution-tools/SKILL.md) when using angr/Z3 for automated deobfuscation
- [vm-and-bytecode-reverse](../vm-and-bytecode-reverse/SKILL.md) for deep VM protector bytecode analysis

### Quick identification picks

| Symptom in IDA/Ghidra | Likely Obfuscation | Start With |
|---|---|---|
| Flat CFG, single giant switch | Control flow flattening | Symbolic execution to recover CFG |
| Only `mov` instructions | movfuscator | demovfuscation / trace-based lifting |
| pushad/pushfd → VM entry | VM protector | Handler table extraction |
| XOR loop before code execution | SMC / string encryption | Dynamic analysis, breakpoint after decode |
| Impossible conditions (opaque predicates) | Junk code insertion | Pattern-based removal |
| All strings unreadable | String encryption | Hook decryption routine, or emulate |
| No imports in IAT | Import hiding | Trace GetProcAddress / hash resolution |

---

## 1. JUNK CODE & OPAQUE PREDICATES

### 1.1 Junk Code Insertion

Dead code that never affects program output, added to increase analysis time.

**Identification**:
- Instructions that write to registers/memory never read afterward
- Function calls whose return values are discarded and have no side effects
- Loops with invariant bounds that compute unused results

**Removal strategy**:
1. Compute def-use chains (IDA/Ghidra data flow analysis)
2. Mark instructions with no downstream use as dead
3. Verify removal doesn't change program behavior (trace comparison)

### 1.2 Opaque Predicates

Conditional branches where the condition is always true or always false, but this is non-obvious.

| Type | Example | Always Evaluates To |
|---|---|---|
| Arithmetic | `x² ≥ 0` | True |
| Number theory | `x*(x+1) % 2 == 0` | True (product of consecutive ints) |
| Pointer-based | `ptr == ptr` after aliasing | True |
| Hash-based | `CRC32(constant) == known_value` | True |

**Deobfuscation**:
- Abstract interpretation: prove the condition is constant
- Symbolic execution: Z3 proves `∀x: predicate(x) = True`
- Pattern matching: recognize known opaque predicate families
- Dynamic: trace and observe the branch is never taken / always taken

```python
import z3
x = z3.BitVec('x', 32)
s = z3.Solver()
s.add(x * (x + 1) % 2 != 0)
print(s.check())  # unsat → always true
```

---

## 2. SELF-MODIFYING CODE (SMC)

Runtime code patching: encrypted code is decrypted just before execution.

### 2.1 XOR Decryption Loop (Most Common)

```asm
lea esi, [encrypted_code]
mov ecx, code_length
mov al, xor_key
decrypt_loop:
    xor byte [esi], al
    inc esi
    loop decrypt_loop
    jmp encrypted_code  ; now decrypted
```

### 2.2 Analysis Strategy

```
1. Identify the decryption routine (look for XOR/ADD/SUB in loops writing to .text)
2. Set breakpoint AFTER the loop completes
3. At breakpoint: dump the decrypted memory region
4. Re-analyze the dumped code in IDA/Ghidra
5. For multi-layer: repeat for each decryption stage
```

### 2.3 Automated Unpacking via Emulation

```python
from unicorn import *
from unicorn.x86_const import *

mu = Uc(UC_ARCH_X86, UC_MODE_32)
mu.mem_map(0x400000, 0x10000)
mu.mem_write(0x400000, binary_code)
mu.emu_start(decrypt_entry, decrypt_end)
decrypted = mu.mem_read(code_start, code_length)
```

---

## 3. CONTROL FLOW FLATTENING (CFF)

### 3.1 Structure

Original sequential blocks are transformed into a dispatcher loop:

```
Original:      A → B → C → D

Flattened:     ┌──────────────────┐
               │   dispatcher     │
               │   switch(state)  │◄─────┐
               ├──────────────────┤      │
               │ case 1: block A  │──────┤
               │ case 2: block B  │──────┤
               │ case 3: block C  │──────┤
               │ case 4: block D  │──────┘
               └──────────────────┘
```

Each block sets `state = next_state` before jumping back to the dispatcher.

### 3.2 Recovery Techniques

| Technique | Tool | Effectiveness |
|---|---|---|
| Symbolic execution | angr, Triton, miasm | High — traces all state transitions |
| Trace-based recovery | Pin/DynamoRIO trace → reconstruct CFG | Medium — covers executed paths only |
| Pattern matching | Custom IDA/Ghidra script | Medium — works for known flatteners |
| D-810 (IDA plugin) | IDA Pro | High — specifically designed for CFF |

### 3.3 Symbolic Deflattening (angr approach)

```python
import angr, claripy

proj = angr.Project('./obfuscated')
cfg = proj.analyses.CFGFast()

# Find dispatcher block (highest in-degree basic block)
dispatcher = max(cfg.graph.nodes(), key=lambda n: cfg.graph.in_degree(n))

# For each case block, symbolically determine successor
for block in case_blocks:
    state = proj.factory.blank_state(addr=block.addr)
    # ... solve state variable to find real successor
```

---

## 4. MOVFUSCATOR

### 4.1 Concept

All computation reduced to `mov` instructions only (Turing-complete via memory-mapped computation tables). Created by Christopher Domas.

### 4.2 Identification

- Function contains only `mov` instructions (no add, sub, xor, jmp, call)
- Large lookup tables in data section
- Memory-mapped flag registers

### 4.3 Demovfuscation

| Approach | Description |
|---|---|
| demovfuscator (tool) | Static analysis, recovers original operations from mov patterns |
| Trace + taint analysis | Run with Pin/DynamoRIO, taint inputs, observe computation |
| Symbolic execution | Treat entire function as constraint system |

---

## 5. VM PROTECTION (VMProtect / Themida / Code Virtualizer)

### 5.1 VM Architecture

```
Protected code → bytecode compiler → custom bytecode
Runtime: VM entry (pushad/pushfd) → fetch → decode → execute → VM exit (popad/popfd)
```

### 5.2 VM Entry Point Identification

```asm
; Typical VMProtect entry
pushad                    ; save all registers
pushfd                    ; save flags
mov ebp, esp              ; VM stack frame
sub esp, VM_LOCALS_SIZE   ; allocate VM context
mov esi, bytecode_addr    ; bytecode instruction pointer
jmp vm_dispatcher         ; enter VM loop
```

### 5.3 Handler Table Extraction

```
1. Find dispatcher (large switch or indirect jump via table)
2. Each case/entry = one VM handler (implements one VM opcode)
3. Map handler addresses to operations by analyzing each handler:
   - Handler reads operand from bytecode stream (esi)
   - Performs operation on VM registers/stack
   - Advances bytecode pointer
   - Returns to dispatcher
```

### 5.4 Devirtualization Approaches

| Method | Description | Tool |
|---|---|---|
| Manual handler mapping | Reverse each handler, build ISA spec | IDA + scripting |
| Trace recording | Record all handler executions, reconstruct program | REVEN, Pin |
| Symbolic lifting | Symbolically execute handlers, lift to IR | Triton, miasm |
| Pattern matching | Match handler patterns to known VM families | Custom scripts |

### 5.5 VMProtect Specifics

- Uses opaque predicates in dispatcher
- Handler mutation: same opcode, different handler code per build
- Multiple VM layers (VM inside VM)
- Integrates anti-debug and integrity checks

---

## 6. STRING ENCRYPTION

### 6.1 Common Patterns

| Pattern | Example | Recovery |
|---|---|---|
| XOR loop | `for (i=0; i<len; i++) s[i] ^= key;` | Hook or emulate XOR function |
| Stack strings | `mov [esp+0], 'H'; mov [esp+1], 'e'; ...` | IDA FLIRT / Ghidra script to reassemble |
| RC4 encrypted | Encrypted blob + RC4 key in binary | Extract key, decrypt offline |
| AES encrypted | Encrypted blob + AES key derived at runtime | Hook after decryption |
| Custom encoding | Base64 + XOR + reverse | Trace the decode function, replicate |

### 6.2 Automated String Decryption

```python
# Ghidra script: find XOR decryption calls, emulate them
from ghidra.program.model.symbol import SourceType

decrypt_func = getFunction("decrypt_string")
refs = getReferencesTo(decrypt_func.getEntryPoint())

for ref in refs:
    call_addr = ref.getFromAddress()
    # extract arguments (encrypted buffer ptr, key, length)
    # emulate decryption, add comment with plaintext
```

---

## 7. IMPORT HIDING

### 7.1 GetProcAddress + Hash Lookup

```c
FARPROC resolve(DWORD hash) {
    // Walk PEB → LDR → InMemoryOrderModuleList
    // For each DLL, walk export table
    // Hash each export name, compare with target hash
    // Return matching function pointer
}
```

### 7.2 Recovery

1. Identify the hash algorithm (common: CRC32, djb2, ROR13+ADD)
2. Compute hashes for all known API names
3. Build hash → API name lookup table
4. Annotate resolved calls in IDA/Ghidra

### 7.3 Common Hash Algorithms

| Name | Algorithm | Used By |
|---|---|---|
| ROR13 | `hash = (hash >> 13 \| hash << 19) + char` | Metasploit shellcode |
| djb2 | `hash = hash * 33 + char` | Various malware |
| CRC32 | Standard CRC32 of function name | Sophisticated packers |
| FNV-1a | `hash = (hash ^ char) * 0x01000193` | Modern malware |

---

## 8. ANTI-DISASSEMBLY TRICKS

### 8.1 Techniques

| Trick | Mechanism | Fix |
|---|---|---|
| Overlapping instructions | `jmp $+2; db 0xE8` (fake call prefix) | Manual re-analysis from correct offset |
| Misaligned jumps | Jump into middle of multi-byte instruction | Force IDA to re-analyze at target |
| Conditional jump pair | `jz $+5; jnz $+3` (always jumps, confuses linear disasm) | Convert to unconditional jmp |
| Return address manipulation | `push addr; ret` instead of `jmp addr` | Recognize push+ret as jump |
| Exception-based flow | Trigger exception, real code in handler | Analyze exception handler chain |
| Call + add [esp] | `call $+5; add [esp], N; ret` (computed jump) | Calculate actual target |

### 8.2 IDA Fixes

```
Right-click → Undefine (U)
Right-click → Code (C) at correct offset
Edit → Patch → Assemble (for permanent fix)
```

---

## 9. DECISION TREE

```
Obfuscated binary — how to approach?
│
├─ Can you run it?
│  ├─ Yes → Dynamic analysis first
│  │  ├─ Set BP on interesting APIs (file, network, crypto)
│  │  ├─ Trace execution to understand real behavior
│  │  └─ Dump decrypted code/strings at runtime
│  │
│  └─ No (embedded/firmware/exotic arch) → Static only
│     └─ Identify obfuscation type from patterns below
│
├─ What does the code look like?
│  │
│  ├─ Giant flat switch/dispatcher loop?
│  │  ├─ State variable drives control flow → CFF
│  │  │  └─ Use D-810 or symbolic deflattening
│  │  └─ Bytecode fetch-decode-execute → VM protection
│  │     └─ Extract handlers, build disassembler
│  │
│  ├─ Only mov instructions?
│  │  └─ movfuscator → demovfuscator tool
│  │
│  ├─ XOR/ADD loop writing to .text section?
│  │  └─ SMC → breakpoint after decode, dump
│  │
│  ├─ Impossible conditions in branches?
│  │  └─ Opaque predicates → Z3 proving or pattern removal
│  │
│  ├─ Disassembly looks wrong / functions overlap?
│  │  └─ Anti-disassembly → manual re-analysis at correct offsets
│  │
│  ├─ No readable strings?
│  │  └─ String encryption → hook decrypt function or emulate
│  │
│  ├─ No imports in IAT?
│  │  └─ Import hiding → identify hash, build lookup table
│  │
│  └─ pushad/pushfd → complex code → popad/popfd?
│     └─ VM protector entry/exit → full VM analysis
│
└─ What tool to use?
   ├─ Known protector (VMProtect/Themida) → specific deprotection guide
   ├─ Custom obfuscation → combine: IDA scripting + Triton + manual
   ├─ CTF challenge → angr symbolic execution often fastest
   └─ Malware analysis → dynamic (debugger + API monitor) first
```

---

## 10. TOOLBOX

| Tool | Purpose | Best For |
|---|---|---|
| IDA Pro + Hex-Rays | Disassembly, decompilation, scripting | All-around analysis |
| Ghidra | Free alternative with scripting (Java/Python) | Budget-friendly RE |
| D-810 (IDA plugin) | Automated CFF deflattening | OLLVM-style obfuscation |
| miasm | IR-based analysis framework | Symbolic deobfuscation |
| Triton | Dynamic symbolic execution | Opaque predicate solving, CFF |
| REVEN | Full-system trace recording and replay | VM protector analysis |
| demovfuscator | movfuscator reversal | mov-only binaries |
| x64dbg + plugins | Dynamic analysis with scripting | Windows RE |
| Unicorn Engine | CPU emulation | SMC unpacking, shellcode |
| Capstone | Disassembly library | Custom tooling |
| IDA FLIRT | Function signature matching | Identify library code in stripped binaries |
| Binary Ninja | Alternative disassembler with MLIL/HLIL | Automated analysis |

---

## 11. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Which **specific transformation** is present, at which **address or region**? | "obfuscated" is not a finding |
| 2 | What is the **input and output** of the transformation loop? | the semantics that must be recovered |
| 3 | Does the **deobfuscated result produce the original behaviour**? | equivalence, which is the only proof |
| 4 | Was there a **reference build** - an unobfuscated or differently-obfuscated copy? | causality |
| 5 | Is the recovery **reproducible** from the original bytes by a scripted pass? | not a manual one-off |
| 6 | Which **analysis goal** does the recovery enable? | the technique alone is not a result |
| 7 | Does the transformation **change across runs or inputs**? | static vs dynamic, which changes the method |

**The recovered semantics plus a behavioural equivalence proof is the bar.** Naming a protector is a
classification, not a result.

---

## 12. THE TRANSFORMATION TAXONOMY — WHAT EACH COSTS THE ANALYST

| Transformation | What it hides | Analytically cheapest route | Cost it actually imposes |
|---|---|---|---|
| Junk code / opaque predicates | the real control flow, among always-true branches | symbolic or constant propagation over one predicate | low: a solver removes it in minutes |
| Instruction substitution | the instruction mix's recognisability | lifting to an IR, then peephole re-simplification | low to moderate |
| Self-modifying code | the static bytes actually executed | a dump after the write, or a page-level trace | moderate: forces a dynamic pass |
| String encryption | the operator's URLs, paths, and messages | emulating the decrypt stub once, then logging every call | moderate: one stub unlocks all strings |
| Import hiding | which APIs the code reaches | resolving the hash/iAT at runtime, or a call trace | moderate: dynamic resolution recovers it |
| Control flow flattening | the CFG's shape | recovering the block-to-state map from the dispatcher | high: the block count drives the work |
| VM protection | the instruction set itself | devirtualising: identifying the handler table and its semantics | the highest: it is a compiler in reverse |
| Anti-disassembly tricks | the linear disassembly's alignment | a recursive-descent disassembler, or forcing alignment | low against a modern disassembler |
| Polymorphism (per-build) | the reuse of a signature | normalising the per-build constant | low: it costs the defender more than the analyst |
| Metamorphism (per-instruction) | any stable byte pattern | behaviour-based comparison rather than pattern matching | moderate: defeats hashing, not analysis |

**State the transformation and its cost, not the protector's brand.** The taxonomy above is what makes an
analysis-resistance assessment comparable between samples, and the cheapest route column is what a reader
needs in order to budget.

---

## 13. EXECUTION PRIMITIVES

An obfuscation finding is proven by **a named transformation at a named region, a scripted recovery from
the original bytes, and a behavioural equivalence between the recovered form and the original**. Naming a
protector is not a result.

### 11b.1 Opcode-level pattern work, which is deterministic

```python
# the deterministic pre-pass: opcode statistics SEPARATE an obfuscated build from a normal one
from collections import Counter
import re, subprocess, json

def objdump_text(path, start=0, end=None):
    args = ["objdump","-d","--no-show-raw-insn","-M","intel",path]
    out = subprocess.run(args, capture_output=True, text=True).stdout
    # narrow to a virtual-address region when one is known
    if start or end:
        keep, rows = False, []
        for line in out.splitlines():
            m = re.match(r'\s*([0-9a-f]+):', line)
            if m:
                a = int(m.group(1), 16)
                keep = a >= start and (end is None or a < end)
            if keep: rows.append(line)
        return "\n".join(rows)
    return out

def opcode_profile(text):
    """The instruction mix. obfuscated code is dominated by mov/jmp/xor/not/push/pop."""
    ops = re.findall(r'^\s*[0-9a-f]+:\s+([a-z][a-z0-9.]*)', text, re.M)
    c = Counter(ops)
    total = sum(c.values()) or 1
    return {k: round(v/total, 4) for k, v in c.most_common(20)}, total

print("=== THE DETERMINISTIC SIGNALS, each mechanically checkable ===")
SIGNALS = {
 "junk/opaque predicates":  "mov reg,imm / test reg,reg / conditional branch where the flag is CONSTANT "
                            "-> verify with a symbolic check, not by eye",
 "instruction entropy":     "nop/push/pop/lea density far above a compiled baseline",
 "dead writes":             "a register written and never read before being overwritten",
 "flat control flow":       "a single dispatch loop with a state variable and an indirect jump per block",
 "string encryption":       "no plaintext strings in .rodata but a decrypt loop called before each use",
 "import hiding":           "an import table that is thin relative to the code's API usage",
 "self-modifying region":   "an mprotect/mmap with PROT_WRITE|PROT_EXEC on a code page",
}
for k, v in SIGNALS.items(): print("  %-26s %s" % (k, v))
print()
print("=== THE CONTROL: profile a KNOWN-UNOBFUSCATED binary with the same function ===")
print("  the same metrics on a normal build must look DIFFERENTLY. If they do not, your metric")
print("  is measuring the compiler rather than the obfuscator, and every claim from it is void.")
print()
print("=== RECORD, for every transformation you name ===")
for r in ["the address range or the symbol", "the transformation's input and output",
          "the script that performs the recovery", "the recovered artefact",
          "the behavioural equivalence test, and its result"]:
    print("  -", r)
```

**The known-clean control binary is what validates the metric.** If the same profile appears on an
unobfuscated build, the metric measures the compiler rather than the obfuscator.

### 11b.2 String recovery, which has an exact proof

```python
# string decryption: the proof is that the recovered strings MATCH behaviour, not that they look readable
import re, subprocess

def strings_of(path, minlen=4):
    out = subprocess.run(["strings","-a","-n",str(minlen),path], capture_output=True, text=True).stdout
    return set(out.splitlines())

def recover_by_emulation(blob, key, algo):
    """Replace with the real routine, run in the SAME environment as the target would use it."""
    raise NotImplementedError("emulate the decrypt stub, do not reimplement it from reading it")

print("=== THE PROOF, in the order that matters ===")
print("  1. the decrypt stub is EMULATED, not reimplemented by reading the disassembly")
print("     (a reimplementation proves your reading is self-consistent, not that it is correct)")
print("  2. the recovered string appears in the target's OWN runtime behaviour:")
print("     a URL it actually requests, a path it actually opens, an error it actually prints")
print("  3. the recovered string is NOT in `strings` of the packed original - so it was genuinely")
print("     encrypted rather than merely obfuscated by a benign refactor")
print()
print("=== THE CONTROL, which rules out the standard false positive ===")
print("  run the SAME recovery on a binary with no string encryption.")
print("  the recovered set must be EMPTY, or your routine is emitting readable text from noise.")
print("  THE STANDARD ERROR: a 'decrypted' string that is plausible English but not present in any")
print("  runtime behaviour is a coincidence of the key space, not a recovery.")
print()
print("=== verify against a runtime observation ===")
print("  strace -f -e trace=openat,connect ./target 2>&1 | grep -v ENOENT")
print("  -> the recovered path or hostname must appear HERE. That is the equivalence.")
```

**A recovered string must appear in the target's runtime behaviour.** A plausible English string that the
binary never uses is a coincidence of the key space, and the no-encryption control is what exposes it.

### 11b.3 Control-flow flattening, and the equivalence test

```python
# CFF recovery: the proof is that the recovered CFG EXECUTES identically, block for block
print("=== THE METHOD, mechanically ===")
for step in [
  "1. identify the dispatcher: the block with an indirect jump whose target is computed from state",
  "2. identify the state variable: the register or stack slot the dispatcher reads",
  "3. enumerate the blocks and, for each, the state value it sets before re-entering the dispatcher",
  "4. rebuild the edge list from those (block -> state) assignments; this IS the CFG",
  "5. EMIT the recovered CFG in a form that can be diffed and re-executed",
]:
    print("  ", step)
print()
print("=== THE EQUIVALENCE PROOF, which has three independent arms ===")
arms = {
 "trace equality":   "run the original and the recovered form on the same inputs; the executed "
                     "block-sequence must match. Record the trace, not an impression.",
 "output equality":  "stdout, stderr, exit code, and every file written must match, byte for byte.",
 "differential arm": "run BOTH forms on 100+ generated inputs and diff. One input proves nothing: "
                     "flattened code often has one path that is only taken on a rare input.",
}
for k, v in arms.items(): print("  %-18s %s" % (k, v))
print()
print("=== THE CONTROL ===")
print("  take a DIFFERENT function with no flattening and run the same recovery pipeline.")
print("  it must report 'no dispatcher found'. A pipeline that 'recovers' a CFG from an ordinary")
print("  function is inventing edges, and every CFF claim it makes is suspect.")
print()
print("=== what must NOT be claimed ===")
for b in ["that the recovery is COMPLETE, if any state value could not be resolved",
          "that the recovered form is the original SOURCE (it is a semantically equivalent form)",
          "that a single successful input demonstrates equivalence"]:
    print("  -", b)
```

**Three arms of equivalence, plus a known-unflattened control.** A recovery pipeline that finds a
dispatcher in an ordinary function is inventing edges.

### 11b.4 The end-to-end harness

```bash
python3 - <<'PY'
import re, subprocess, hashlib, json
print("=== OBFUSCATION RECOVERY ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the RAW binary's SHA-256 is recorded before anything else",
  "an analysis whose input is unrecorded is unreproducible"),
 ("a KNOWN-CLEAN control binary was profiled with the same metric",
  "if the metric matches the clean build, it measures the compiler, not the obfuscator"),
 ("the transformation is NAMED and has an ADDRESS RANGE",
  "'obfuscated' and a protector's name are classifications, not findings"),
 ("recovery was done by EMULATION or a SCRIPTED pass over the original bytes",
  "a hand-recovery is a one-off and cannot be re-run on the next sample"),
 ("the recovered artefact is EMITTED to a file and diffable",
  "an artefact that lives only in a session is not evidence"),
 ("behavioural EQUIVALENCE was tested on 100+ inputs, not one",
  "flattened code has rare paths that a single input cannot reach"),
 ("a NO-ENCRYPTION / NO-FLATTENING control was run through the SAME pipeline",
  "it must report nothing; otherwise the pipeline invents results"),
 ("recovered strings were confirmed against RUNTIME behaviour",
  "a plausible-but-unused string is a key-space coincidence"),
 ("the analysis GOAL was reached through the recovery",
  "recovering a string is not the same as answering the question"),
 ("what remains UNRECOVERED is stated explicitly",
  "an honest partial result is usable; an overclaimed complete one is not"),
]
for n, how in CHECKS.items() if hasattr(CHECKS,'items') else enumerate(CHECKS):
    print("  [ ] %-58s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  artifact  : the SHA-256 of the analysed bytes")
print("  transform : the name, the address range, and the input/output of the loop")
print("  method    : the script or emulator used, not prose")
print("  proof     : the equivalence arms and their results, plus the clean-build control")
print("  residual  : what could not be recovered, stated plainly")
PY
```

**Artifact hash, named transformation, scripted method, equivalence arms, clean control, residual.** The
residual list is what separates a usable analysis from an overclaim.

---

## 14. EVIDENCE STANDARD — RECOVERY ARTEFACTS

| Item | Why |
|---|---|
| The **SHA-256 of the analysed bytes** | the input identity; without it nothing is reproducible |
| The **transformation name** and the **address range** | the finding is a region, not a label |
| The **input and output** of the transformation loop | the semantics that were recovered |
| The **recovery script or emulator**, quoted | a hand-recovery cannot be re-run on the next sample |
| The **recovered artefact**, emitted to a file | diffable evidence rather than a session claim |
| The **equivalence arms**: trace, output, and the 100+ input differential | one input proves nothing |
| The **known-clean control binary's** profile and pipeline result | rules out a metric or pipeline that invents results |
| Runtime **confirmation** of each recovered string | a plausible string may be a key-space coincidence |
| The **analysis goal reached** | the technique alone is an intermediate result |
| The **residual**: what could not be recovered | the honest scope of the result |

Report the **transformation and its equivalence**: "the sample's SHA-256 is `9c41…`, and the region
`0x401200`–`0x403f00` is dominated by `mov`/`xor`/`not` at `0.71` of its instructions against `0.18` in a
known-clean build of the same program, which is the signal that separates the flattened region from the
compiler's own output. The dispatcher at `0x402a10` reads a state variable at `[rbp-0x8]` and jumps
indirectly through a table at `0x404000`, and the block-to-state assignments recovered from the 34 blocks
produce an edge list that executes the same block sequence as the original on `100 of 100` generated
inputs, with byte-identical stdout and exit codes, which is the equivalence. The recovery pipeline was run
on a second, unflattened function in the same binary and reported `no dispatcher found`, which is the
control. Eleven of the 34 blocks have a state value that could not be resolved statically, so the
recovered CFG is incomplete for those paths and the residual is stated in the report. The string-decrypt
stub at `0x401980` was emulated rather than reimplemented, and the recovered hostname
`updates.example-cdn.net` appears in the target's own `connect` call under `strace`, which is the runtime
confirmation", never "the binary is protected with control flow flattening".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A protector's **name** with no named transformation or region | a classification, not a result |
| A metric that matches a **known-clean** build | it measures the compiler |
| A "decrypted" string that is **plausible English** but appears in no runtime behaviour | a key-space coincidence |
| A recovery pipeline that "**recovers**" a CFG from an ordinary function | it invents edges |
| Equivalence claimed from **one input** | flattened code has rare paths |
| A **hand-recovery** with no script | not reproducible on the next sample |
| A **partially** recovered CFG reported as complete | an overclaim; the residual must be stated |
| A **large** binary reported as obfuscated without a metric | size is not obfuscation |
| The recovered form presented as the **original source** | it is a semantically equivalent form |
| A transformation that **disappears** under a different compiler flag | a build artifact, not a protection |

**A named region, a scripted recovery, an equivalence proof, and a clean-build control.** A protector's
name and a plausible-but-unused recovered string are this family's two standard non-findings.

---

## 15. REMEDIATION REFERENCE — ANALYSIS-RESISTANCE ASSESSMENT

1. **Record the SHA-256 of every analysed artefact before touching it, and analyse copies rather than originals** - an unrecorded input makes the whole result unreproducible.
2. **Profile a known-clean build with the same metric before drawing any conclusion from it** - a metric that matches the clean build measures the compiler rather than the obfuscator.
3. **Emulate the decrypt or dispatch routine rather than reimplementing it from a reading of the disassembly** - a reimplementation proves self-consistency, not correctness.
4. **Test equivalence on 100+ generated inputs across trace, output, and files written, because flattened code has rare paths** - a single input cannot reach them.
5. **Run the recovery pipeline on a known-undisturbed function as a control, and require it to report nothing** - a pipeline that always finds a structure is inventing one.
6. **Confirm every recovered string against the target's own runtime behaviour (`strace`, a listener, an output file)** - a plausible string that the binary never uses is a key-space coincidence.
7. **Emit recovered artefacts to files so they can be diffed and re-run** - an artefact that exists only inside a session is not evidence.
8. **State the residual: which blocks, states, or paths could not be resolved** - an honest partial result is usable, and an overclaimed complete one is not.
9. **Write the recovery as a script that runs on the next sample in the family** - the scheme's reproducibility is what gives the work value beyond one binary.
10. **Keep the recovered form labelled as a semantically equivalent reconstruction, never as the original source** - the distinction matters to anyone who reuses it.
11. **Report the analysis goal reached and the cost it took, rather than the protector's name** - the reader needs to know what the protection actually bought.

---

## 16. RELATED SIBLINGS - LOAD TOGETHER

- [anti-debugging-techniques](../anti-debugging-techniques/SKILL.md) - the checks that accompany these transformations
- [vm-and-bytecode-reverse](../vm-and-bytecode-reverse/SKILL.md) - the protector family that bundles both
- [binary-protection-bypass](../binary-protection-bypass/SKILL.md) - the wider hardening-bypass methodology
- [symbolic-execution-tools](../symbolic-execution-tools/SKILL.md) - when a predicate must be solved rather than removed
- [reverse-shell-techniques](../reverse-shell-techniques/SKILL.md) - the analysis-goal context for a protected sample
