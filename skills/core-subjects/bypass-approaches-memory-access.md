# Bypass Approaches (Memory Access)

**Domain:** GAME HACKING & MEMORY EDITING — CHEAT ENGINE OPERATIONS

## Overview
1. **External Read**: ReadProcessMemory from separate process (less detectable)
2. **DMA Hardware**: PCILeech/FPGA reads GPU memory without touching game process
3. **Hardware Breakpoints**: Dr0-Dr7 registers, no software hooks
4. **Kernel Driver**: Load unsigned driver via exploit, access from ring 0

## Full Doctrine

1. **External Read**: ReadProcessMemory from separate process (less detectable)
2. **DMA Hardware**: PCILeech/FPGA reads GPU memory without touching game process
3. **Hardware Breakpoints**: Dr0-Dr7 registers, no software hooks
4. **Kernel Driver**: Load unsigned driver via exploit, access from ring 0
5. **Hypervisor**: Type-1 hypervisor reads guest memory from VMX root
6. **Overlay Injection**: Draw ESP/aimbot via separate overlay window

## References
- LTX-QUASAR CORE.md (persona doctrine)
