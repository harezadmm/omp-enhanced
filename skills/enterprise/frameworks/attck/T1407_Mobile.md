# T1407: Download New Code at Runtime

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may download and execute dynamic code not included in the original application package after installation. This technique is primarily used to evade static analysis checks and pre-publication scans in official app stores. In some cases, more advanced dynamic or behavioral analysis techniques could detect this behavior. However, in conjunction with [Execution Guardrails](https://attack.mitre.org/techniques/T1627) techniques, detecting malicious code downloaded after installation could be difficult.
On Android, dynamic code could include native code, Dalvik code, or JavaScript code that utilizes Android WebView’s `JavascriptInterface` capability.
On iOS, dynamic code could be downloaded and executed through 3rd party libraries such as JSPatch. (Citation: FireEye-JSPatch)

## Tactics
Defense Evasion

## Platforms
Android, iOS

## Procedure
Adversaries may download and execute dynamic code not included in the original application package after installation. This technique is primarily used to evade static analysis checks and pre-publication scans in official app stores. In some cases, more advanced dynamic or behavioral analysis techniques could detect this behavior. However, in conjunction with [Execution Guardrails](https://attack.mitre.org/techniques/T1627) techniques, detecting malicious code downloaded after installation could be difficult.

**Known users/tools:** AbstractEmu, Anubis, BOULDSPY, BRATA, BrainTest, Bread, BusyGasper, CHEMISTGAMES, CarbonSteal, Cerberus, Chameleon, Crocodilus, Desert Scorpion, DoubleAgent, Dvmap

## Mitigations
- **Use Recent OS Version** — New mobile operating system versions bring not only patches against discovered vulnerabilities but also often bring security architecture improvements that provide resilience against potential vulnerabilities or weaknesses that have not yet been discovered. They may also bring improvements that bloc

## References
- https://attack.mitre.org/techniques/T1407/
