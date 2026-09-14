# T1489: Service Stop

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may stop or disable services on a system to render those services unavailable to legitimate users. Stopping critical services or processes can inhibit or stop response to an incident or aid in the adversary's overall objectives to cause damage to the environment.(Citation: Talos Olympic Destroyer 2018)(Citation: Novetta Blockbuster)
Adversaries may accomplish this by disabling individual services of high importance to an organization, such as <code>MSExchangeIS</code>, which will make Exchange content inaccessible.(Citation: Novetta Blockbuster) In some cases, adversaries may stop or disable many or all services to render systems unusable.(Citation: Talos Olympic Destroyer 2018) Services or processes may not allow for modification of their data stores while running. Adversaries may stop services or processes in order to conduct [Data Destruction](https://attack.mitre.org/techniques/T1485) or [Data Encrypted for Impact](https://attack.mitre.org/techniques/T1486) on the data stores of services like Exchange and SQL Server, or on virtual machines hosted on ESXi infrastructure.(Citation: SecureWorks WannaCry Analysis)(Citation: Crowdstrike Hypervisor Jackpotting Pt 2 2021)
Threat actors may also disable or stop service in cloud environments. For example, by leveraging the `DisableAPIServiceAccess` API in AWS, a threat actor may prevent the service from creating service-linked roles on new accounts in the AWS Organization.(Citation: Datadog Security Labs Cloud Persistence 2025)(Citation: AWS DisableAWSServiceAccess)

## Tactics
Impact

## Platforms
ESXi, IaaS, Linux, macOS, Windows

## Procedure
Adversaries may stop or disable services on a system to render those services unavailable to legitimate users. Stopping critical services or processes can inhibit or stop response to an incident or aid in the adversary's overall objectives to cause damage to the environment.(Citation: Talos Olympic Destroyer 2018)(Citation: Novetta Blockbuster)
Adversaries may accomplish this by disabling individual services of high importance to an organization, such as <code>MSExchangeIS</code>, which will make Exchange content inaccessible.(Citation: Novetta Blockbuster) In some cases, adversaries may stop or disable many or all services to render systems unusable.(Citation: Talos Olympic Destroyer 2018) Services or processes may not allow for modification of their data stores while running. Adversaries may stop services or processes in order to conduct [Data Destruction](https://attack.mitre.org/techniques/T1485) or [Data Encrypted for Impact](https://attack.mitre.org/techniques/T1486) on the data stores of services like Exchange and SQL Server, or on virtual machines hosted on ESXi infrastructure.(Citation: SecureWorks WannaCry Analysis)(Citation: Crowdstrike Hypervisor Jackpotting Pt 2 2021)
Threat actors may also disable or stop service in cloud environments. For example, by leveraging the `DisableAPIServiceAccess` API in AWS, a threat actor may prevent the service from creating service-linked roles on new accounts in the AWS Organization.(Citation: Datadog Security Labs Cloud Persistence 2025)(Citation: AWS DisableAWSServiceAccess)

**Known users/tools:** Akira _v2, Avaddon, AvosLocker, BRICKSTORM, Babuk, BlackByte 2.0 Ransomware, BlackCat, Cheerscrypt, Clop, Conti, Cuba, DRYHOOK, Diavol, EKANS, Embargo

## Mitigations
- **Out-of-Band Communications Channel** — Establish secure out-of-band communication channels to ensure the continuity of critical communications during security incidents, data integrity attacks, or in-network communication failures. Out-of-band communication refers to using an alternative, separate communication path that is not dependent
- **Network Segmentation** — Network segmentation involves dividing a network into smaller, isolated segments to control and limit the flow of traffic between devices, systems, and applications. By segmenting networks, organizations can reduce the attack surface, restrict lateral movement by adversaries, and protect critical as
- **User Account Management** — User Account Management involves implementing and enforcing policies for the lifecycle of user accounts, including creation, modification, and deactivation. Proper account management reduces the attack surface by limiting unauthorized access, managing account privileges, and ensuring accounts are us
- **Restrict File and Directory Permissions** — Restricting file and directory permissions involves setting access controls at the file system level to limit which users, groups, or processes can read, write, or execute files. By configuring permissions appropriately, organizations can reduce the attack surface for adversaries seeking to access s
- **Restrict Registry Permissions** — Restricting registry permissions involves configuring access control settings for sensitive registry keys and hives to ensure that only authorized users or processes can make modifications. By limiting access, organizations can prevent unauthorized changes that adversaries might use for persistence,

## References
- https://attack.mitre.org/techniques/T1489/
