# T1560: Archive Collected Data

**Matrix:** Enterprise | **Type:** Technique

## Description
An adversary may compress and/or encrypt data that is collected prior to exfiltration. Compressing the data can help to obfuscate the collected data and minimize the amount of data sent over the network.(Citation: DOJ GRU Indictment Jul 2018) Encryption can be used to hide information that is being exfiltrated from detection or make exfiltration less conspicuous upon inspection by a defender.
Both compression and encryption are done prior to exfiltration, and can be performed using a utility, 3rd party library, or custom method.

## Tactics
Collection

## Platforms
Linux, macOS, Windows

## Procedure
An adversary may compress and/or encrypt data that is collected prior to exfiltration. Compressing the data can help to obfuscate the collected data and minimize the amount of data sent over the network.(Citation: DOJ GRU Indictment Jul 2018) Encryption can be used to hide information that is being exfiltrated from detection or make exfiltration less conspicuous upon inspection by a defender. Both compression and encryption are done prior to exfiltration, and can be performed using a utility, 3rd party library, or custom method.

**Known users/tools:** ADVSTORESHELL, APT28, APT32, Agent Tesla, AppleSeed, Aria-body, Axiom, BLUELIGHT, Backdoor.Oldrea, BlackByte, BloodHound, Bumblebee, Cadelspy, Chrommme, Daserf

## Mitigations
- **Audit** — Auditing is the process of recording activity and systematically reviewing and analyzing the activity and system configurations. The primary purpose of auditing is to detect anomalies and identify potential threats or weaknesses in the environment. Proper auditing configurations can also help to mee

## References
- https://attack.mitre.org/techniques/T1560/
