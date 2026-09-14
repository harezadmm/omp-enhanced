# T1573: Encrypted Channel

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may employ an encryption algorithm to conceal command and control traffic rather than relying on any inherent protections provided by a communication protocol. Despite the use of a secure algorithm, these implementations may be vulnerable to reverse engineering if secret keys are encoded and/or generated within malware samples/configuration files.

## Tactics
Command And Control

## Platforms
ESXi, Linux, macOS, Network Devices, Windows

## Procedure
Adversaries may employ an encryption algorithm to conceal command and control traffic rather than relying on any inherent protections provided by a communication protocol. Despite the use of a secure algorithm, these implementations may be vulnerable to reverse engineering if secret keys are encoded and/or generated within malware samples/configuration files.

**Known users/tools:** APT29, BITTER, Chaes, Cryptoistic, Emotet, Gomir, KV Botnet Activity, Lizar, MacMa, Magic Hound, NETWIRE, PowGoop, PowerLess, RCSession, Triton Safety Instrumented System Attack

## Mitigations
- **Network Intrusion Prevention** — Use intrusion detection signatures to block traffic at network boundaries.
- **SSL/TLS Inspection** — SSL/TLS inspection involves decrypting encrypted network traffic to examine its content for signs of malicious activity. This capability is crucial for detecting threats that use encryption to evade detection, such as phishing, malware, or data exfiltration. After inspection, the traffic is re-encry

## References
- https://attack.mitre.org/techniques/T1573/
