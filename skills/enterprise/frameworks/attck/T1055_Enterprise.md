# T1055: Process Injection

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may inject code into processes in order to evade process-based defenses as well as possibly elevate privileges. Process injection is a method of executing arbitrary code in the address space of a separate live process. Running code in the context of another process may allow access to the process's memory, system/network resources, and possibly elevated privileges. Execution via process injection may also evade detection from security products since the execution is masked under a legitimate process.
There are many different ways to inject code into a process, many of which abuse legitimate functionalities. These implementations exist for every major OS but are typically platform specific.
More sophisticated samples may perform multiple process injections to segment modules and further evade detection, utilizing named pipes or other inter-process communication (IPC) mechanisms as a communication channel.

## Tactics
Stealth, Privilege Escalation

## Platforms
Linux, macOS, Windows

## Procedure
Adversaries may inject code into processes in order to evade process-based defenses as well as possibly elevate privileges. Process injection is a method of executing arbitrary code in the address space of a separate live process. Running code in the context of another process may allow access to the process's memory, system/network resources, and possibly elevated privileges. Execution via process injection may also evade detection from security products since the execution is masked under a legitimate process.

**Known users/tools:** 2015 Ukraine Electric Power Attack, 3CX Supply Chain Attack, ABK, ANDROMEDA, APT32, APT37, APT38, APT41, APT5, Agent Tesla, ArcaneDoor, Attor, AuditCred, Avenger, BADHATCH

## Mitigations
- **Behavior Prevention on Endpoint** — Behavior Prevention on Endpoint refers to the use of technologies and strategies to detect and block potentially malicious activities by analyzing the behavior of processes, files, API calls, and other endpoint events. Rather than relying solely on known signatures, this approach leverages heuristic
- **Privileged Account Management** — Privileged Account Management focuses on implementing policies, controls, and tools to securely manage privileged accounts (e.g., SYSTEM, root, or administrative accounts). This includes restricting access, limiting the scope of permissions, monitoring privileged account usage, and ensuring accounta

## References
- https://attack.mitre.org/techniques/T1055/
