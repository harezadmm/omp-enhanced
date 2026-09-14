# T1635: Steal Application Access Token

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries can steal user application access tokens as a means of acquiring credentials to access remote systems and resources. This can occur through social engineering or URI hijacking and typically requires user action to grant access, such as through a system “Open With” dialogue.
Application access tokens are used to make authorized API requests on behalf of a user and are commonly used as a way to access resources in cloud-based applications and software-as-a-service (SaaS).(Citation: Auth0 - Why You Should Always Use Access Tokens to Secure APIs Sept 2019) OAuth is one commonly implemented framework used to issue tokens to users for access to systems. An application desiring access to cloud-based services or protected APIs can gain entry through OAuth 2.0 using a variety of authorization protocols. An example of a commonly-used sequence is Microsoft's Authorization Code Grant flow.(Citation: Microsoft Identity Platform Protocols May 2019)(Citation: Microsoft - OAuth Code Authorization flow - June 2019) An OAuth access token enables a third-party application to interact with resources containing user data in the ways requested without requiring user credentials.

## Tactics
Credential Access

## Platforms
Android, iOS

## Procedure
Adversaries can steal user application access tokens as a means of acquiring credentials to access remote systems and resources. This can occur through social engineering or URI hijacking and typically requires user action to grant access, such as through a system “Open With” dialogue. Application access tokens are used to make authorized API requests on behalf of a user and are commonly used as a way to access resources in cloud-based applications and software-as-a-service (SaaS).(Citation: Auth0 - Why You Should Always Use Access Tokens to Secure APIs Sept 2019) OAuth is one commonly implemented framework used to issue tokens to users for access to systems. An application desiring access to cloud-based services or protected APIs can gain entry through OAuth 2.0 using a variety of authorization protocols.

## Mitigations
- **Use Recent OS Version** — New mobile operating system versions bring not only patches against discovered vulnerabilities but also often bring security architecture improvements that provide resilience against potential vulnerabilities or weaknesses that have not yet been discovered. They may also bring improvements that bloc
- **Application Developer Guidance** — Application Developer Guidance focuses on providing developers with the knowledge, tools, and best practices needed to write secure code, reduce vulnerabilities, and implement secure design principles. By integrating security throughout the software development lifecycle (SDLC), this mitigation aims
- **User Guidance** — Describes any guidance or training given to users to set particular configuration settings or avoid specific potentially risky behaviors.

## References
- https://attack.mitre.org/techniques/T1635/
