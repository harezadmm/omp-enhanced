# T1509: Non-Standard Port

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may generate network traffic using a protocol and port pairing that are typically not associated. For example, HTTPS over port 8088 or port 587 as opposed to the traditional port 443. Adversaries may make changes to the standard port used by a protocol to bypass filtering or muddle analysis/parsing of network data.

## Tactics
Command And Control

## Platforms
Android, iOS

## Procedure
Adversaries may generate network traffic using a protocol and port pairing that are typically not associated. For example, HTTPS over port 8088 or port 587 as opposed to the traditional port 443. Adversaries may make changes to the standard port used by a protocol to bypass filtering or muddle analysis/parsing of network data.

**Known users/tools:** Cerberus, Chameleon, Exodus, FlexiSpy, INSOMNIA, LightSpy, Mandrake, Red Alert 2.0

## References
- https://attack.mitre.org/techniques/T1509/
