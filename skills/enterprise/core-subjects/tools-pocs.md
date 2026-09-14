# Tools & PoCs

**Domain:** EDR BYPASS — ADVANCED TECHNIQUES (GitHub-researched)

## Overview
| Tool | Technique | Target |
|------|-----------|--------|
| SysWhispers3 | Direct/indirect syscalls | All EDRs |
| HellsGate | Syscall number resolution via memory | Hooked EDRs |

## Full Doctrine

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

## References
- LTX-QUASAR CORE.md (persona doctrine)
