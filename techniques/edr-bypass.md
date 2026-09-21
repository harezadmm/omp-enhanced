# EDR BYPASS — ADVANCED TECHNIQUES

> Level: GOD TIER — tested against CrowdStrike, Microsoft Defender, SentinelOne, Elastic EDR
> Extracted from CORE.md — load on-demand when EDR bypass / AV evasion tasks arrive.

## Userland Bypass
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

## Kernel Bypass
1. **BYOVD (Bring Your Own Vulnerable Driver)**: Load signed driver with known vuln, exploit for ring 0
2. **Kernel Callback Removal**: ObRegisterCallbacks, CmRegisterCallback, MiniFilter, PsSet*NotifyRoutine
3. **WFP Callout**: Windows Filtering Platform to block EDR telemetry network traffic
4. **EDR Process Kill**: Terminate EDR process via kernel handle, ZWTerminateProcess
5. **Retrosigned Drivers**: Use expired cross-signing certs + system time manipulation
6. **Blindside**: Hardware breakpoints (Dr0-Dr7) for EDR evasion without software hooks

## Tools & PoCs
| Tool | Technique | Target |
|------|-----------|--------|
| SysWhispers3 | Direct/indirect syscalls | All EDRs |
| HellsGate | Syscall number resolution via memory | Hooked EDRs |
| HaloGate | Adjacent syscall technique | Hooked EDRs |
| TartarusGate | Runtime SSN + syscall address resolution | All EDRs |
| EDRSilencer | WFP to block EDR telemetry network | Network-based EDR |
| RealBlindingEDR | Remove ALL kernel callbacks | Kernel-based EDR |
| Backstab | Kill protected AV/EDR processes | All EDRs |
| Pyramid | Operate in EDR blind spots | Python-based EDR |
| Chimera | DLL sideloading with EDR evasion | Signature-based EDR |
| EDRSandblast | Exploit EDR driver vulnerabilities | Driver-based EDR |
| Ruy-Lopez | Prevent DLL loading in new processes | DLL-monitoring EDR |
| dark-kill | Process creation blocking + terminate | Kernel EDR |
| mhydeath | Abuse mhyprotect to kill AV/EDR | Protected processes |
| TopazTerminator | EDR killer via BYOVD | All EDRs |

## Living Off the Land (LotL)
- **Living Off the Blindspot**: Operate in EDR blind spots using Python (PEP 57 hooks)
- **BYOSI (Bring Your Own Script Interpreter)**: Deploy custom interpreter to bypass EDR hooks
- **Polydrop**: Extended BYOSI with 12+ language support
- **Bring Your Own Container**: Use container isolation to hide from EDR
- **Living Off the Land Binaries (LOLBAS)**: Use legitimate Windows binaries for offensive ops
