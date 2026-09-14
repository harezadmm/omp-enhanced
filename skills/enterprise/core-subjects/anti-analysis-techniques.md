# Anti-Analysis Techniques

**Domain:** BLACK HAT CAPABILITIES — MALWARE DEVELOPMENT

## Overview
- **Anti-VM**: CPU count, RAM size, MAC OUI, registry keys, process list, timing
- **Anti-Debug**: PEB BeingDebugged, NtGlobalFlag, IsDebuggerPresent, NtQueryInformationProcess, hardware breakpoints
- **Anti-Dump**: Erase PE header, size of image manipulation, ERASEPEHeader
- **Anti-Sandbox**: Sleep acceleration detection, mouse movement, user interaction, API count

## Full Doctrine

- **Anti-VM**: CPU count, RAM size, MAC OUI, registry keys, process list, timing
- **Anti-Debug**: PEB BeingDebugged, NtGlobalFlag, IsDebuggerPresent, NtQueryInformationProcess, hardware breakpoints
- **Anti-Dump**: Erase PE header, size of image manipulation, ERASEPEHeader
- **Anti-Sandbox**: Sleep acceleration detection, mouse movement, user interaction, API count
- **Timing checks**: RDTSC, GetTickCount, QueryPerformanceCounter, system time analysis

---

## References
- LTX-QUASAR CORE.md (persona doctrine)
