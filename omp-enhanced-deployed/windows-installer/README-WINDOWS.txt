OMP Enhanced - Windows Installation Guide
==========================================

QUICK START:
1. Double-click install.bat
2. Wait for installation to complete
3. Double-click start.bat to run server

REQUIREMENTS:
- Windows 10/11 (x64)
- PowerShell (built-in)
- Java 8+ (auto-installed if missing)
- 512MB RAM minimum

MANUAL STEPS (if auto-installer fails):

1. Install Java:
   Download from: https://adoptium.net/temurin/releases/
   Choose: Windows x64 JDK 17 MSI installer

2. Download OMP server:
   https://github.com/openmultiplayer/open.mp/releases/latest
   Download: open.mp-win-x86.zip

3. Extract to folder

4. Edit config.json (optional):
   - Change "hostname" to your server name
   - Change "rcon_password" to secure password
   - Change "port" if needed (default 7777)

5. Run: omp-server.exe

CONFIGURATION:
- Server config: config.json
- RCON password: changeme123 (CHANGE THIS!)
- Port: 7777 (configurable)
- Max players: 50 (configurable)

FIREWALL:
Allow inbound UDP port 7777 in Windows Firewall:
1. Control Panel → Windows Defender Firewall
2. Advanced Settings → Inbound Rules → New Rule
3. Port → UDP → 7777 → Allow

PORT FORWARDING (for internet access):
1. Access router admin (usually 192.168.1.1)
2. Find Port Forwarding section
3. Add rule: UDP port 7777 → your PC's local IP

TROUBLESHOOTING:
- "Java not found": Restart installer or install manually
- "Port already in use": Change port in config.json
- Server won't start: Check if port 7777 is open
- Can't connect: Check firewall and port forwarding

CONNECTING:
1. Open GTA San Andreas
2. Open SA-MP client
3. Add server: your_ip:7777
4. Join server

For VPS/dedicated server, use public IP.
For home network, use public IP with port forwarding.

SECURITY:
- Change RCON password in config.json
- Don't share RCON password
- Keep server files in separate folder
- Regular backups of scriptfiles/

SUPPORT:
GitHub: https://github.com/harezadmm/omp-enhanced
Issues: https://github.com/harezadmm/omp-enhanced/issues
