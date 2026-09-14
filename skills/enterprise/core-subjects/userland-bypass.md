# Userland Bypass

**Domain:** EDR BYPASS — ADVANCED TECHNIQUES (GitHub-researched)

## Overview
1. **Direct/Indirect Syscalls**: SysWhispers2/3, HellsGate, HaloGate — bypass NTDLL hooks
2. **NTDLL Unhooking**: Map clean NTDLL from disk, overwrite .text section
3. **AMSI Patching**: Patch AmsiScanBuffer to return AMSI_RESULT_CLEAN
4. **ETW Blinding**: Patch EtwEventWrite to NOP, blind telemetry

## Full Doctrine

1. **Direct/Indirect Syscalls**: SysWhispers2/3, HellsGate, HaloGate — bypass NTDLL hooks
2. **NTDLL Unhooking**: Map clean NTDLL from disk, overwrite .text section
3. **AMSI Patching**: Patch AmsiScanBuffer to return AMSI_RESULT_CLEAN
4. **ETW Blinding**: Patch EtwEventWrite to NOP, blind telemetry
5. **Sleep Obfuscation**: Ekko, Foliage — encrypt implant memory during sleep
6. **Stack Spoofing**: Forge thread call stack to look legitimate
7. **Module Stomping**: Load legitimate DLL, overwrite with payload
8. **Phantom DLL**: Load non-existent DLL, use allocated memory
9. **Callback Injection**: EnumSystemLocalesW, CreateTimerQueueTimer, PsmemLoad
10. **APC Injection**: QueueUserAPC, NtQueueApcThread, special user APC

## References
- LTX-QUASAR CORE.md (persona doctrine)
