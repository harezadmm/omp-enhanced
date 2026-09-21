# T1406: Obfuscated Files or Information

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may attempt to make a payload or file difficult to discover or analyze by encrypting, encoding, or otherwise obfuscating its contents on the device or in transit. This is common behavior that can be used across different platforms and the network to evade defenses.
Payloads may be compressed, archived, or encrypted in order to avoid detection. These payloads may be used during Initial Access or later to mitigate detection. Portions of files can also be encoded to hide the plaintext strings that would otherwise help defenders with discovery. Payloads may also be split into separate, seemingly benign files that only reveal malicious functionality when reassembled.(Citation: Microsoft MalLockerB)

## Tactics
Defense Evasion

## Platforms
Android, iOS

## Procedure
Adversaries may attempt to make a payload or file difficult to discover or analyze by encrypting, encoding, or otherwise obfuscating its contents on the device or in transit. This is common behavior that can be used across different platforms and the network to evade defenses. Payloads may be compressed, archived, or encrypted in order to avoid detection. These payloads may be used during Initial Access or later to mitigate detection.

**Known users/tools:** AbstractEmu, AhRat, Android/AdDisplay.Ashas, Android/SpyAgent, AndroidOS/MalLocker.B, Asacub, BRATA, BrainTest, Bread, C0033, CHEMISTGAMES, CarbonSteal, Cerberus, Charger, Crocodilus

## References
- https://attack.mitre.org/techniques/T1406/
