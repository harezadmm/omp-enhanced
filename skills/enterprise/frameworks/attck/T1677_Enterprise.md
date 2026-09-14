# T1677: Poisoned Pipeline Execution

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may manipulate continuous integration / continuous development (CI/CD) processes by injecting malicious code into the build process. There are several mechanisms for poisoning pipelines:
* In a <b>Direct Pipeline Execution</b> scenario, the threat actor directly modifies the CI configuration file (e.g., `gitlab-ci.yml` in GitLab). They may include a command to exfiltrate credentials leveraged in the build process to a remote server, or to export them as a workflow artifact.(Citation: Unit 42 Palo Alto GitHub Actions Supply Chain Attack 2025)(Citation: OWASP CICD-SEC-4)
* In an <b>Indirect Pipeline Execution</b> scenario, the threat actor injects malicious code into files referenced by the CI configuration file. These may include makefiles, scripts, unit tests, and linters.(Citation: OWASP CICD-SEC-4)
* In a <b>Public Pipeline Execution</b> scenario, the threat actor does not have direct access to the repository but instead creates a malicious pull request from a fork that triggers a part of the CI/CD pipeline. For example, in GitHub Actions, the `pull_request_target` trigger allows workflows running from forked repositories to access secrets.  If this trigger is combined with an explicit pull request checkout and a location for a threat actor to insert malicious code (e.g., an `npm build` command), a threat actor may be able to leak pipeline credentials.(Citation: Unit 42 Palo Alto GitHub Actions Supply Chain Attack 2025)(Citation: GitHub Security Lab GitHub Actions Security 2021) Similarly, threat actors may craft pull requests with malicious inputs (such as branch names) if the build pipeline treats those inputs as trusted.(Citation: Wiz Ultralytics AI Library Hijack 2024)(Citation: Synactiv Hijacking GitHub Runners)(Citation: GitHub Security Labs GitHub Actions Security Part 2 2021) Finally, if a pipeline leverages a self-hosted runner, a threat actor may be able to execute arbitrary code on a host inside the organization’s network.(Citation: John Stawinski PyTorch Supply Chain Attack 2024)
By poisoning CI/CD pipelines, threat actors may be able to gain access to credentials, laterally move to additional hosts, or input malicious components to be shipped further down the pipeline (i.e., [Supply Chain Compromise](https://attack.mitre.org/techniques/T1195)).

## Tactics
Execution

## Platforms
SaaS

## Procedure
Adversaries may manipulate continuous integration / continuous development (CI/CD) processes by injecting malicious code into the build process. There are several mechanisms for poisoning pipelines:
* In a <b>Direct Pipeline Execution</b> scenario, the threat actor directly modifies the CI configuration file (e.g., `gitlab-ci.yml` in GitLab). They may include a command to exfiltrate credentials leveraged in the build process to a remote server, or to export them as a workflow artifact.(Citation: Unit 42 Palo Alto GitHub Actions Supply Chain Attack 2025)(Citation: OWASP CICD-SEC-4)
* In an <b>Indirect Pipeline Execution</b> scenario, the threat actor injects malicious code into files referenced by the CI configuration file. These may include makefiles, scripts, unit tests, and linters.(Citation: OWASP CICD-SEC-4)
* In a <b>Public Pipeline Execution</b> scenario, the threat actor does not have direct access to the repository but instead creates a malicious pull request from a fork that triggers a part of the CI/CD pipeline.

**Known users/tools:** CanisterWorm, Mini Shai-Hulud, Shai-Hulud, TeamPCP

## Mitigations
- **User Account Management** — User Account Management involves implementing and enforcing policies for the lifecycle of user accounts, including creation, modification, and deactivation. Proper account management reduces the attack surface by limiting unauthorized access, managing account privileges, and ensuring accounts are us
- **Software Configuration** — Software configuration refers to making security-focused adjustments to the settings of applications, middleware, databases, or other software to mitigate potential threats. These changes help reduce the attack surface, enforce best practices, and protect sensitive data. This mitigation can be imple

## References
- https://attack.mitre.org/techniques/T1677/
