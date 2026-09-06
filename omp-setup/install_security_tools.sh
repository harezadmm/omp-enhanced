#!/bin/bash
# OMP Security Tools Installer
# Installs all necessary pentesting and hacking tools for the security skills

set -e

echo "============================================================"
echo "OMP Security Tools Installer"
echo "Installing tools untuk semua security skills..."
echo "============================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Please run as root (sudo)"
    exit 1
fi

# Update system
echo "📦 Updating system..."
apt-get update -qq

# Network Penetration Testing Tools
echo ""
echo "🔧 Installing Network Pentest Tools..."
apt-get install -y \
    nmap \
    masscan \
    netcat-traditional \
    socat \
    proxychains4 \
    tor \
    enum4linux \
    smbclient \
    smbmap \
    snmp \
    onesixtyone \
    dnsutils \
    ldap-utils \
    nfs-common \
    hydra \
    medusa \
    crackmapexec \
    john \
    hashcat \
    openssh-client \
    ftp \
    telnet \
    responder \
    wireshark \
    tcpdump \
    tshark

# Web Application Hacking Tools
echo ""
echo "🌐 Installing Web Hacking Tools..."
apt-get install -y \
    sqlmap \
    nikto \
    dirb \
    gobuster \
    ffuf \
    wfuzz \
    curl \
    wget \
    python3-requests \
    python3-beautifulsoup4

# Install additional web tools via pip
pip3 install --quiet \
    arjun \
    paramspider \
    sublist3r \
    wappalyzer

# Wireless Hacking Tools
echo ""
echo "📡 Installing Wireless Hacking Tools..."
apt-get install -y \
    aircrack-ng \
    reaver \
    bully \
    wifite \
    macchanger \
    hcxtools \
    hcxdumptool \
    hostapd

# Exploitation Frameworks
echo ""
echo "💣 Installing Exploitation Tools..."

# Metasploit (if not already installed)
if ! command -v msfconsole &> /dev/null; then
    echo "  Installing Metasploit Framework..."
    curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > /tmp/msfinstall
    chmod +x /tmp/msfinstall
    /tmp/msfinstall
fi

# Install exploit development tools
apt-get install -y \
    gdb \
    gdb-multiarch \
    python3-pwntools \
    radare2 \
    rizin \
    gcc \
    g++ \
    gcc-multilib \
    g++-multilib \
    nasm \
    binutils

# ROPgadget and ropper
pip3 install --quiet ropgadget ropper

# RAT/Malware Development Tools
echo ""
echo "🦠 Installing Malware Development Tools..."
apt-get install -y \
    mingw-w64 \
    wine \
    wine64 \
    upx-ucl \
    build-essential \
    cmake

# Phishing Tools
echo ""
echo "🎣 Installing Phishing Tools..."
pip3 install --quiet \
    flask \
    beautifulsoup4 \
    requests \
    dnspython

# Social Engineering Toolkit (optional)
if [ ! -d "/opt/setoolkit" ]; then
    echo "  Installing Social Engineering Toolkit..."
    git clone https://github.com/trustedsec/social-engineer-toolkit /opt/setoolkit
    cd /opt/setoolkit
    pip3 install -r requirements.txt
    cd -
fi

# Botnet C2 Tools
echo ""
echo "🤖 Installing Botnet C2 Tools..."
pip3 install --quiet \
    flask \
    sqlite3 \
    pycryptodome

# Additional Python libraries
echo ""
echo "🐍 Installing Python Libraries..."
pip3 install --quiet \
    impacket \
    scapy \
    pyshark \
    paramiko \
    pycrypto \
    pycryptodome \
    netifaces \
    python-nmap \
    pymetasploit3

# Post-Exploitation Tools
echo ""
echo "🔓 Installing Post-Exploitation Tools..."
apt-get install -y \
    mimikatz \
    bloodhound \
    neo4j

# Install Nuclei (modern scanner)
echo ""
echo "⚡ Installing Nuclei..."
if ! command -v nuclei &> /dev/null; then
    GO111MODULE=on go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest
    
    # Install nuclei templates
    nuclei -update-templates
fi

# Install additional recon tools
echo ""
echo "🔍 Installing Recon Tools..."
if ! command -v subfinder &> /dev/null; then
    GO111MODULE=on go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
fi

if ! command -v httpx &> /dev/null; then
    GO111MODULE=on go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
fi

# Configure tools
echo ""
echo "⚙️  Configuring tools..."

# Setup proxychains for Tor
if [ -f /etc/proxychains4.conf ]; then
    sed -i 's/^strict_chain/#strict_chain/' /etc/proxychains4.conf
    sed -i 's/^#dynamic_chain/dynamic_chain/' /etc/proxychains4.conf
fi

# Summary
echo ""
echo "============================================================"
echo "✓ Installation Complete!"
echo "============================================================"
echo ""
echo "Installed tool categories:"
echo "  ✓ Network Penetration Testing"
echo "  ✓ Web Application Hacking"
echo "  ✓ Wireless Network Hacking"
echo "  ✓ Exploitation Frameworks"
echo "  ✓ Malware Development"
echo "  ✓ Phishing Tools"
echo "  ✓ Botnet C2 Infrastructure"
echo "  ✓ Post-Exploitation"
echo ""
echo "Semua tools sudah siap!"
echo "Skills di ~/.hermes/profiles/umi2/skills/security/ sekarang fully supported."
echo ""
echo "CATATAN: Beberapa tools memerlukan konfigurasi tambahan:"
echo "  - Metasploit: msfconsole (first run to initialize)"
echo "  - Tor: service tor start"
echo "  - Neo4j (for BloodHound): neo4j start"
echo ""
echo "============================================================"
