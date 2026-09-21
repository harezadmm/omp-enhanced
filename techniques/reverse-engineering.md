# REVERSE ENGINEERING & BINARY

> Level: GOD TIER — disassembly, memory manipulation, hooking, syscall unhooking, mitigation bypass
> Extracted from CORE.md — load on-demand when reverse engineering / binary tasks arrive.

## Disassembly & Analysis
- x86/x64 disassembly: IDA Pro, Ghidra, Binary Ninja, x64dbg, radare2/Cutter
- PE/COFF: sections, imports/exports, relocations, digital signatures
- Memory: AOB scanning with masks, pointer chain, heap/stack analysis

## Hooking
- Detour (manual/MinHook), IAT/EAT patching, VMT hooking, inline hooks, VEH

## Process Manipulation
- DLL injection (LoadLibrary/manual map/reflective), shellcode injection
- Process hollowing, thread hijacking, APC injection, atom bombing
- Kernel: PEB/TEB/EPROCESS/KTHREAD, token manipulation, handle hijacking

## Mitigation Bypass
- ASLR leak, DEP (ROP/ret2libc), CFG/CIG, PatchGuard, DSE, Secure Boot
- Direct syscalls: Hell's Gate, Halo's Gate, SysWhispers3

## EDR/AV Evasion
- AMSI patching, ETW blind, ntdll unhooking, sleep obfuscation, stack spoofing

## Exploit Dev
- Stack overflow (SEH, egg hunt), ROP chain, heap (UAF, double-free, tcache)
- Format string (GOT overwrite, arbitrary read/write)
