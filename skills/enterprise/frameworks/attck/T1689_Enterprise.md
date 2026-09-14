# T1689: Downgrade Attack

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may downgrade or use a version of system features that may be outdated, vulnerable, and/or does not support updated security controls. Downgrade attacks typically take advantage of a system’s backward compatibility to force it into less secure modes of operation.
Adversaries may downgrade and use various less-secure versions of features of a system, such as [Command and Scripting Interpreter](https://attack.mitre.org/techniques/T1059) or even network protocols that can be abused to enable [Adversary-in-the-Middle](https://attack.mitre.org/techniques/T1557) or [Network Sniffing](https://attack.mitre.org/techniques/T1040).(Citation: Praetorian TLS Downgrade Attack 2014) For example, [PowerShell](https://attack.mitre.org/techniques/T1059/001) versions 5+ includes Script Block Logging (SBL), which can record executed script content. However, adversaries may attempt to execute a previous version of PowerShell that does not support SBL with the intent to impair defenses while running malicious scripts that may have otherwise been detected.(Citation: CrowdStrike downgrade attack)(Citation: Google Cloud downgrade attack)(Citation: att_def_ps_logging)
Adversaries may similarly target network traffic to downgrade from an encrypted HTTPS connection to an unsecured HTTP connection that exposes network data in clear text.(Citation: Targeted SSL Stripping Attacks Are Real)(Citation: CrowdStrike Downgrade attack 2) On Windows systems, adversaries may downgrade the boot manager to a vulnerable version that bypasses Secure Boot, granting the ability to disable various operating system security mechanisms.(Citation: SafeBreach)

## Tactics
Defense Impairment

## Platforms
macOS, Windows, Linux

## Procedure
Adversaries may downgrade or use a version of system features that may be outdated, vulnerable, and/or does not support updated security controls. Downgrade attacks typically take advantage of a system’s backward compatibility to force it into less secure modes of operation. Adversaries may downgrade and use various less-secure versions of features of a system, such as [Command and Scripting Interpreter](https://attack.mitre.org/techniques/T1059) or even network protocols that can be abused to enable [Adversary-in-the-Middle](https://attack.mitre.org/techniques/T1557) or [Network Sniffing](https://attack.mitre.org/techniques/T1040).(Citation: Praetorian TLS Downgrade Attack 2014) For example, [PowerShell](https://attack.mitre.org/techniques/T1059/001) versions 5+ includes Script Block Logging (SBL), which can record executed script content. However, adversaries may attempt to execute a previous version of PowerShell that does not support SBL with the intent to impair defenses while running malicious scripts that may have otherwise been detected.(Citation: CrowdStrike downgrade attack)(Citation: Google Cloud downgrade attack)(Citation: att_def_ps_logging)
Adversaries may similarly target network traffic to downgrade from an encrypted HTTPS connection to an unsecured HTTP connection that exposes network data in clear text.(Citation: Targeted SSL Stripping Attacks Are Real)(Citation: CrowdStrike Downgrade attack 2) On Windows systems, adversaries may downgrade the boot manager to a vulnerable version that bypasses Secure Boot, granting the ability to disable various operating system security mechanisms.(Citation: SafeBreach)

**Known users/tools:** BlackByte Ransomware, FrostyGoop Incident, SILENTTRINITY

## Mitigations
- **Software Configuration** — Software configuration refers to making security-focused adjustments to the settings of applications, middleware, databases, or other software to mitigate potential threats. These changes help reduce the attack surface, enforce best practices, and protect sensitive data. This mitigation can be imple
- **Disable or Remove Feature or Program** — Disable or remove unnecessary and potentially vulnerable software, features, or services to reduce the attack surface and prevent abuse by adversaries. This involves identifying software or features that are no longer needed or that could be exploited and ensuring they are either removed or properly

## References
- https://attack.mitre.org/techniques/T1689/
