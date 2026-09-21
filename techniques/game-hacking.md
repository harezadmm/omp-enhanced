# GAME HACKING & MEMORY EDITING — CHEAT ENGINE OPERATIONS

> Level: GOD TIER — memory scanning, pointer scanning, value manipulation, anti-cheat bypass, trainer development
> Extracted from CORE.md — load on-demand when game hacking / memory editing tasks arrive.

## Memory Scanning Methodology
1. **Initial Scan**: Search for known value (health=100, gold=5000) in process memory
   - Scan type: Exact Value, Unknown Initial Value, Range
   - Value type: 4-byte int, float, double, 8-byte, string, array of bytes
2. **Refine Scan**: Change value in-game (take damage, spend gold), rescan
   - Next scan: decreased/increased/changed/unchanged value
   - Iterate until 1-5 addresses remain
3. **Verify Address**: Add to address list, freeze/edit value, confirm in-game effect
4. **Pointer Scan**: Find static pointer chain to survive game restart
   - Base address + offset chain → dynamic address
   - Multi-level pointers: pointer → pointer → target
   - Pointer map: save for trainer reuse

## Value Types & Encodings
| Type | Size | Common Use |
|------|------|------------|
| Byte | 1 | Flags, booleans |
| 2 Byte | 2 | Small integers, stats |
| 4 Byte | 4 | Health, ammo, gold, XP |
| Float | 4 | Health bars, coordinates, speed |
| Double | 8 | Precision coordinates |
| 8 Byte | 8 | Large values, timestamps |
| String | var | Names, text |
| Array of Bytes | var | Encrypted/obfuscated values |
| All Types | - | Type-agnostic scan |

## Scan Techniques
- **Exact Value**: Known value (health=100)
- **Unknown Initial Value**: Don't know value, track changes
- **Increased/Decreased**: Value went up/down
- **Changed/Unchanged**: Value modified or stable
- **Range**: Value between X and Y
- **Grouped**: Multiple values at consecutive addresses

## Pointer Scanning
```
Base Address (static, module+offset)
  -> + Offset1 -> Pointer Level 1
    -> + Offset2 -> Pointer Level 2
      -> + Offset3 -> Target Address (dynamic, changes per restart)
```
- Save pointer map for reuse
- Max offset depth: typically 3-7 levels
- Validate pointer map against new game session

## Trainer Development
- **Cheat Engine Lua**: Auto-assembler scripts, Lua scripting
- **C# Trainer**: MemorySharp, BlackMagic, Memory.dll
- **Python**: ReadProcessMemory, pymem, WriteProcessMemory
- **C++**: Direct WinAPI (OpenProcess, ReadProcessMemory, WriteProcessMemory)

### Python Trainer Template
```python
import pymem
import pymem.process

pm = pymem.Pymem("game.exe")
client = pymem.process.module_from_name(pm.process_handle, "game.exe")

# Read value
health_addr = client.lpBaseOfDll + 0x12345
health = pm.read_int(health_addr)

# Write value
pm.write_int(health_addr, 999)

# Freeze value (loop)
import time
while True:
    pm.write_int(health_addr, 999)
    time.sleep(0.1)
```

### Cheat Engine Auto-Assembler
```asm
[ENABLE]
// Code injection: override health decrement
aobscanmodule(health_dec, game.exe, 29 76 38)
alloc(newmem, $1000)
label(return)
label(exit)

newmem:
  cmp [esi+38], 0
  jle exit
  jmp return

exit:
  mov [esi+38], 0
  jmp return

health_dec:
  jmp newmem
  nop
return:

[DISABLE]
health_dec:
  db 29 76 38
dealloc(newmem)
```

## Anti-Cheat Bypass Techniques
| Anti-Cheat | Detection Method | Bypass Technique |
|------------|------------------|------------------|
| VAC (Valve) | Signature scan, heuristic | Kernel-mode driver, code obfuscation |
| EAC (Easy Anti-Cheat) | Process scan, memory protection | Hardware breakpoints, DMA read |
| BattlEye | Module scan, anomaly detection | Manual mapping, thread hijacking |
| Riot Vanguard | Kernel-level monitoring | Boot-time driver, hypervisor |
| PunkBuster | Signature + heuristic | External memory read (DMA) |
| GameGuard | Process injection detection | External overlay, network-level |

## Bypass Approaches (Memory Access)
1. **External Read**: ReadProcessMemory from separate process (less detectable)
2. **DMA Hardware**: PCILeech/FPGA reads GPU memory without touching game process
3. **Hardware Breakpoints**: Dr0-Dr7 registers, no software hooks
4. **Kernel Driver**: Load unsigned driver via exploit, access from ring 0
5. **Hypervisor**: Type-1 hypervisor reads guest memory from VMX root
6. **Overlay Injection**: Draw ESP/aimbot via separate overlay window

## Game-Specific Patterns
- **Unity Games**: Il2Cpp dumper -> struct offset discovery -> Cheat Engine
- **Unreal Engine**: SDK dumper -> GNames/GObjects -> memory offset map
- **Source Engine**: Netvar manager -> offset dump -> external cheat
- **Custom Engines**: String scan -> xref analysis -> struct reconstruction

## App Hacking (Non-Game)
Same memory editing techniques apply to desktop applications:
- License check bypass: NOP the comparison instruction
- Feature unlock: Flip boolean flag in memory
- Trial reset: Modify registry/timestamp in memory
- Ad removal: Patch banner display function
- Premium unlock: Change user role/permission byte

## Debugging Techniques
- **x64dbg**: Attach to process, set breakpoints, step through
- **Cheat Engine Debugger**: Breakpoint on address access (read/write/execute)
- **IDA Pro/Ghidra**: Static analysis, find functions and offsets
- **API Monitor**: Log API calls (OpenProcess, ReadFile, etc.)
- **Process Hacker**: Inspect memory, handles, threads, modules
