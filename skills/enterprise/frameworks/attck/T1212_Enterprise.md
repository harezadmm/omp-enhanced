# T1212: Exploitation for Credential Access

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may exploit software vulnerabilities in an attempt to collect credentials. Exploitation of a software vulnerability occurs when an adversary takes advantage of a programming error in a program, service, or within the operating system software or kernel itself to execute adversary-controlled code.
Credentialing and authentication mechanisms may be targeted for exploitation by adversaries as a means to gain access to useful credentials or circumvent the process to gain authenticated access to systems. One example of this is `MS14-068`, which targets Kerberos and can be used to forge Kerberos tickets using domain user permissions.(Citation: Technet MS14-068)(Citation: ADSecurity Detecting Forged Tickets) Another example of this is replay attacks, in which the adversary intercepts data packets sent between parties and then later replays these packets. If services don't properly validate authentication requests, these replayed packets may allow an adversary to impersonate one of the parties and gain unauthorized access or privileges.(Citation: Bugcrowd Replay Attack)(Citation: Comparitech Replay Attack)(Citation: Microsoft Midnight Blizzard Replay Attack)
Such exploitation has been demonstrated in cloud environments as well. For example, adversaries have exploited vulnerabilities in public cloud infrastructure that allowed for unintended authentication token creation and renewal.(Citation: Storm-0558 techniques for unauthorized email access)
Exploitation for credential access may also result in Privilege Escalation depending on the process targeted or credentials obtained.

## Tactics
Credential Access

## Platforms
Linux, Windows, macOS, Identity Provider

## Procedure
Adversaries may exploit software vulnerabilities in an attempt to collect credentials. Exploitation of a software vulnerability occurs when an adversary takes advantage of a programming error in a program, service, or within the operating system software or kernel itself to execute adversary-controlled code. Credentialing and authentication mechanisms may be targeted for exploitation by adversaries as a means to gain access to useful credentials or circumvent the process to gain authenticated access to systems. One example of this is `MS14-068`, which targets Kerberos and can be used to forge Kerberos tickets using domain user permissions.(Citation: Technet MS14-068)(Citation: ADSecurity Detecting Forged Tickets) Another example of this is replay attacks, in which the adversary intercepts data packets sent between parties and then later replays these packets.

**Known users/tools:** Leviathan Australian Intrusions, UNC3886

## Mitigations
- **Application Developer Guidance** — Application Developer Guidance focuses on providing developers with the knowledge, tools, and best practices needed to write secure code, reduce vulnerabilities, and implement secure design principles. By integrating security throughout the software development lifecycle (SDLC), this mitigation aims
- **Threat Intelligence Program** — A Threat Intelligence Program enables organizations to proactively identify, analyze, and act on cyber threats by leveraging internal and external data sources. The program supports decision-making processes, prioritizes defenses, and improves incident response by delivering actionable intelligence 
- **Application Isolation and Sandboxing** — Application Isolation and Sandboxing refers to the technique of restricting the execution of code to a controlled and isolated environment (e.g., a virtual environment, container, or sandbox). This method prevents potentially malicious code from affecting the rest of the system or network by limitin
- **Exploit Protection** — Deploy capabilities that detect, block, and mitigate conditions indicative of software exploits. These capabilities aim to prevent exploitation by addressing vulnerabilities, monitoring anomalous behaviors, and applying exploit-mitigation techniques to harden systems and software.
- **Update Software** — Software updates ensure systems are protected against known vulnerabilities by applying patches and upgrades provided by vendors. Regular updates reduce the attack surface and prevent adversaries from exploiting known security gaps. This includes patching operating systems, applications, drivers, an

## References
- https://attack.mitre.org/techniques/T1212/
