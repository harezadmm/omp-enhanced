# T1688: Safe Mode Boot

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may abuse Windows safe mode to disable endpoint defenses. Safe mode starts up the Windows operating system with a limited set of drivers and services. Third-party security software such as endpoint detection and response (EDR) tools may not start after booting Windows in safe mode. There are two versions of safe mode: Safe Mode and Safe Mode with Networking. It is possible to start additional services after a safe mode boot.(Citation: Microsoft Windows Startup Settings)(Citation: Sophos Safe Mode Boot)
Adversaries may abuse safe mode to disable endpoint defenses that may not start with a limited boot. Hosts can be forced into safe mode after the next reboot via modifications to Boot Configuration Data (BCD) stores, which are files that manage boot application settings.(Citation: Microsoft bcdedit)
Adversaries may also add their malicious applications to the list of minimal services that start in safe mode by modifying relevant Registry values (i.e. [Modify Registry](https://attack.mitre.org/techniques/T1112)). Malicious [Component Object Model](https://attack.mitre.org/techniques/T1559/001) (COM) objects may also be registered and loaded in safe mode.(Citation: CyberArk Labs Safe Mode 2016)(Citation: Cybereason safe mode boot)(Citation: BleepingComputer REvil 2021)

## Tactics
Defense Impairment

## Platforms
Windows

## Procedure
Adversaries may abuse Windows safe mode to disable endpoint defenses. Safe mode starts up the Windows operating system with a limited set of drivers and services. Third-party security software such as endpoint detection and response (EDR) tools may not start after booting Windows in safe mode. There are two versions of safe mode: Safe Mode and Safe Mode with Networking.

**Known users/tools:** AvosLocker, Black Basta, Embargo, LockBit 3.0, Qilin, REvil, RansomHub

## Mitigations
- **Privileged Account Management** — Privileged Account Management focuses on implementing policies, controls, and tools to securely manage privileged accounts (e.g., SYSTEM, root, or administrative accounts). This includes restricting access, limiting the scope of permissions, monitoring privileged account usage, and ensuring accounta
- **Software Configuration** — Software configuration refers to making security-focused adjustments to the settings of applications, middleware, databases, or other software to mitigate potential threats. These changes help reduce the attack surface, enforce best practices, and protect sensitive data. This mitigation can be imple

## References
- https://attack.mitre.org/techniques/T1688/
