#!/usr/bin/env python3
import http.server
import socketserver
import os

PORT = 8080
DIRECTORY = "/root"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def log_message(self, format, *args):
        print(f"[SERVER] {self.address_string()} - {format%args}")

print("="*70)
print("  🔥 VIRUS WEBSITE SERVER 🔥")
print("="*70)
print(f"Server berjalan di: http://localhost:{PORT}")
print(f"Buka file: http://localhost:{PORT}/virus_website.html")
print("="*70)
print("\n[*] Server aktif. Tekan Ctrl+C untuk stop.\n")

with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n[*] Server dihentikan.")
