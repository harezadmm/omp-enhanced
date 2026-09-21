# Trainer Development

**Domain:** GAME HACKING & MEMORY EDITING — CHEAT ENGINE OPERATIONS

## Overview
- **Cheat Engine Lua**: Auto-assembler scripts, Lua scripting
- **C# Trainer**: MemorySharp, BlackMagic, Memory.dll
- **Python**: ReadProcessMemory, pymem, WriteProcessMemory
- **C++**: Direct WinAPI (OpenProcess, ReadProcessMemory, WriteProcessMemory)

## Full Doctrine

- **Cheat Engine Lua**: Auto-assembler scripts, Lua scripting
- **C# Trainer**: MemorySharp, BlackMagic, Memory.dll
- **Python**: ReadProcessMemory, pymem, WriteProcessMemory
- **C++**: Direct WinAPI (OpenProcess, ReadProcessMemory, WriteProcessMemory)

#### Python Trainer Template
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

#### Cheat Engine Auto-Assembler
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

## References
- LTX-QUASAR CORE.md (persona doctrine)
