# T1684: Social Engineering

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may use social engineering techniques to influence users to take actions that result in unauthorized access, approval of changes, disclosure of sensitive information, or execution of adversary-supplied instructions (i.e., introduction of malicious payloads or software), while minimizing technical indicators.
Adversaries may leverage trust-building methods across multiple channels (e.g., executive, vendor, or help desk scenarios, including AI-enabled voice interactions) to prompt user-authorized actions such as password resets, MFA changes, financial approvals, or the disclosure of sensitive information. Adversaries may also leverage common business communications and workflows such as email, collaboration platforms, voice communications, recruiting processes, help desk interactions, and SaaS consent mechanisms to make malicious requests appear routine and legitimate.(Citation: Proofpoint TA427 April 2024)(Citation: SE SentinelOne 2)(Citation: SE - Hackers Target Workday)
Additionally, adversaries have persuaded victims to take actions through references of current events, harnessing relevant themes to the work role or the organizations mission. For example, adversaries may use scare tactics (i.e., threaten repercussions for non-compliance) or otherwise incite victims’ emotions in order to generate a sense of urgency to take action.(Citation: SE Proofpoint)(Citation: SE SentinelOne)
This technique may include common social engineering patterns such as [Phishing](https://attack.mitre.org/techniques/T1566) and [Spearphishing Voice](https://attack.mitre.org/techniques/T1566/004), often supported by convincing and targeted narratives.(Citation: SE SentinelOne 2)(Citation: Fortinet Trends 25-26)

## Tactics
Stealth

## Platforms
Linux, macOS, Office Suite, SaaS, Windows

## Procedure
Adversaries may use social engineering techniques to influence users to take actions that result in unauthorized access, approval of changes, disclosure of sensitive information, or execution of adversary-supplied instructions (i.e., introduction of malicious payloads or software), while minimizing technical indicators. Adversaries may leverage trust-building methods across multiple channels (e.g., executive, vendor, or help desk scenarios, including AI-enabled voice interactions) to prompt user-authorized actions such as password resets, MFA changes, financial approvals, or the disclosure of sensitive information. Adversaries may also leverage common business communications and workflows such as email, collaboration platforms, voice communications, recruiting processes, help desk interactions, and SaaS consent mechanisms to make malicious requests appear routine and legitimate.(Citation: Proofpoint TA427 April 2024)(Citation: SE SentinelOne 2)(Citation: SE - Hackers Target Workday)
Additionally, adversaries have persuaded victims to take actions through references of current events, harnessing relevant themes to the work role or the organizations mission. For example, adversaries may use scare tactics (i.e., threaten repercussions for non-compliance) or otherwise incite victims’ emotions in order to generate a sense of urgency to take action.(Citation: SE Proofpoint)(Citation: SE SentinelOne)
This technique may include common social engineering patterns such as [Phishing](https://attack.mitre.org/techniques/T1566) and [Spearphishing Voice](https://attack.mitre.org/techniques/T1566/004), often supported by convincing and targeted narratives.(Citation: SE SentinelOne 2)(Citation: Fortinet Trends 25-26)

**Known users/tools:** ShinyHunters

## Mitigations
- **User Training** — User Training involves educating employees and contractors on recognizing, reporting, and preventing cyber threats that rely on human interaction, such as phishing, social engineering, and other manipulative techniques. Comprehensive training programs create a human firewall by empowering users to b
- **Audit** — Auditing is the process of recording activity and systematically reviewing and analyzing the activity and system configurations. The primary purpose of auditing is to detect anomalies and identify potential threats or weaknesses in the environment. Proper auditing configurations can also help to mee
- **Account Use Policies** — Account Use Policies help mitigate unauthorized access by configuring and enforcing rules that govern how and when accounts can be used. These policies include enforcing account lockout mechanisms, restricting login times, and setting inactivity timeouts. Proper configuration of these policies reduc

## References
- https://attack.mitre.org/techniques/T1684/
