---
name: vm-and-bytecode-reverse
description: >-
  Custom VM and bytecode reverse engineering playbook. Use when CTF challenges
  or protected software implement custom virtual machines with proprietary
  bytecode, dispatcher loops, or maze-style challenges.
---

# SKILL: VM & Bytecode Reverse Engineering — Expert Analysis Playbook

> **AI LOAD INSTRUCTION**: Expert techniques for reversing custom virtual machines and bytecode interpreters. Covers dispatcher identification, opcode mapping, custom ISA reconstruction, disassembler/decompiler writing, maze challenges, and real-world VM protector analysis. Base models often fail to recognize the fetch-decode-execute pattern or attempt to analyze VM bytecode as native code.

## 0. RELATED ROUTING

- [code-obfuscation-deobfuscation](../code-obfuscation-deobfuscation/SKILL.md) when the VM is a commercial protector (VMProtect/Themida)
- [symbolic-execution-tools](../symbolic-execution-tools/SKILL.md) when using angr to solve VM-based challenges
- [anti-debugging-techniques](../anti-debugging-techniques/SKILL.md) when the VM includes anti-debug checks

### Quick identification

| Binary Pattern | Likely VM Type | Start With |
|---|---|---|
| `while(1) { switch(bytecode[pc]) }` | Switch-based dispatcher | Map each case to an operation |
| Indirect jump via table `jmp [table + opcode*8]` | Table-based dispatcher | Dump jump table, analyze handlers |
| Nested if-else chain on byte value | If-chain dispatcher | Same as switch, just different syntax |
| Stack push/pop dominant operations | Stack-based VM | Identify push, pop, arithmetic ops |
| `reg[X] = ...` array operations | Register-based VM | Map register indices to operations |
| 2D grid + direction input | Maze challenge | Extract grid, apply BFS/DFS |

---

## 1. CUSTOM VM IDENTIFICATION

### 1.1 Structural Indicators

```
VM Architecture Components:
┌─────────────────────────────────┐
│  Bytecode Program (data section)│
├─────────────────────────────────┤
│  Program Counter (pc/ip)        │
│  Register File / Stack          │
│  Memory / Data Area             │
├─────────────────────────────────┤
│  Dispatcher Loop                │
│  ├─ Fetch: opcode = code[pc]    │
│  ├─ Decode: lookup handler      │
│  └─ Execute: run handler        │
└─────────────────────────────────┘
```

### 1.2 IDA/Ghidra Signatures

**Switch dispatcher** (most common in CTF):
```c
while (running) {
    unsigned char op = bytecode[pc++];
    switch (op) {
        case 0x00: /* nop */       break;
        case 0x01: /* push imm */  stack[sp++] = bytecode[pc++]; break;
        case 0x02: /* add */       stack[sp-2] += stack[sp-1]; sp--; break;
        // ...
        case 0xFF: /* halt */      running = 0; break;
    }
}
```

**Table dispatcher** (more optimized):
```c
typedef void (*handler_t)(vm_ctx_t*);
handler_t handlers[256] = { handle_nop, handle_push, handle_add, ... };

while (running) {
    handlers[bytecode[pc++]](&ctx);
}
```

---

## 2. ANALYSIS METHODOLOGY

### Step 1: Find the Dispatcher

Look for:
- Large switch statement (many cases) in a loop
- Array of function pointers indexed by a byte from a data buffer
- Single function with high cyclomatic complexity
- Cross-references to a data buffer read byte-by-byte

### Step 2: Map Opcodes to Operations

For each case/handler, determine:

| Property | How to Identify |
|---|---|
| Opcode value | Case number or table index |
| Operation type | Register/stack modifications |
| Operand count | How many bytes consumed after opcode |
| Operand type | Immediate value, register index, or memory address |
| Side effects | Output, memory write, flag modification |

### Step 3: Extract Bytecode Program

```python
# Typical extraction from binary
import struct

with open('challenge', 'rb') as f:
    f.seek(bytecode_offset)
    bytecode = f.read(bytecode_length)

# Or from IDA:
# bytecode = idc.get_bytes(bytecode_addr, bytecode_len)
```

### Step 4: Write Custom Disassembler

```python
OPCODES = {
    0x00: ("nop",  0),    # (mnemonic, operand_bytes)
    0x01: ("push", 1),    # push immediate byte
    0x02: ("pop",  0),
    0x03: ("add",  0),
    0x04: ("sub",  0),
    0x05: ("xor",  0),
    0x06: ("cmp",  0),
    0x07: ("jmp",  2),    # jump to 16-bit address
    0x08: ("je",   2),
    0x09: ("jne",  2),
    0x0A: ("mov",  2),    # mov reg, imm
    0x0B: ("load", 1),    # load from memory[operand]
    0x0C: ("store",1),    # store to memory[operand]
    0x0D: ("print",0),
    0x0E: ("read", 0),    # read input
    0xFF: ("halt", 0),
}

def disassemble(bytecode):
    pc = 0
    while pc < len(bytecode):
        op = bytecode[pc]
        if op not in OPCODES:
            print(f"  {pc:04x}: UNKNOWN {op:#04x}")
            pc += 1
            continue

        mnemonic, operand_size = OPCODES[op]
        operands = bytecode[pc+1:pc+1+operand_size]
        operand_str = ' '.join(f'{b:#04x}' for b in operands)
        print(f"  {pc:04x}: {mnemonic:8s} {operand_str}")
        pc += 1 + operand_size

disassemble(bytecode)
```

### Step 5: Analyze Disassembled Program

With the custom disassembly, apply standard reverse engineering:
- Identify input reading (read opcode)
- Trace data flow from input to comparison
- Determine success/failure conditions
- Extract the check logic (often XOR/ADD transformations of input compared against constants)

---

## 3. COMMON VM PATTERNS IN CTF

### 3.1 Stack-Based VM

Operations work on a stack (like JVM or Python bytecode).

| Opcode | Operation | Stack Effect |
|---|---|---|
| PUSH imm | Push immediate value | [...] → [..., imm] |
| POP | Discard top | [..., a] → [...] |
| ADD | Add top two | [..., a, b] → [..., a+b] |
| SUB | Subtract | [..., a, b] → [..., a-b] |
| MUL | Multiply | [..., a, b] → [..., a*b] |
| XOR | Bitwise XOR | [..., a, b] → [..., a^b] |
| CMP | Compare | [..., a, b] → [..., (a==b)] |
| JMP addr | Unconditional jump | no change |
| JZ addr | Jump if top is zero | [..., a] → [...] |
| PRINT | Output top as char | [..., a] → [...] |
| READ | Read char to stack | [...] → [..., input] |
| HALT | Stop execution | - |

### 3.2 Register-Based VM

Operations use register indices (like x86, ARM).

| Opcode | Format | Operation |
|---|---|---|
| MOV r, imm | `0x01 RR II II` | reg[R] = imm16 |
| MOV r1, r2 | `0x02 R1 R2` | reg[R1] = reg[R2] |
| ADD r1, r2 | `0x03 R1 R2` | reg[R1] += reg[R2] |
| SUB r1, r2 | `0x04 R1 R2` | reg[R1] -= reg[R2] |
| XOR r1, r2 | `0x05 R1 R2` | reg[R1] ^= reg[R2] |
| CMP r1, r2 | `0x06 R1 R2` | flags = compare(r1, r2) |
| JMP addr | `0x07 AA AA` | pc = addr |
| JE addr | `0x08 AA AA` | if equal: pc = addr |
| LOAD r, [addr] | `0x09 RR AA` | reg[R] = mem[addr] |
| STORE [addr], r | `0x0A AA RR` | mem[addr] = reg[R] |
| SYSCALL | `0x0B` | I/O operation based on reg[0] |
| HALT | `0xFF` | stop |

### 3.3 Brainfuck-like / Esoteric VMs

| BF Command | VM Equivalent | Description |
|---|---|---|
| `>` | INC ptr | Move data pointer right |
| `<` | DEC ptr | Move data pointer left |
| `+` | INC [ptr] | Increment byte at pointer |
| `-` | DEC [ptr] | Decrement byte at pointer |
| `.` | OUTPUT [ptr] | Output byte at pointer |
| `,` | INPUT [ptr] | Input byte to pointer |
| `[` | JZ forward | Jump past `]` if byte is zero |
| `]` | JNZ back | Jump back to `[` if byte is nonzero |

---

## 4. MAZE CHALLENGES

### 4.1 Identification

- Binary reads directional input (WASD, arrow keys, UDLR)
- 2D array in data section (walls, paths, start, end)
- Position tracking with x,y coordinates
- Win condition at specific coordinates

### 4.2 Map Extraction

```python
# Extract maze grid from binary data section
MAZE_ADDR = 0x601060
WIDTH = 20
HEIGHT = 15

# From binary dump:
maze = []
for row in range(HEIGHT):
    line = ""
    for col in range(WIDTH):
        cell = bytecode[MAZE_ADDR + row * WIDTH + col - base_addr]
        if cell == 0: line += "."    # path
        elif cell == 1: line += "#"  # wall
        elif cell == 2: line += "S"  # start
        elif cell == 3: line += "E"  # end
        else: line += "?"
    maze.append(line)
    print(line)
```

### 4.3 Automated Solving

```python
from collections import deque

def solve_maze(maze, start, end):
    """BFS solver returns direction string."""
    rows, cols = len(maze), len(maze[0])
    directions = {'U': (-1, 0), 'D': (1, 0), 'L': (0, -1), 'R': (0, 1)}
    queue = deque([(start, "")])
    visited = {start}

    while queue:
        (r, c), path = queue.popleft()
        if (r, c) == end:
            return path

        for name, (dr, dc) in directions.items():
            nr, nc = r + dr, c + dc
            if (0 <= nr < rows and 0 <= nc < cols and
                maze[nr][nc] != '#' and (nr, nc) not in visited):
                visited.add((nr, nc))
                queue.append(((nr, nc), path + name))

    return None

# Find start and end positions
for r, row in enumerate(maze):
    for c, cell in enumerate(row):
        if cell == 'S': start = (r, c)
        if cell == 'E': end = (r, c)

solution = solve_maze(maze, start, end)
print(f"Path: {solution}")
```

### 4.4 Direction Encoding

Different challenges encode directions differently:

| Encoding | Up | Down | Left | Right |
|---|---|---|---|---|
| WASD | W | S | A | D |
| UDLR | U | D | L | R |
| Arrow keys | ↑ (0x48) | ↓ (0x50) | ← (0x4B) | → (0x4D) |
| Numbers | 1 | 2 | 3 | 4 |
| Hex opcodes | 0x01 | 0x02 | 0x03 | 0x04 |

---

## 5. REAL-WORLD VM PROTECTORS

### 5.1 VMProtect Analysis Approach

```
1. Find VM entry: search for pushad/pushfd sequence
2. Identify VM context structure (registers, flags, bytecode pointer)
3. Locate handler table (often obfuscated with opaque predicates)
4. For each handler:
   a. Remove junk code / opaque predicates
   b. Identify the core operation
   c. Document handler semantics
5. Trace bytecode execution (instruction-level trace)
6. Reconstruct original code from trace
```

### 5.2 Tigress Obfuscator

Academic VM obfuscator with configurable protection layers.

| Feature | Approach |
|---|---|
| Single-dispatch VM | Standard handler extraction |
| Split handlers | Handlers spread across multiple functions |
| Nested VMs | Outer VM handler invokes inner VM |
| Encrypted bytecode | Dynamic decryption before each fetch |
| Polymorphic handlers | Different code for same operation on each build |

### 5.3 Common VM Protector Patterns

| Protector | Dispatcher Style | Difficulty |
|---|---|---|
| VMProtect | Table + opaque predicates | High |
| Themida (Code Virtualizer) | CISC-like, large handler set | High |
| Tigress | Configurable, academic | Medium-High |
| Custom CTF VM | Simple switch | Low-Medium |
| Movfuscator | All-mov computation | Medium |

---

## 6. TOOLS

| Tool | Purpose | Usage |
|---|---|---|
| IDA Pro | Identify dispatcher, reverse handlers | F5 decompile, xref analysis |
| Ghidra | Free alternative with Sleigh processor modules | Write custom processor for VM ISA |
| angr | Symbolic execution through VM | Treat entire VM as constraint system |
| Pin / DynamoRIO | Dynamic instrumentation for tracing | Record opcode handler execution sequence |
| REVEN | Full-system trace recording | Replay and analyze VM execution |
| Unicorn | Emulate VM execution | Fast handler emulation |
| Miasm | IR-based analysis | Lift VM handlers to IR for analysis |
| Custom Python | Write disassembler/decompiler | Per-challenge custom tooling |

### Ghidra Sleigh Processor Module

For recurring VM architectures, write a Sleigh processor specification:

```
define space ram      type=ram_space      size=2  default;
define space register type=register_space  size=1;

define register offset=0 size=1 [ R0 R1 R2 R3 FLAGS PC SP ];

define token opcode(8)
    op = (0,7)
;

:NOP    is op=0x00 { }
:PUSH   imm is op=0x01; imm { SP = SP - 1; *[ram]:1 SP = imm; }
:POP    is op=0x02 { SP = SP + 1; }
:ADD    is op=0x03 { local a = *[ram]:1 (SP+1); *[ram]:1 (SP+1) = a + *[ram]:1 SP; SP = SP + 1; }
```

---

## 7. DECISION TREE

```
Binary contains custom bytecode interpreter?
│
├─ Can you identify the dispatcher?
│  ├─ Yes (switch/table/if-chain)
│  │  ├─ Few opcodes (< 20) → Simple CTF VM
│  │  │  ├─ Stack-based → map push/pop/arithmetic ops
│  │  │  ├─ Register-based → map mov/add/cmp ops
│  │  │  └─ Write disassembler → analyze program → solve
│  │  │
│  │  └─ Many opcodes (50+) → Commercial protector
│  │     ├─ Known protector → use specific deprotection tools
│  │     └─ Custom → trace execution, pattern-match handlers
│  │
│  └─ No clear dispatcher
│     ├─ All-mov instructions → movfuscator
│     ├─ Encrypted bytecode → find decryption, dump after decode
│     └─ Split/distributed handlers → trace execution to find them
│
├─ Is it a maze challenge?
│  ├─ Extract grid from data section
│  ├─ Identify direction encoding
│  ├─ BFS/DFS to find shortest path
│  └─ Convert path to expected input format
│
├─ Is there input validation in VM?
│  ├─ Small input space → brute-force via Unicorn emulation
│  ├─ Known format → constrained angr solve
│  └─ Complex check → write disassembler, analyze check logic
│
└─ Multiple VM layers (VM in VM)?
   ├─ Analyze outer VM first
   ├─ Extract inner bytecode
   ├─ Repeat analysis for inner VM
   └─ Consider: symbolic execution may handle nested VMs directly
```

---

## 8. CTF SOLVING WORKFLOW

```
1. Run the binary — understand I/O behavior
   └─ What input does it expect? What output on success/failure?

2. Open in IDA/Ghidra — find the main loop
   └─ Look for while/for loop with switch or indirect jump

3. Identify VM components:
   ├─ Bytecode location (where is the program data?)
   ├─ PC/IP variable (how is current position tracked?)
   ├─ Registers/stack (where is VM state stored?)
   └─ I/O handlers (which opcodes read input / write output?)

4. Map all opcodes (create the ISA specification)
   └─ For each case/handler: opcode number, operation, operands

5. Write disassembler in Python
   └─ Output readable assembly for the bytecode

6. Analyze the disassembled program:
   ├─ Find input reading
   ├─ Trace transformations applied to input
   ├─ Find comparison against expected values
   └─ Reverse the transformation to find valid input

7. Solve:
   ├─ If simple transforms (XOR, ADD) → reverse manually
   ├─ If complex → feed to Z3 as constraints
   └─ If maze → extract grid, run pathfinding
```

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Is there a **dispatcher loop** with a computed jump, and where is the bytecode array? | a VM was identified, not assumed |
| 2 | What is the **handler table's** shape and how many handlers exist? | the instruction set's size, which is the work estimate |
| 3 | Did the **devirtualised form reproduce the original's behaviour** on generated inputs? | equivalence, the only proof |
| 4 | Was there a **control** - a build with no VM, or a function with no dispatcher? | the recovery is not inventing structure |
| 5 | Is the devirtualiser a **script** that re-runs on the family? | reusability, which is the finding's value |
| 6 | What is **left unresolved**: handlers, keys, or handlers reached only at runtime? | the honest scope |
| 7 | Which **analysis goal** did devirtualisation enable? | the technique is an intermediate result |

**A dispatcher and bytecode located, a handler table enumerated, a scripted devirtualiser, and a
behavioural equivalence.** "There is a VM" is an observation.

---

## 10. EXECUTION PRIMITIVES

A VM-protection finding is proven by **a located dispatcher and bytecode array, an enumerated handler
table, a scripted devirtualiser, and a behavioural equivalence against the original**. Spotting a
dispatcher is the beginning.

### 10.1 Locating the dispatcher, deterministically

```python
# the mechanical signals for a custom VM, each checkable in a disassembly listing
import re, subprocess, json
from collections import Counter

def disasm(path):
    return subprocess.run(["objdump","-d","--no-show-raw-insn","-M","intel",path],
                          capture_output=True, text=True).stdout

VM_SIGNALS = {
 "indirect jump through a register":  r'jmp\s+(r(?:a|b|c|d|s|8|9|1[0-5])|e(?:ax|bx|cx|dx|si|di))',
 "jump table read":                   r'jmp\s+QWORD PTR \[.*\*8.*\]|jmp\s+QWORD PTR \[\w+\+\w+\*8\]',
 "handler table in .rodata":          "a contiguous run of code pointers in a data section",
 "dispatch counter":                  r'(add|sub)\s+(dword ptr )?\[rbp-0x[0-9a-f]+\],\s*1',
 "bytecode pointer advance":          r'(add|lea)\s+r\w+,\s*\[r\w+\+(0x)?1\]',
 "bounds check before jump":          r'cmp\s+\w+,\s*0x[0-9a-f]+\s*\n\s*j(a|b|be|ae)\b',
}
def signals(text):
    hits = Counter()
    for name, pat in VM_SIGNALS.items():
        if name.endswith("table"): continue
        hits[name] = len(re.findall(pat, text, re.M))
    return hits

print("=== THE SIGNAL SET, and the SHAPE that distinguishes a VM from ordinary indirect code ===")
for k, v in VM_SIGNALS.items(): print("  %-34s %s" % (k, v if isinstance(v,str) else v))
print()
print("=== THE DISTINGUISHING SHAPE (all three must be present at the SAME address) ===")
for s in ["1. a loop whose body ENDS in an indirect jump",
          "2. a table indexed by a value read from a DATA region (the bytecode), not from a register set by the caller",
          "3. the same loop achieving a large share of the function's total instruction count"]:
    print("  ", s)
print()
print("=== THE CONTROL: a switch statement compiled with a jump table ===")
print("  a compiler-generated switch has signal 1 and 2 but NOT 3, and its table's targets are")
print("  prologue-complete blocks rather than handlers that RETURN TO THE SAME DISPATCHER.")
print("  Run the same detector on a known switch-heavy binary: if it reports a VM, the detector")
print("  cannot tell a VM from a switch, and every VM claim from it is void.")
print()
print("=== RECORD, for any VM you name ===")
for r in ["the dispatcher's address and the bytecode array's address and length",
          "the handler count and the table's base", "the bytecode's size in bytes",
          "the handler that is the most frequent, which is usually the VM's 'mov'"]:
    print("  -", r)
```

**The switch-heavy control binary is what validates the detector.** A detector that reports a VM in an
ordinary jump-table switch cannot distinguish a VM from a switch, and every claim from it is void.

### 10.2 Handler semantics, recovered mechanically

```python
# recover each handler's semantics by EMULATION with a distinctive marker value, not by reading it
import struct

def probe_handler(handler_addr, trace_fn, marker=0x4142434445464748):
    """Run ONE handler with a marker in every register and on the stack, then read the diff.
    The marker makes the handler's effect VISIBLE instead of inferred."""
    before = {"regs": trace_fn.regs(handler_addr), "stack": trace_fn.stack(handler_addr)}
    trace_fn.single_step_to(handler_addr)         # emulate exactly one handler
    after  = {"regs": trace_fn.regs(trace_fn.next_dispatch()), "stack": trace_fn.stack(trace_fn.next_dispatch())}
    return {"reg_delta":  {k: (before["regs"].get(k), after["regs"].get(k))
                           for k in before["regs"] if before["regs"].get(k) != after["regs"].get(k)},
            "stack_delta": {"before": before["stack"], "after": after["stack"]}}

print("=== THE HANDLER-CLASSIFICATION METHOD ===")
CLASSES = {
 "arith":   "changes a register by a VALUE derived from the bytecode's operand -> group by the delta",
 "stack":   "changes rsp and writes to the new top",
 "load":    "reads from the memory the bytecode operand names",
 "store":   "writes to the memory the bytecode operand names",
 "branch":  "writes the NEXT bytecode index rather than advancing by a constant",
 "call":    "pushes a return index and jumps outside the VM's own code region",
 "compare": "writes flags but no general register (verify with eflags before/after)",
}
for k, v in CLASSES.items(): print("  %-10s %s" % (k, v))
print()
print("=== THE MECHANICAL PROOF that two handlers are the SAME operation ===")
print("  feed both handlers the SAME marker state and compare the register and stack deltas.")
print("  identical deltas across the whole marker set means they are the same op modulo encoding.")
print()
print("=== THE CONTROL, which stops you from inventing semantics ===")
print("  build a TEST bytecode program of a known meaning (e.g. 3 + 4) and run it in the VM.")
print("  your recovered handler set must EXECUTE it to 7. A handler table that cannot run a")
print("  program whose meaning you know is not correctly recovered, however neat it looks.")
print()
print("=== THE STANDARD ERROR ===")
print("  assigning a handler an opcode based on its POSITION in the table. The opcode is in the")
print("  BYTECODE; the table index is an implementation detail. Read the bytecode, not the table.")
```

**The known-meaning test program is the control for the handler set.** A recovered table that cannot
execute `3 + 4` to `7` is not correctly recovered, however tidy the classification looks.

### 10.3 Devirtualisation, and the equivalence proof

```python
# the devirtualiser must be a SCRIPT that runs on the family, not a session
print("=== THE DEVIRTUALISER'S SHAPE ===")
for s in [
  "1. read the bytecode array and the handler table from the binary, by address",
  "2. lift each handler to an IR operation, using the marker-probe deltas rather than a reading",
  "3. walk the bytecode, emitting the IR, and RESOLVE branches by the handler that writes the index",
  "4. emit a diffable artefact (pseudo-C, LLVM IR, or a Python model of the computation)",
  "5. RE-RUN steps 1-4 on a second sample in the family, changing only the addresses",
]:
    print("  ", s)
print()
print("=== THE EQUIVALENCE ARMS, all three required ===")
arms = {
 "the VM's own IO":     "feed the ORIGINAL binary and the devirtualised model the same input; the "
                        "outputs must match byte for byte",
 "the known-meaning arm": "a bytecode program whose meaning you know must execute to the known result",
 "the differential arm":  "100+ generated inputs, diffed. A VM may have a rare handler that only "
                          "one input reaches, and one input cannot find it",
}
for k, v in arms.items(): print("  %-22s %s" % (k, v))
print()
print("=== THE CONTROL INSTRUMENT: a program the VM DOES NOT TRACE ===")
print("  if the sample emits untraced native code for some functions, run the devirtualiser against")
print("  one of THOSE addresses. It must report 'not VM code'. A devirtualiser that lifts native")
print("  code is misreading the handler signatures.")
print()
print("=== WHAT MUST NOT BE CLAIMED ===")
for b in ["that the recovered IR is the ORIGINAL source (the VM's semantics are not the compiler's)",
          "that an unmapped handler is 'unused' (it may be reached only through a computed index)",
          "that a single matching input demonstrates equivalence"]:
    print("  -", b)
```

**The untraced-native control is what proves the devirtualiser reads VM code.** A devirtualiser that lifts
ordinary native code is misreading its own handler signatures.

### 10.4 The end-to-end harness

```bash
python3 - <<'PY'
print("=== VM DEVIRTUALISATION ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the artifact's SHA-256 is recorded before analysis",
  "an unrecorded input makes the result unreproducible"),
 ("the dispatcher and the bytecode array are both LOCATED, by address",
  "a loop that looks like a dispatcher is not a VM until the bytecode is found"),
 ("the distinguishing shape was confirmed: loop + data-driven table + instruction dominance",
  "a compiled switch has the first two and not the third"),
 ("a SWITCH-HEAVY control binary was run through the detector",
  "it must report no VM, or the detector cannot distinguish a VM from a switch"),
 ("the handler table was enumerated, with its count and base",
  "the handler count IS the work estimate and belongs in the report"),
 ("handler semantics were recovered by MARKER PROBING, not by reading",
  "a marker makes the effect visible instead of inferred"),
 ("a KNOWN-MEANING bytecode program was executed to its known result",
  "the control that stops you from inventing semantics"),
 ("the devirtualiser is a SCRIPT that re-runs on a second sample",
  "a session's work is not reusable and has no value beyond one binary"),
 ("equivalence was tested on the known-meaning arm, the IO arm, and 100+ generated inputs",
  "a VM may have a rare handler that only one input reaches"),
 ("an UNTRACED-NATIVE address was fed to the devirtualiser",
  "it must report 'not VM code'; otherwise the signature reading is wrong"),
 ("what remains unmapped is stated explicitly",
  "an honest partial recovery is usable; an overclaimed complete one is not"),
]
for n, how in CHECKS: print("  [ ] %-62s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  artifact  : SHA-256, architecture, and the protector's build if identifiable")
print("  geometry  : dispatcher address, bytecode address and length, handler count and base")
print("  method    : marker probing plus the lifting script, quoted")
print("  proof     : the known-meaning arm, the IO arm, and the differential result")
print("  controls  : the switch-heavy detector control and the untraced-native control")
print("  residual  : unmapped handlers and paths reached only at runtime")
PY
```

**Geometry, method, three equivalence arms, two controls, residual.** The geometry line is what makes the
work estimate possible for the next sample in the family.

---

## 11. EVIDENCE STANDARD — DEVIRTUALISATION ARTEFACTS

| Item | Why |
|---|---|
| The **SHA-256** and the architecture of the analysed artefact | the input identity |
| The **dispatcher's address** and the **bytecode array's address and length** | the VM is located, not inferred |
| The **distinguishing shape**: loop, data-driven table, and instruction dominance | separates a VM from a compiled switch |
| The **switch-heavy control's** detector result | validates the detector |
| The **handler count** and the **table base** | the work estimate, and it belongs in the report |
| The **marker-probe deltas** per handler | the semantics, recovered mechanically |
| The **known-meaning program** and its executed result | the control against invented semantics |
| The **devirtualiser script**, quoted | reusability across the family |
| The **equivalence arms**: known-meaning, IO, and the 100+ input differential | one input proves nothing |
| The **untraced-native control's** result | proves the devirtualiser reads VM code |
| The **residual**: unmapped handlers and runtime-only paths | the honest scope |

Report the **geometry and the equivalence**: "the sample's SHA-256 is `c4b0…` and is x86-64. The
dispatcher is at `0x401f40`, a loop whose body ends in `jmp rax` with the state read from a bytecode array
at `0x603000` of `0x1c40` bytes, and it accounts for `0.63` of the function's instruction count, which is
the third signal that distinguishes it from a compiled switch. The detector was run against a known
switch-heavy binary and reported no VM, which is the control. The handler table at `0x602e00` holds 47
entries, and marker probing with a distinctive value in every register recovered 41 of the 47 as
arithmetic, stack, load, store, branch, call, and compare classes. A bytecode program whose meaning is
`3 + 4` executed in the VM to `7`, and the devirtualiser's model reproduces the original's stdout and exit
code for `100 of 100` generated inputs. Feeding the devirtualiser the address of a function the sample
emits as untraced native code returned `not VM code`, which is the second control. Six handlers remain
unmapped, three of which are reached only through computed indices at runtime, and the residual is stated
in the report", never "the sample uses a custom VM protection".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| An **indirect jump** in a loop, with no bytecode array | ordinary indirect dispatch, not a VM |
| A **compiled switch** from a `switch` statement | not a VM, and the control proves the detector's discrimination |
| A detector that reports a VM in a **switch-heavy control** | the detector cannot discriminate; fix it |
| A handler table **classified but never executed** | the known-meaning control was skipped |
| Opcodes assigned from the **table's index** | the opcode is in the bytecode; the index is an implementation detail |
| A single input demonstrating **equivalence** | a VM may have a rare handler |
| A **session-only** devirtualisation | not reproducible on the next sample |
| The **recovered IR** presented as the original source | the VM's semantics are not the compiler's |
| An **unmapped** handler called "unused" | it may be reached through a computed index |
| A **protector's name** with no bytecode address or handler count | a classification, not a result |

**A located dispatcher with a bytecode array, a marker-probed handler set, a scripted devirtualiser, and
three equivalence arms.** An indirect jump and a protector's brand are this family's two standard
non-findings.

---

## 12. REMEDIATION REFERENCE — VM-PROTECTION COST AND ANALYSIS

1. **Record the artefact's SHA-256 and analyse copies, so results stay reproducible across the family** - an unrecorded input makes the geometry you report unverifiable.
2. **Locate both the dispatcher and the bytecode array before claiming a VM, and require the third signal (instruction dominance)** - a loop with an indirect jump and a table is also a compiled switch.
3. **Validate the detector against a switch-heavy binary and require it to report no VM** - a detector that cannot tell a switch from a VM has no evidentiary value.
4. **Recover handler semantics by marker probing rather than by reading the disassembly** - the marker makes the effect visible, and a reading proves only self-consistency.
5. **Execute a bytecode program of known meaning as the control for the handler set** - a table that cannot compute `3 + 4` to `7` is not correctly recovered, however neat it looks.
6. **Write the devirtualiser as a script parameterised by addresses, and re-run it on a second sample in the family** - the scheme's reusability is where the work's value lies.
7. **Test equivalence on a known-meaning arm, an IO arm, and 100+ generated inputs** - a VM may have a handler that only a rare input reaches.
8. **Feed the devirtualiser an untraced-native address and require `not VM code`** - it proves the handler signatures are being read correctly.
9. **State the residual explicitly: which handlers, keys, and paths remain unmapped** - an honest partial recovery is usable and an overclaim is not.
10. **Read opcodes from the bytecode rather than from the handler table's index** - the index is an implementation detail that changes between builds.
11. **Report the geometry (dispatcher address, bytecode length, handler count) rather than the protector's name** - the geometry is what lets the next analyst estimate the work before starting.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [code-obfuscation-deobfuscation](../code-obfuscation-deobfuscation/SKILL.md) - the transformations that accompany a VM
- [anti-debugging-techniques](../anti-debugging-techniques/SKILL.md) - the checks that guard the dispatcher
- [binary-protection-bypass](../binary-protection-bypass/SKILL.md) - the wider hardening-bypass methodology
- [symbolic-execution-tools](../symbolic-execution-tools/SKILL.md) - solving the VM's predicates rather than lifting them
- [reverse-shell-techniques](../reverse-shell-techniques/SKILL.md) - the analysis-goal context for a protected sample
