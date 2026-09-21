# Kernel Bypass

**Domain:** EDR BYPASS — ADVANCED TECHNIQUES (GitHub-researched)

## Overview
1. **BYOVD (Bring Your Own Vulnerable Driver)**: Load signed driver with known vuln, exploit for ring 0
2. **Kernel Callback Removal**: ObRegisterCallbacks, CmRegisterCallback, MiniFilter, PsSet*NotifyRoutine
3. **WFP Callout**: Windows Filtering Platform to block EDR telemetry network traffic
4. **EDR Process Kill**: Terminate EDR process via kernel handle, ZWTerminateProcess

## Full Doctrine

1. **BYOVD (Bring Your Own Vulnerable Driver)**: Load signed driver with known vuln, exploit for ring 0
2. **Kernel Callback Removal**: ObRegisterCallbacks, CmRegisterCallback, MiniFilter, PsSet*NotifyRoutine
3. **WFP Callout**: Windows Filtering Platform to block EDR telemetry network traffic
4. **EDR Process Kill**: Terminate EDR process via kernel handle, ZWTerminateProcess
5. **Retrosigned Drivers**: Use expired cross-signing certs + system time manipulation
6. **Blindside**: Hardware breakpoints (Dr0-Dr7) for EDR evasion without software hooks

## References
- LTX-QUASAR CORE.md (persona doctrine)
