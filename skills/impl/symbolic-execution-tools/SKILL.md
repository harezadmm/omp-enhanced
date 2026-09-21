---
name: symbolic-execution-tools
description: >-
  Symbolic execution and constraint solving playbook. Use when solving CTF
  reversing challenges, recovering keys, bypassing checks, or automating
  binary analysis with angr, Z3, or Unicorn Engine.
---

# SKILL: Symbolic Execution Tools — Expert Analysis Playbook

> **AI LOAD INSTRUCTION**: Expert symbolic execution techniques using angr, Z3, and Unicorn Engine. Covers CTF challenge automation, constraint solving patterns, function hooking, SimProcedure replacement, and emulation-based unpacking. Base models often produce broken angr scripts due to incorrect state initialization or missing hooks for libc functions.

## 0. RELATED ROUTING

- [anti-debugging-techniques](../anti-debugging-techniques/SKILL.md) when anti-debug checks need to be symbolically bypassed
- [code-obfuscation-deobfuscation](../code-obfuscation-deobfuscation/SKILL.md) when using symbolic execution for deobfuscation
- [vm-and-bytecode-reverse](../vm-and-bytecode-reverse/SKILL.md) when applying angr to custom VM challenges

### Advanced Reference

Also load [ANGR_COOKBOOK.md](./ANGR_COOKBOOK.md) when you need:
- 15+ ready-to-use angr script patterns for common CTF challenges
- Hook templates for scanf, printf, malloc, strcmp
- Symbolic file input, stdin, argv patterns
- Optimization tricks for path explosion management

### When to use which tool

| Scenario | Best Tool | Why |
|---|---|---|
| Pure math / equation system | Z3 | Direct constraint solving, no binary needed |
| Binary with control flow | angr | Explores paths, manages constraints automatically |
| Emulate specific code region | Unicorn | Fast, no symbolic overhead, good for unpacking |
| Complex binary + custom VM | angr + Unicorn (combo) | angr for control flow, Unicorn for VM handlers |
| Kernel / firmware code | Qiling | Full system emulation with OS awareness |

---

## 1. ANGR — CORE CONCEPTS

### 1.1 Pipeline

```
Project(binary)
  → Factory.entry_state() / blank_state(addr=)
    → SimulationManager(state)
      → explore(find=target, avoid=bad)
        → found[0].solver.eval(symbolic_var)
```

### 1.2 Essential Setup

```python
import angr
import claripy

proj = angr.Project('./challenge', auto_load_libs=False)

# Entry state: start from program entry point
state = proj.factory.entry_state()

# Blank state: start from arbitrary address
state = proj.factory.blank_state(addr=0x401000)

# Full init state: with command-line args
state = proj.factory.full_init_state(args=['./challenge', arg1_sym])

simgr = proj.factory.simulation_manager(state)
simgr.explore(find=0x401234, avoid=[0x401300])

if simgr.found:
    found = simgr.found[0]
    solution = found.solver.eval(symbolic_input, cast_to=bytes)
    print(f"Solution: {solution}")
```

### 1.3 Symbolic Variables (claripy)

```python
# Bitvector (fixed-size integer)
sym_input = claripy.BVS("input", 64)        # 64-bit symbolic
sym_byte = claripy.BVS("byte", 8)           # 8-bit symbolic
sym_buf = claripy.BVS("buffer", 8 * 32)     # 32-byte buffer

# Concrete bitvector
concrete = claripy.BVV(0x41, 8)             # concrete value 0x41

# Constraints
state.solver.add(sym_input > 0)
state.solver.add(sym_input < 100)
state.solver.add(sym_byte >= 0x20)           # printable ASCII
state.solver.add(sym_byte <= 0x7e)

# Evaluate
value = state.solver.eval(sym_input)
all_values = state.solver.eval_upto(sym_input, 10)  # up to 10 solutions
```

### 1.4 Symbolic stdin

```python
flag_len = 32
sym_stdin = claripy.BVS("stdin", 8 * flag_len)

state = proj.factory.entry_state(stdin=sym_stdin)

# Constrain to printable ASCII
for i in range(flag_len):
    byte = sym_stdin.get_byte(i)
    state.solver.add(byte >= 0x20)
    state.solver.add(byte <= 0x7e)
```

### 1.5 Hooking Functions

```python
# Hook by address (skip N bytes of original code)
@proj.hook(0x401100, length=5)
def skip_check(state):
    state.regs.eax = 1  # force success

# SimProcedure: replace library function
class MyStrcmp(angr.SimProcedure):
    def run(self, s1, s2):
        return claripy.If(
            self.state.memory.load(s1, 32) == self.state.memory.load(s2, 32),
            claripy.BVV(0, 32),
            claripy.BVV(1, 32)
        )

proj.hook_symbol('strcmp', MyStrcmp())

# Hook common problematic functions
proj.hook_symbol('printf', angr.SIM_PROCEDURES['libc']['printf']())
proj.hook_symbol('scanf', angr.SIM_PROCEDURES['libc']['scanf']())
proj.hook_symbol('puts', angr.SIM_PROCEDURES['libc']['puts']())
```

### 1.6 Memory Operations

```python
# Read memory (symbolic-aware)
data = state.memory.load(addr, size)          # returns BV
data_concrete = state.solver.eval(data, cast_to=bytes)

# Write memory
state.memory.store(addr, claripy.BVV(0x41, 8))
state.memory.store(addr, sym_buf)

# Read/write registers
rax = state.regs.rax
state.regs.rdi = claripy.BVV(0x1000, 64)
```

---

## 2. Z3 CONSTRAINT SOLVING

### 2.1 Core API

```python
from z3 import *

# Sorts
x = BitVec('x', 32)    # 32-bit bitvector
y = Int('y')             # arbitrary precision integer
b = Bool('b')            # boolean

# Solver
s = Solver()
s.add(x + y == 42)
s.add(x > 0)
s.add(y > 0)

if s.check() == sat:
    m = s.model()
    print(f"x = {m[x]}, y = {m[y]}")
```

### 2.2 Common CTF Patterns

```python
# Serial key validation: each char satisfies constraints
key = [BitVec(f'k{i}', 8) for i in range(16)]
s = Solver()
for k in key:
    s.add(k >= 0x30, k <= 0x7a)  # alphanumeric-ish

# XOR key recovery
plaintext = b"known_plaintext"
ciphertext = b"\x12\x34..."
key_byte = BitVec('key', 8)
s = Solver()
for p, c in zip(plaintext, ciphertext):
    s.add(p ^ key_byte == c)

# System of linear equations (modular)
a, b, c = BitVecs('a b c', 32)
s = Solver()
s.add(3*a + 5*b + 7*c == 0x12345678)
s.add(2*a + 4*b + 6*c == 0xDEADBEEF)
s.add(a ^ b ^ c == 0xCAFEBABE)
```

### 2.3 Optimization

```python
from z3 import Optimize

opt = Optimize()
x = BitVec('x', 32)
opt.add(x > 0)
opt.add(x < 1000)
opt.minimize(x)  # find smallest satisfying value
opt.check()
print(opt.model())
```

---

## 3. UNICORN ENGINE — CODE EMULATION

### 3.1 Basic Setup

```python
from unicorn import *
from unicorn.x86_const import *
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

mu = Uc(UC_ARCH_X86, UC_MODE_64)

CODE_ADDR = 0x400000
STACK_ADDR = 0x7fff0000
STACK_SIZE = 0x10000

mu.mem_map(CODE_ADDR, 0x10000)
mu.mem_map(STACK_ADDR, STACK_SIZE)

mu.mem_write(CODE_ADDR, code_bytes)
mu.reg_write(UC_X86_REG_RSP, STACK_ADDR + STACK_SIZE - 0x1000)
mu.reg_write(UC_X86_REG_RBP, STACK_ADDR + STACK_SIZE - 0x1000)

mu.emu_start(CODE_ADDR, CODE_ADDR + len(code_bytes))

result = mu.reg_read(UC_X86_REG_RAX)
```

### 3.2 Hooking Memory & Instructions

```python
# Hook memory access
def hook_mem(uc, access, address, size, value, user_data):
    if access == UC_MEM_WRITE:
        print(f"Write {value:#x} to {address:#x}")
    elif access == UC_MEM_READ:
        print(f"Read from {address:#x}")

mu.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, hook_mem)

# Hook specific instruction (for tracing)
def hook_code(uc, address, size, user_data):
    code = uc.mem_read(address, size)
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    for insn in md.disasm(bytes(code), address):
        print(f"  {insn.address:#x}: {insn.mnemonic} {insn.op_str}")

mu.hook_add(UC_HOOK_CODE, hook_code)
```

### 3.3 Use Cases

| Use Case | Approach |
|---|---|
| Unpack shellcode | Map shellcode, emulate, dump decoded payload |
| Decrypt strings | Emulate decryption function with controlled inputs |
| Brute-force short keys | Loop emulation with different key inputs |
| Analyze obfuscated function | Emulate function, observe register/memory state |
| Firmware code emulation | Map firmware memory layout, emulate routines |

---

## 4. ANGR EXPLORATION STRATEGIES

### 4.1 find/avoid

```python
simgr.explore(
    find=lambda s: b"Correct" in s.posix.dumps(1),   # stdout contains "Correct"
    avoid=lambda s: b"Wrong" in s.posix.dumps(1)      # avoid "Wrong" output
)
```

### 4.2 Managing Path Explosion

| Strategy | Implementation |
|---|---|
| Constrain input space | Add constraints (printable, length limits) |
| Avoid dead-end paths | Use `avoid=` for known failure addresses |
| Hook complex functions | Replace with simplified SimProcedure |
| Limit loop iterations | `state.options.add(angr.options.LAZY_SOLVES)` |
| Use veritesting | `simgr.explore(..., technique=angr.exploration_techniques.Veritesting())` |
| DFS instead of BFS | `simgr.use_technique(angr.exploration_techniques.DFS())` |
| Timeout per path | `simgr.explore(..., num_find=1)` + timeout wrapper |

### 4.3 Concrete + Symbolic Hybrid

```python
state = proj.factory.entry_state(
    add_options={angr.options.UNICORN}  # use Unicorn for concrete regions
)
```

This dramatically speeds up execution: concrete code runs natively via Unicorn, switching to symbolic only when symbolic variables are involved.

---

## 5. PRACTICAL WORKFLOW

### 5.1 CTF Binary Solving Workflow

```
1. Static analysis: identify input method, success/fail conditions
   └─ Find "Correct" / "Wrong" strings → get their xref addresses

2. Choose tool:
   ├─ Pure math (no binary needed) → Z3
   ├─ Small binary, clear success/fail → angr explore
   └─ Specific function to emulate → Unicorn

3. Set up symbolic input:
   ├─ stdin → claripy.BVS + entry_state(stdin=)
   ├─ argv → full_init_state(args=[...])
   ├─ file input → SimFile
   └─ specific memory → state.memory.store(addr, sym)

4. Hook problematic functions:
   ├─ printf/puts → SimProcedure or no-op
   ├─ scanf → custom handler
   ├─ time/random → return concrete value
   └─ anti-debug → skip entirely

5. Explore and extract:
   └─ simgr.explore(find=, avoid=) → solver.eval()
```

---

## 6. DECISION TREE

```
Need to solve a reversing challenge?
│
├─ Is the challenge pure math / equations?
│  └─ Yes → Z3
│     ├─ Linear equations → BitVec + Solver
│     ├─ Modular arithmetic → BitVec (natural mod 2^n)
│     ├─ Boolean logic → Bool + Solver
│     └─ Optimization → Optimize + minimize/maximize
│
├─ Is it a compiled binary with clear success/fail?
│  └─ Yes → angr
│     ├─ Input via stdin → symbolic stdin
│     ├─ Input via argv → full_init_state with symbolic args
│     ├─ Input via file → SimFile
│     ├─ Path explosion → add constraints, avoid paths, hook loops
│     └─ Complex library calls → hook with SimProcedure
│
├─ Need to emulate a specific function/region?
│  └─ Yes → Unicorn Engine
│     ├─ Decryption routine → map code + data, emulate, read result
│     ├─ Shellcode analysis → map shellcode, hook syscalls
│     └─ Key schedule → emulate with different inputs
│
├─ Need to analyze firmware / exotic arch?
│  └─ Yes → Qiling (full system emulation with OS support)
│
├─ Binary has VM protection?
│  └─ angr for handler analysis + Z3 for bytecode constraints
│
└─ None of the above working?
   ├─ Combine: Unicorn for concrete regions + Z3 for constraints
   ├─ Manual reverse engineering with debugger
   └─ Side-channel approach (timing, power analysis for hardware)
```

---

## 7. COMMON PITFALLS & FIXES

| Problem | Cause | Fix |
|---|---|---|
| angr hangs forever | Path explosion in loops | Add `avoid=` for loop-back edges, or hook the loop |
| Z3 returns `unknown` | Non-linear constraints too complex | Simplify, split into sub-problems, use `set_param("timeout", 5000)` |
| Unicorn crashes on syscall | Syscall not handled | Hook syscall interrupt, handle or skip |
| angr wrong result | Incorrect state initialization | Verify initial memory layout matches actual binary |
| Symbolic memory too large | Unbounded symbolic reads | Concretize array indices where possible |
| SimProcedure wrong types | Argument type mismatch | Check calling convention (cdecl vs fastcall) |
| angr can't load binary | Missing libraries | Use `auto_load_libs=False` + hook needed symbols |

---

## 8. TOOL VERSIONS & INSTALLATION

```bash
# angr (Python 3.8+)
pip install angr

# Z3
pip install z3-solver

# Unicorn Engine
pip install unicorn

# Capstone (disassembly, pairs with Unicorn)
pip install capstone

# Keystone (assembly)
pip install keystone-engine
```

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the **constraint model faithful** to the binary's actual semantics? | a wrong model solves a different program |
| 2 | Was the solution **fed back into the original binary** and observed? | the only end-to-end proof |
| 3 | Was there a **negative control**: a wrong input that the binary rejects? | the check has a failing side |
| 4 | Did the solver report `unsat` anywhere a solution is known to exist? | the model is over-constrained |
| 5 | Is the solving **reproducible** from the script, on this and a sibling sample? | a session is not evidence |
| 6 | What are the **model's approximations** - concretisation, timeouts, unsupported SIMD? | where the result may be wrong |
| 7 | Which **analysis goal** did the constraint solving reach? | solving a predicate is an intermediate step |

**A model that reproduces the binary's own verdict on a control input, and a solution the binary accepts.**
A satisfying assignment from a hand-built model proves the model, not the binary.

---

## 10. EXECUTION PRIMITIVES

A symbolic-execution result is proven by **a solution the original binary accepts, a negative control it
rejects, and a faithfulness argument for the model**. A satisfiable constraint from a hand-written model
proves the model.

### 10.1 The faithfulness loop, which is the whole discipline

```python
# THE ORDER: binary -> trace -> model -> solver -> BINARY AGAIN. The last arrow is the proof.
print("=== THE FAITHFULNESS LOOP ===")
for s in [
  "1. run the REAL binary on random inputs and record the branch trace",
  "2. build the model, and REPLAY the same inputs through it",
  "3. the model's branch sequence must match the binary's on every input - if it diverges, so does",
  "   your model, and every solution it produces is a solution to a DIFFERENT program",
  "4. solve the model to obtain a candidate input",
  "5. FEED THE CANDIDATE TO THE REAL BINARY. Its verdict, not the model's, is the finding",
  "6. feed a NEAR-MISS candidate and confirm the binary REJECTS it (the negative control)",
]:
    print("  ", s)
print()
print("=== THE FAITHFULNESS HARNESS ===")
import random
def equivalence_check(binary_run, model_run, n=200, seed=0):
    """Replay random inputs through both. Report the FIRST divergence, not a success rate."""
    random.seed(seed)
    for i in range(n):
        inp = bytes(random.randrange(256) for _ in range(64))
        b, m = binary_run(inp), model_run(inp)
        if b != m:
            return {"faithful": False, "at_input": i, "binary": b, "model": m, "input": inp.hex()}
    return {"faithful": True, "n": n}
print("  equivalence_check returns a FALSIFIER: the first input where the model and the binary")
print("  disagree. That input is what you iterate on. A 'faithful' verdict is only ever provisional,")
print("  and it is bounded by n - state n in the report.")
print()
print("=== THE STANDARD ERRORS, all model-faithfulness failures ===")
for e in ["assuming a C `int` is a mathematical integer, where overflow WRAPS (a common missed constraint)",
          "concretising a symbolic pointer to its first observed value",
          "ignoring `char` signedness, which differs by platform, in a byte comparison",
          "treating `strlen` as a pure function when the input is symbolic and unbounded",
          "letting angr time out on a path and reporting the REMAINING paths as all paths",
          "modelling a hash or PRNG as symbolic when the solver cannot invert it (it will time out)"]:
    print("  -", e)
print()
print("=== unbounded loops: bound them explicitly and REPORT the bound ===")
print("  every run must state its step limit, timeout, and the number of paths abandoned.")
print("  'the solver found no solution' with 4,000 abandoned paths is NOT 'unsat'.")
```

**The replay harness returns a falsifier, and the state count must be reported.** "No solution" with
abandoned paths is not `unsat`, and reporting it as such is the family's most common error.

### 10.2 The binary-as-oracle proof

```bash
# the ONLY end-to-end proof: the candidate goes back into the real binary
BIN="./crackme"
echo "=== STEP 1: the negative control - a near-miss the binary MUST reject ==="
printf '%s' "AAAAAAAAAAAAAAAA" | "$BIN"; echo "  exit=$?  <- must be non-zero"
echo
echo "=== STEP 2: the solver's candidate - the binary MUST accept it ==="
# the candidate comes from the solver, not from a guess
read -r CAND < candidate.txt
printf '%s' "$CAND" | "$BIN"; echo "  exit=$?  <- must be zero"
echo
echo "=== STEP 3: the solver's own arm, re-run through the model, to confirm determinism ==="
python3 solve.py --input candidate.txt --verify-model
echo
echo "=== STEP 4: perturb the candidate by ONE byte and confirm rejection ==="
python3 - "$CAND" <<'PY'
import sys, subprocess
c = bytearray(sys.argv[1].encode())
for i in range(min(len(c), 8)):
    d = bytearray(c); d[i] ^= 0x01
    r = subprocess.run(["./crackme"], input=bytes(d), capture_output=True)
    print(f"  flip byte {i}: exit={r.returncode} {'REJECTED' if r.returncode else 'ACCEPTED <-- a second solution, or the check does not depend on this byte'}")
PY
echo
echo "  A byte that may be flipped with the binary still accepting means the model has FREE variables"
echo "  the solver happened to pin. That is not an error, but the report must say the solution is one"
echo "  of a family rather than unique."
```

**Byte-flip perturbation is the cheap test for a non-unique solution.** If the binary still accepts, the
solver pinned a free variable and the solution is one of a family.

### 10.3 Soundness limits, stated as part of the result

```python
LIMITS = {
 "timeout":            "the wall-clock cap. Paths hit it and were ABANDONED, not proven unsatisfiable.",
 "step limit":         "the per-path instruction cap, with the same caveat.",
 "path explosion":     "the count of live states at abandonment. A high count means coverage is unproven.",
 "concretisation":     "every symbol the engine pinned to a concrete value, and where.",
 "unsupported insns":  "SIMD, crypto intrinsics, syscalls the engine stubbed rather than modelled.",
 "external calls":     "library calls that were summarised rather than executed - the biggest soundness hole.",
 "symbolic size":      "bytes symbolic per input. A 4-byte symbolic read cannot express an 8-byte key.",
 "memory model":       "whether uninitialised reads were treated as zero or as symbolic.",
}
print("%-22s %s" % ("limit","what it invalidates if unreported"))
for k, v in LIMITS.items(): print("%-22s %s" % (k, v))
print()
print("=== THE RULE ===")
print("  'unsat' from a run with abandoned paths, stubbed libc, or a 4-byte symbolic input is NOT a")
print("  proof of unreachability. Report the limits WITH the verdict, and never state a negative")
print("  result more strongly than the limits support.")
print()
print("=== THE FALSE-NEGATIVE this prevents ===")
print("  reporting 'this branch is unreachable' when the engine simply ran out of time. The")
print("  follow-up work of an analyst who trusts that verdict is wasted, and the error is silent.")
```

**Never state a negative result more strongly than the limits support.** `unsat` from a run with abandoned
paths or stubbed libc is not a proof of unreachability, and the error is silent.

### 10.4 The end-to-end harness

```bash
python3 - <<'PY'
print("=== SYMBOLIC EXECUTION ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the engine, its version, and its configuration are recorded",
  "angr/z3 behaviour changes between versions and between engines"),
 ("the model was REPLAYED against the real binary on 200+ random inputs",
  "the first divergence is the model's bug; without this step nothing downstream is valid"),
 ("every CONCRETISATION and STUBBED call is listed",
  "these are where the model and the binary diverge"),
 ("the state count at abandonment is reported, with the timeout and step limit",
  "'no solution' with abandoned paths is not 'unsat'"),
 ("the candidate was fed to the REAL binary, and it accepted",
  "the binary is the only oracle; the model's verdict is not evidence"),
 ("a NEAR-MISS candidate was rejected by the binary",
  "the negative control: the check has a failing side"),
 ("a single-byte perturbation was tested",
  "if the binary still accepts, the solution is one of a family and the report must say so"),
 ("the solving script is committed alongside the result",
  "a session's work is not reproducible and has no value beyond one binary"),
 ("the analysis GOAL was reached",
  "solving a predicate is an intermediate step, not the finding"),
 ("the soundness limits are stated with the verdict",
  "'unsat' must never be stronger than the limits support"),
]
for n, how in CHECKS: print("  [ ] %-62s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  engine  : name, version, configuration, and the symbolic sizes used")
print("  model   : the faithfulness replay's result and its n, or the divergence if there was one")
print("  limits  : concretisations, stubbed calls, timeout, steps, abandoned states")
print("  proof   : the binary accepting the candidate, and rejecting the near-miss")
print("  family  : whether the solution is unique, from the perturbation test")
print("  script  : the committed solver invocation")
PY
```

**Faithfulness, limits, binary-accepts, negative control, uniqueness, script.** The limits line is not
optional and belongs beside the verdict, not in an appendix.

---

## 11. EVIDENCE STANDARD — SOLVER ARTEFACTS

| Item | Why |
|---|---|
| The **engine, version, and configuration**, with the symbolic sizes | behaviour differs across versions and engines |
| The **faithfulness replay**: n, and the first divergence if any | the model's validity is the precondition |
| Every **concretisation** and **stubbed call** | exactly where the model and the binary diverge |
| The **timeout, step limit, and abandoned-state count** | a negative result is bounded by these |
| The **candidate input**, and the **binary's verdict** on it | the only end-to-end proof |
| The **near-miss input** and the binary's **rejection** | the negative control |
| The **single-byte perturbation** results | proves whether the solution is unique or one of a family |
| The **solver script**, quoted, with its invocation | reproducibility on the next sample |
| The **analysis goal** reached | solving a predicate is intermediate |
| The **unsupported instructions** and summarised library calls | the soundness holes, named |

Report the **model and the oracle**: "angr `9.x` with z3 `4.x` was given 8 symbolic bytes at the
`fgets` buffer. Replaying `200` random inputs through the model and the real binary produced identical
branch sequences, so the model is faithful for the explored region, and the replay script reports any
divergence as a falsifier. The solution `K9f3#Lm2` exits `0` against the real binary, and a near-miss
`K9f3#Lm3` exits `1`, which is the negative control. Flipping any of the last three bytes still exits
`0`, so those bytes are free variables and the solution is one of a family rather than unique, which the
report states. `angr` abandoned `312` states at the `90`-second timeout, and `strlen` and `memcmp` were
summarised rather than executed, so the 'no other path reaches the success branch' claim is NOT made and
the search's coverage is stated as bounded rather than complete", never "the symbolic execution proved
there is no other way to pass the check".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A satisfiable assignment from a **hand-built model**, never run against the binary | proves the model, not the program |
| A model that **diverged** from the binary on replay | every downstream solution is to a different program |
| **"unsat"** from a run with abandoned paths or a timeout | bounded, not proven |
| A **concretised pointer** treated as the input's real value | the model pinned what was symbolic |
| A **stubbed** `strcmp`/`strlen` verdict treated as executed | the summarisation is the soundness hole |
| A single 4-byte symbolic input for an 8-byte key check | the symbolic size cannot express the key |
| A solution the binary **rejects** | the model is wrong, and the replay step would have shown it |
| A solution **byte-flipped** still accepted, reported as unique | it is one of a family |
| A crash reached by the **explorer** but never reproduced | a state artefact, not a finding |
| An engine's **timeout** reported as "no vulnerabilities found" | a negative claim beyond the limits |

**A faithful model, a binary-accepted candidate, a rejected near-miss, and stated limits.** A model's own
`sat` verdict and an unbounded `unsat` claim are this family's two standard non-findings.

---

## 12. REMEDIATION REFERENCE — SOLVER METHODOLOGY

1. **Replay the model against the real binary on 200+ random inputs before trusting any solution, and treat the first divergence as the bug to fix** - a model's `sat` verdict proves the model rather than the program.
2. **Feed every candidate back into the real binary and report its verdict, never the solver's** - the binary is the oracle.
3. **Always run a near-miss negative control and confirm the binary rejects it** - a check with no failing side is not a check.
4. **Perturb the solution by one byte at a time to test uniqueness, and report a family when the binary still accepts** - the solver pins free variables it happened to pick.
5. **State the engine, its version, its configuration, and the symbolic input sizes with every result** - angr and z3 behaviour changes between versions, and a 4-byte symbolic read cannot express an 8-byte key.
6. **List every concretisation and every summarised library call, because they are exactly where the model and the binary diverge** - `strcmp` and `strlen` summarisations are the largest soundness holes.
7. **Report the timeout, step limit, and abandoned-state count beside every negative verdict** - "no solution with 312 abandoned states" is not `unsat`, and the distinction is the whole value of a negative result.
8. **Model integer overflow explicitly, using bitvectors of the correct width and signedness** - a C `int` that wraps is the most frequently missed constraint.
9. **Bound unbounded loops explicitly and report the bound** - an unstated loop bound makes the coverage claim unfalsifiable.
10. **Commit the solver script with the report** - a session's work cannot be re-run on a sibling sample.
11. **Never state a negative result more strongly than the limits support: unsat from a bounded run is a bounded claim** - an overclaimed unreachability verdict silently wastes the next analyst's work.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [vm-and-bytecode-reverse](../vm-and-bytecode-reverse/SKILL.md) - when the predicate lives inside a VM
- [code-obfuscation-deobfuscation](../code-obfuscation-deobfuscation/SKILL.md) - the opaque predicates a solver removes
- [binary-protection-bypass](../binary-protection-bypass/SKILL.md) - the wider hardening-bypass methodology
- [anti-debugging-techniques](../anti-debugging-techniques/SKILL.md) - the checks that break a solve mid-run
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - how a bounded result is reported honestly
