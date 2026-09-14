# T1474: Supply Chain Compromise

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may manipulate products or product delivery mechanisms prior to receipt by a final consumer for the purpose of data or system compromise.
Supply chain compromise can take place at any stage of the supply chain including:
* Manipulation of development tools
* Manipulation of a development environment
* Manipulation of source code repositories (public or private)
* Manipulation of source code in open-source dependencies
* Manipulation of software update/distribution mechanisms
* Compromised/infected system images
* Replacement of legitimate software with modified versions
* Sales of modified/counterfeit products to legitimate distributors
* Shipment interdiction
While supply chain compromise can impact any component of hardware or software, attackers looking to gain execution have often focused on malicious additions to legitimate software in software distribution or update channels. Targeting may be specific to a desired victim set or malicious software may be distributed to a broad set of consumers but only move on to additional tactics on specific victims.  Popular open source projects that are used as dependencies in many applications may also be targeted as a means to add malicious code to users of the dependency, specifically with the widespread usage of third-party advertising libraries.(Citation: Grace-Advertisement)(Citation: NowSecure-RemoteCode)

## Tactics
Initial Access

## Platforms
Android, iOS

## Procedure
Adversaries may manipulate products or product delivery mechanisms prior to receipt by a final consumer for the purpose of data or system compromise. Supply chain compromise can take place at any stage of the supply chain including:
* Manipulation of development tools
* Manipulation of a development environment
* Manipulation of source code repositories (public or private)
* Manipulation of source code in open-source dependencies
* Manipulation of software update/distribution mechanisms
* Compromised/infected system images
* Replacement of legitimate software with modified versions
* Sales of modified/counterfeit products to legitimate distributors
* Shipment interdiction
While supply chain compromise can impact any component of hardware or software, attackers looking to gain execution have often focused on malicious additions to legitimate software in software distribution or update channels. Targeting may be specific to a desired victim set or malicious software may be distributed to a broad set of consumers but only move on to additional tactics on specific victims. Popular open source projects that are used as dependencies in many applications may also be targeted as a means to add malicious code to users of the dependency, specifically with the widespread usage of third-party advertising libraries.(Citation: Grace-Advertisement)(Citation: NowSecure-RemoteCode)

## Mitigations
- **Application Developer Guidance** — Application Developer Guidance focuses on providing developers with the knowledge, tools, and best practices needed to write secure code, reduce vulnerabilities, and implement secure design principles. By integrating security throughout the software development lifecycle (SDLC), this mitigation aims
- **Security Updates** — Install security updates in response to discovered vulnerabilities.

## References
- https://attack.mitre.org/techniques/T1474/
