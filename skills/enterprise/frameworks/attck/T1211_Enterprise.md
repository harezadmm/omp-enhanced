# T1211: Exploitation for Stealth

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may exploit vulnerabilities to evade detection by hiding activity, suppressing logging, or operating within trusted or unmonitored components.
Adversaries may exploit a system or application vulnerability to avoid detection while maintaining access within an environment. Exploitation occurs when an adversary leverages a programming flaw to execute code in a manner that minimizes visibility or blends in with legitimate activity.
Rather than directly disabling defenses, adversaries may use exploitation to circumvent monitoring and logging mechanisms. This can include abusing vulnerabilities in logging pipelines, security tools, or cloud infrastructure to evade audit trails, suppress alerts, or operate without generating telemetry.
Adversaries may identify these opportunities through prior reconnaissance or by performing discovery of security controls after initial access. In some cases, vulnerabilities in SaaS or public cloud environments may be exploited to evade logging, obscure activity, or deploy infrastructure that remains hidden from standard monitoring tools.(Citation: Bypassing CloudTrail in AWS Service Catalog)(Citation: GhostToken GCP flaw)

## Tactics
Stealth

## Platforms
Linux, Windows, macOS, SaaS, IaaS

## Procedure
Adversaries may exploit vulnerabilities to evade detection by hiding activity, suppressing logging, or operating within trusted or unmonitored components. Adversaries may exploit a system or application vulnerability to avoid detection while maintaining access within an environment. Exploitation occurs when an adversary leverages a programming flaw to execute code in a manner that minimizes visibility or blends in with legitimate activity. Rather than directly disabling defenses, adversaries may use exploitation to circumvent monitoring and logging mechanisms.

**Known users/tools:** APT28, Velvet Ant

## Mitigations
- **Threat Intelligence Program** — A Threat Intelligence Program enables organizations to proactively identify, analyze, and act on cyber threats by leveraging internal and external data sources. The program supports decision-making processes, prioritizes defenses, and improves incident response by delivering actionable intelligence 
- **Application Isolation and Sandboxing** — Application Isolation and Sandboxing refers to the technique of restricting the execution of code to a controlled and isolated environment (e.g., a virtual environment, container, or sandbox). This method prevents potentially malicious code from affecting the rest of the system or network by limitin
- **Exploit Protection** — Deploy capabilities that detect, block, and mitigate conditions indicative of software exploits. These capabilities aim to prevent exploitation by addressing vulnerabilities, monitoring anomalous behaviors, and applying exploit-mitigation techniques to harden systems and software.
- **Update Software** — Software updates ensure systems are protected against known vulnerabilities by applying patches and upgrades provided by vendors. Regular updates reduce the attack surface and prevent adversaries from exploiting known security gaps. This includes patching operating systems, applications, drivers, an

## References
- https://attack.mitre.org/techniques/T1211/
