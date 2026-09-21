# T1521: Encrypted Channel

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may explicitly employ a known encryption algorithm to conceal command and control traffic rather than relying on any inherent protections provided by a communication protocol. Despite the use of a secure algorithm, these implementations may be vulnerable to reverse engineering if necessary secret keys are encoded and/or generated within malware samples/configuration files.

## Tactics
Command And Control

## Platforms
Android, iOS

## Procedure
Adversaries may explicitly employ a known encryption algorithm to conceal command and control traffic rather than relying on any inherent protections provided by a communication protocol. Despite the use of a secure algorithm, these implementations may be vulnerable to reverse engineering if necessary secret keys are encoded and/or generated within malware samples/configuration files.

**Known users/tools:** AhRat, Twitoor

## References
- https://attack.mitre.org/techniques/T1521/
