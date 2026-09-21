# T1409: Stored Application Data

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may try to access and collect application data resident on the device. Adversaries often target popular applications, such as Facebook, WeChat, and Gmail.(Citation: SWB Exodus March 2019)
Due to mobile OS sandboxing, this technique is only possible in three scenarios:
* An application stores files in unprotected external storage
* An application stores files in its internal storage directory with insecure permissions (e.g. 777)
* The adversary gains root permissions on the device

## Tactics
Collection

## Platforms
Android, iOS

## Procedure
Adversaries may try to access and collect application data resident on the device. Adversaries often target popular applications, such as Facebook, WeChat, and Gmail.(Citation: SWB Exodus March 2019)
Due to mobile OS sandboxing, this technique is only possible in three scenarios:
* An application stores files in unprotected external storage
* An application stores files in its internal storage directory with insecure permissions (e.g. 777)
* The adversary gains root permissions on the device

**Known users/tools:** BOULDSPY, BusyGasper, CarbonSteal, DCHSpy, Desert Scorpion, DoubleAgent, Escobar, Exodus, FakeSpy, FlexiSpy, FlixOnline, FluBot, FlyTrap, FrozenCell, GoldenEagle

## Mitigations
- **Use Recent OS Version** — New mobile operating system versions bring not only patches against discovered vulnerabilities but also often bring security architecture improvements that provide resilience against potential vulnerabilities or weaknesses that have not yet been discovered. They may also bring improvements that bloc

## References
- https://attack.mitre.org/techniques/T1409/
