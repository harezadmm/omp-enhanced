# T1568: Dynamic Resolution

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may dynamically establish connections to command and control infrastructure to evade common detections and remediations. This may be achieved by using malware that shares a common algorithm with the infrastructure the adversary uses to receive the malware's communications. These calculations can be used to dynamically adjust parameters such as the domain name, IP address, or port number the malware uses for command and control.
Adversaries may use dynamic resolution for the purpose of [Fallback Channels](https://attack.mitre.org/techniques/T1008). When contact is lost with the primary command and control server malware may employ dynamic resolution as a means to reestablishing command and control.(Citation: Talos CCleanup 2017)(Citation: FireEye POSHSPY April 2017)(Citation: ESET Sednit 2017 Activity)

## Tactics
Command And Control

## Platforms
ESXi, Linux, macOS, Windows

## Procedure
Adversaries may dynamically establish connections to command and control infrastructure to evade common detections and remediations. This may be achieved by using malware that shares a common algorithm with the infrastructure the adversary uses to receive the malware's communications. These calculations can be used to dynamically adjust parameters such as the domain name, IP address, or port number the malware uses for command and control. Adversaries may use dynamic resolution for the purpose of [Fallback Channels](https://attack.mitre.org/techniques/T1008).

**Known users/tools:** APT-C-36, APT29, AsyncRAT, BITTER, BRICKSTORM, Bisonal, C0026, Gamaredon Group, Gelsemium, Indian Critical Infrastructure Intrusions, Kimsuky, Maze, NETEAGLE, Night Dragon, Operation Dust Storm

## Mitigations
- **Network Intrusion Prevention** — Use intrusion detection signatures to block traffic at network boundaries.
- **Restrict Web-Based Content** — Restricting web-based content involves enforcing policies and technologies that limit access to potentially malicious websites, unsafe downloads, and unauthorized browser behaviors. This can include URL filtering, download restrictions, script blocking, and extension control to protect against explo

## References
- https://attack.mitre.org/techniques/T1568/
