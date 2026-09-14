# T1567: Exfiltration Over Web Service

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may use an existing, legitimate external Web service to exfiltrate data rather than their primary command and control channel. Popular Web services acting as an exfiltration mechanism may give a significant amount of cover due to the likelihood that hosts within a network are already communicating with them prior to compromise. Firewall rules may also already exist to permit traffic to these services.
Web service providers also commonly use SSL/TLS encryption, giving adversaries an added level of protection.

## Tactics
Exfiltration

## Platforms
ESXi, Linux, macOS, Office Suite, SaaS, Windows

## Procedure
Adversaries may use an existing, legitimate external Web service to exfiltrate data rather than their primary command and control channel. Popular Web services acting as an exfiltration mechanism may give a significant amount of cover due to the likelihood that hosts within a network are already communicating with them prior to compromise. Firewall rules may also already exist to permit traffic to these services. Web service providers also commonly use SSL/TLS encryption, giving adversaries an added level of protection.

**Known users/tools:** APT28, APT28 Nearest Neighbor Campaign, Anthropic AI-orchestrated Campaign, AppleSeed, BlackByte, C0017, Contagious Interview, DropBook, Exbyte, InvisibleFerret, Magic Hound, OilCheck, Salesforce Data Exfiltration, SampleCheck5000, ShinyHunters

## Mitigations
- **Restrict Web-Based Content** — Restricting web-based content involves enforcing policies and technologies that limit access to potentially malicious websites, unsafe downloads, and unauthorized browser behaviors. This can include URL filtering, download restrictions, script blocking, and extension control to protect against explo
- **Data Loss Prevention** — Data Loss Prevention (DLP) involves implementing strategies and technologies to identify, categorize, monitor, and control the movement of sensitive data within an organization. This includes protecting data formats indicative of Personally Identifiable Information (PII), intellectual property, or f

## References
- https://attack.mitre.org/techniques/T1567/
