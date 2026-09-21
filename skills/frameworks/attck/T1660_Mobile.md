# T1660: Phishing

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may send malicious content to users in order to gain access to their mobile devices. All forms of phishing are electronically delivered social engineering. Adversaries can conduct both non-targeted phishing, such as in mass malware spam campaigns, as well as more targeted phishing tailored for a specific individual, company, or industry, known as “spearphishing.” Phishing often involves social engineering techniques, such as posing as a trusted source, as well as evasion techniques, such as removing or manipulating emails or metadata/headers from compromised accounts being abused to send messages.
Mobile phishing may take various forms. For example, adversaries may send emails containing malicious attachments or links, typically to deliver and then execute malicious code on victim devices. Phishing may also be conducted via third-party services, like social media platforms. Adversaries may also impersonate executives of organizations to persuade victims into performing some action on their behalf. For example, adversaries will often use social engineering techniques in text messages to trick the victims into acting quickly, which leads to adversaries obtaining credentials and other information.
Mobile devices are a particularly attractive target for adversaries executing phishing campaigns.  Due to their smaller form factor than traditional desktop endpoints, users may not be able to notice minor differences between genuine and phishing websites. Further, mobile devices have additional sensors and radios that allow adversaries to execute phishing attempts over several different vectors, such as:
- SMS messages: Adversaries may send SMS messages (known as “smishing”) from compromised devices to potential targets to convince the target to, for example, install malware, navigate to a specific website, or enable certain insecure configurations on their device.
- Quick Response (QR) Codes: Adversaries may use QR codes (known as “quishing”) to redirect users to a phishing website. For example, an adversary could replace a legitimate public QR Code with one that leads to a different destination, such as a phishing website. A malicious QR code could also be delivered via other means, such as SMS or email. In the latter case, an adversary could utilize a malicious QR code in an email to pivot from the user’s desktop computer to their mobile device.
- Phone Calls: Adversaries may call victims (known as "vishing") to persuade them to perform an action, such as providing login credentials or navigating to malicious websites. Common vishing targets include employees, especially executives of organizations, and help desks. This may also be used as a technique to perform the initial access on a mobile device, but then pivot to a desktop computer by having the victims perform actions on a desktop computer. With the rise of artificial intelligence (AI), adversaries may also use AI to clone a person’s voice, resulting in deepfake vishing. The cloned voice provides familiarity to the victims, increasing the likelihood of successful malicious actions performed by the victims. Additionally, adversaries may leave voicemails, which may use a real person’s voice or an AI-generated voice; these scams would urgently ask victims into calling back to perform an action, e.g. sending money or providing sensitive information and credentials.

## Tactics
Initial Access

## Platforms
Android, iOS

## Procedure
Adversaries may send malicious content to users in order to gain access to their mobile devices. All forms of phishing are electronically delivered social engineering. Adversaries can conduct both non-targeted phishing, such as in mass malware spam campaigns, as well as more targeted phishing tailored for a specific individual, company, or industry, known as “spearphishing.” Phishing often involves social engineering techniques, such as posing as a trusted source, as well as evasion techniques, such as removing or manipulating emails or metadata/headers from compromised accounts being abused to send messages. Mobile phishing may take various forms.

**Known users/tools:** APT-C-23, BITTER, BRATA, Chameleon, CherryBlos, DocSwap, FjordPhantom, FluBot, GodFather, Kimsuky, LightSpy, Pegasus for iOS, RatMilad, Sandworm Team, Scattered Spider

## Mitigations
- **User Guidance** — Describes any guidance or training given to users to set particular configuration settings or avoid specific potentially risky behaviors.
- **Antivirus/Antimalware** — Mobile security products, such as Mobile Threat Defense (MTD), offer various device-based mitigations against certain behaviors.

## References
- https://attack.mitre.org/techniques/T1660/
