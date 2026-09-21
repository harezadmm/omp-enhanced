# T1001: Data Obfuscation

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may obfuscate command and control traffic to make it more difficult to detect.(Citation: Bitdefender FunnyDream Campaign November 2020) Command and control (C2) communications are hidden (but not necessarily encrypted) in an attempt to make the content more difficult to discover or decipher and to make the communication less conspicuous and hide commands from being seen. This encompasses many methods, such as adding junk data to protocol traffic, using steganography, or impersonating legitimate protocols.

## Tactics
Command And Control

## Platforms
ESXi, Linux, macOS, Windows

## Procedure
Adversaries may obfuscate command and control traffic to make it more difficult to detect.(Citation: Bitdefender FunnyDream Campaign November 2020) Command and control (C2) communications are hidden (but not necessarily encrypted) in an attempt to make the content more difficult to discover or decipher and to make the communication less conspicuous and hide commands from being seen. This encompasses many methods, such as adding junk data to protocol traffic, using steganography, or impersonating legitimate protocols.

**Known users/tools:** DarkGate, FRAMESTING, FlawedAmmyy, FunnyDream, Gamaredon Group, Ninja, Okrum, Operation Wocao, RDAT, SLOTHFULMEDIA, SideTwist, StrelaStealer, SystemBC, TrailBlazer, evilginx2

## Mitigations
- **Network Intrusion Prevention** — Use intrusion detection signatures to block traffic at network boundaries.

## References
- https://attack.mitre.org/techniques/T1001/
