# T1516: Input Injection

**Matrix:** Mobile | **Type:** Technique

## Description
A malicious application can inject input to the user interface to mimic user interaction through the abuse of Android's accessibility APIs.
[Input Injection](https://attack.mitre.org/techniques/T1516) can be achieved using any of the following methods:
* Mimicking user clicks on the screen, for example to steal money from a user's PayPal account.(Citation: android-trojan-steals-paypal-2fa)
* Injecting global actions, such as `GLOBAL_ACTION_BACK` (programatically mimicking a physical back button press), to trigger actions on behalf of the user.(Citation: Talos Gustuff Apr 2019)
* Inserting input into text fields on behalf of the user. This method is used legitimately to auto-fill text fields by applications such as password managers.(Citation: bitwarden autofill logins)

## Tactics
Defense Evasion, Impact

## Platforms
Android

## Procedure
A malicious application can inject input to the user interface to mimic user interaction through the abuse of Android's accessibility APIs. [Input Injection](https://attack.mitre.org/techniques/T1516) can be achieved using any of the following methods:
* Mimicking user clicks on the screen, for example to steal money from a user's PayPal account.(Citation: android-trojan-steals-paypal-2fa)
* Injecting global actions, such as `GLOBAL_ACTION_BACK` (programatically mimicking a physical back button press), to trigger actions on behalf of the user.(Citation: Talos Gustuff Apr 2019)
* Inserting input into text fields on behalf of the user. This method is used legitimately to auto-fill text fields by applications such as password managers.(Citation: bitwarden autofill logins)

**Known users/tools:** BRATA, Cerberus, Crocodilus, DEFENSOR ID, Ginp, GodFather, Gustuff, Mandrake, Riltok, S.O.V.A., SharkBot, TERRACOTTA, TrickMo, Zen

## Mitigations
- **Enterprise Policy** — An enterprise mobility management (EMM), also known as mobile device management (MDM), system can be used to provision policies to mobile devices to control aspects of their allowed behavior.
- **User Guidance** — Describes any guidance or training given to users to set particular configuration settings or avoid specific potentially risky behaviors.

## References
- https://attack.mitre.org/techniques/T1516/
