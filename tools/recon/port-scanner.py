#!/usr/bin/env python3
"""Simple TCP port scanner — connect-only, no root needed.
Usage: python3 port-scanner.py target.com [start_port] [end_port] [--top1000]"""
import sys, socket, time
TARGET = sys.argv[1] if len(sys.argv) > 1 else sys.exit("Usage: port-scanner.py target.com [start] [end] [--top1000]")
if "--top1000" in sys.argv:
    PORTS = [1,3,7,9,13,17,19,21,22,23,25,26,37,43,49,53,67,68,69,70,79,80,81,88,110,111,113,119,123,135,137,139,143,161,162,177,179,194,199,201,220,311,389,427,443,445,464,465,497,500,512,513,514,515,520,530,543,544,546,547,548,554,587,593,623,625,631,636,639,646,691,873,902,989,990,993,995,1025,1080,1099,1194,1214,1241,1311,1337,1352,1433,1434,1443,1521,1701,1720,1723,1755,1863,1883,1900,1935,2000,2001,2002,2049,2082,2083,2100,2222,2301,2375,2376,2443,2483,2484,2546,2560,3000,3001,3030,3128,3260,3268,3269,3283,3306,3389,3478,3500,3632,3689,3690,3780,4000,4100,4369,4443,4444,4500,4567,4662,4899,5000,5001,5038,5060,5222,5353,5432,5555,5631,5632,5672,5800,5900,5938,5984,5985,5986,6000,6379,6969,7001,7002,7070,7474,8000,8008,8009,8014,8080,8081,8083,8200,8443,8500,8765,8880,8888,8983,9000,9001,9043,9060,9090,9100,9160,9200,9300,9443,9600,9800,9999,10000,10050,10051,10250,10443,11211,15672,16379,27017,27018,27019,28017,50000,50030,50060,50070,50075,50090,61616]
else:
    s = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    e = int(sys.argv[3]) if len(sys.argv) > 3 else 65535
    PORTS = range(s, e+1)
open_ports = []
for port in PORTS:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM); sock.settimeout(1)
        if sock.connect_ex((TARGET, port)) == 0:
            try: banner = sock.recv(1024).decode(errors="replace").strip().split("\n")[0][:60]
            except: banner = ""
            open_ports.append((port, banner))
            print(f"OPEN {port:6d}  {banner}")
        sock.close()
    except: pass
print(f"\nDone. {len(open_ports)} ports open on {TARGET}")
