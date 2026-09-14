# T1629: Impair Defenses

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may maliciously modify components of a victim environment in order to hinder or disable defensive mechanisms. This not only involves impairing preventative defenses, such as anti-virus, but also detection capabilities that defenders can use to audit activity and identify malicious behavior. This may span both native defenses as well as supplemental capabilities installed by users or mobile endpoint administrators.

## Tactics
Defense Evasion

## Platforms
Android

## Procedure
Adversaries may maliciously modify components of a victim environment in order to hinder or disable defensive mechanisms. This not only involves impairing preventative defenses, such as anti-virus, but also detection capabilities that defenders can use to audit activity and identify malicious behavior. This may span both native defenses as well as supplemental capabilities installed by users or mobile endpoint administrators.

**Known users/tools:** CherryBlos, GodFather

## Mitigations
- **Enterprise Policy** — An enterprise mobility management (EMM), also known as mobile device management (MDM), system can be used to provision policies to mobile devices to control aspects of their allowed behavior.
- **User Guidance** — Describes any guidance or training given to users to set particular configuration settings or avoid specific potentially risky behaviors.
- **System Partition Integrity** — Ensure that Android devices being used include and enable the Verified Boot capability, which cryptographically ensures the integrity of the system partition.
- **Security Updates** — Install security updates in response to discovered vulnerabilities.
- **Deploy Compromised Device Detection Method** — A variety of methods exist that can be used to enable enterprises to identify compromised (e.g. rooted/jailbroken) devices, whether using security mechanisms built directly into the device, third-party mobile security applications, enterprise mobility management (EMM)/mobile device management (MDM) 

## References
- https://attack.mitre.org/techniques/T1629/
