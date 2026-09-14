# T1682: Query Public AI Services

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may query publicly accessible artificial intelligence (AI) services, such as large language models (LLMs), to support targeting and operations. In addition to searching websites or databases directly (i.e., [Search Open Websites/Domains](https://attack.mitre.org/techniques/T1593)), adversaries may use AI services to synthesize, aggregate, and analyze publicly available information at scale. This may include identifying individuals or organizations to target, researching organizational structures and personnel, identifying technologies used by target organizations, researching business relationships to develop plausible pretexts for [Social Engineering](https://attack.mitre.org/techniques/T1684) approaches, identifying contact information for use in [Phishing](https://attack.mitre.org/techniques/T1566) or [Phishing for Information](https://attack.mitre.org/techniques/T1598), or gathering derogatory or sensitive information about individuals that may be used for extortion or coercion.(Citation: MSFT-AI)(Citation: GTIG AI Threat Tracker)
Information gathered through AI services may be leveraged for other behaviors, such as establishing operational resources (i.e., [Generate Content](https://attack.mitre.org/techniques/T1683) or [Establish Accounts](https://attack.mitre.org/techniques/T1585). For obtaining access to AI tools and services, see [Artificial Intelligence](https://attack.mitre.org/techniques/T1588/007).

## Tactics
Reconnaissance

## Platforms
PRE

## Procedure
Adversaries may query publicly accessible artificial intelligence (AI) services, such as large language models (LLMs), to support targeting and operations. In addition to searching websites or databases directly (i.e., [Search Open Websites/Domains](https://attack.mitre.org/techniques/T1593)), adversaries may use AI services to synthesize, aggregate, and analyze publicly available information at scale. This may include identifying individuals or organizations to target, researching organizational structures and personnel, identifying technologies used by target organizations, researching business relationships to develop plausible pretexts for [Social Engineering](https://attack.mitre.org/techniques/T1684) approaches, identifying contact information for use in [Phishing](https://attack.mitre.org/techniques/T1566) or [Phishing for Information](https://attack.mitre.org/techniques/T1598), or gathering derogatory or sensitive information about individuals that may be used for extortion or coercion.(Citation: MSFT-AI)(Citation: GTIG AI Threat Tracker)
Information gathered through AI services may be leveraged for other behaviors, such as establishing operational resources (i.e., [Generate Content](https://attack.mitre.org/techniques/T1683) or [Establish Accounts](https://attack.mitre.org/techniques/T1585). For obtaining access to AI tools and services, see [Artificial Intelligence](https://attack.mitre.org/techniques/T1588/007).

**Known users/tools:** APT42, Kimsuky

## Mitigations
- **Pre-compromise** — Pre-compromise mitigations involve proactive measures and defenses implemented to prevent adversaries from successfully identifying and exploiting weaknesses during the Reconnaissance and Resource Development phases of an attack. These activities focus on reducing an organization's attack surface, i

## References
- https://attack.mitre.org/techniques/T1682/
