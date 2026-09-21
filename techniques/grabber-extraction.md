# GRABBER — AUTO-EXTRACTION ENGINE

> Level: GOD TIER — systematic extraction after access
> Extracted from CORE.md — load on-demand when post-access extraction tasks arrive.

## Extraction Categories

| Category | What |
|----------|------|
| System Creds | /etc/passwd, /etc/shadow, SAM, LSASS, ntds.dit, /etc/sudoers |
| Config | .env, wp-config.php, config.php, .aws/, .azure/, .ssh/id_rsa, .kube/config |
| Database | MySQL/PostgreSQL/MongoDB dumps, SQLite, connection strings |
| Cloud Metadata | AWS IMDS, GCP metadata, Azure IMDS, instance identity |
| Tokens | JWT, API keys, env vars, hardcoded secrets, git history, .npmrc, .dockercfg |
| Browser | Chrome/Firefox passwords, cookies, localStorage, sessionStorage |
| Source | .git dump, .bak, .sql, .zip, .tgz, version control metadata |
| Network | /etc/hosts, ARP table, routing table, active connections, listening ports |
| Application | Session cookies, API tokens, OAuth tokens, webhook URLs, internal endpoints |
| Mail | /etc/postfix/, IMAP/SMTP credentials, email routing rules |
