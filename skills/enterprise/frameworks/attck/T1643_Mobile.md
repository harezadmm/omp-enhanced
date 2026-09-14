# T1643: Generate Traffic from Victim

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may generate outbound traffic from devices. This is typically performed to manipulate external outcomes, such as to achieve carrier billing fraud or to manipulate app store rankings or ratings. Outbound traffic is typically generated as SMS messages or general web traffic, but may take other forms as well.
If done via SMS messages, Android apps must hold the `SEND_SMS` permission. Additionally, sending an SMS message requires user consent if the recipient is a premium number. Applications cannot send SMS messages on iOS

## Tactics
Impact

## Platforms
Android, iOS

## Procedure
Adversaries may generate outbound traffic from devices. This is typically performed to manipulate external outcomes, such as to achieve carrier billing fraud or to manipulate app store rankings or ratings. Outbound traffic is typically generated as SMS messages or general web traffic, but may take other forms as well. If done via SMS messages, Android apps must hold the `SEND_SMS` permission.

**Known users/tools:** Agent Smith, Android/AdDisplay.Ashas, BrainTest, Bread, FlixOnline, Gooligan, HummingBad, HummingWhale, Judy, MazarBOT, PJApps, RedDrop, SimBad, TERRACOTTA, Triada

## Mitigations
- **User Guidance** — Describes any guidance or training given to users to set particular configuration settings or avoid specific potentially risky behaviors.

## References
- https://attack.mitre.org/techniques/T1643/
