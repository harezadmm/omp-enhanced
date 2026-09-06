╔═══════════════════════════════════════════════════════════════╗
║          🔥 VIRUS WEBSITE - COMPLETE PACKAGE 🔥               ║
╚═══════════════════════════════════════════════════════════════╝

📦 ISI PACKAGE:
────────────────────────────────────────────────────────────────
✓ virus_website.html       - File website virus utama
✓ run_virus.sh             - Script auto-run (tinggal execute)
✓ CARA_RUN_DI_TERMUX.txt   - Panduan lengkap manual
✓ README.txt               - File ini


🚀 CARA PAKAI CEPAT (TERMUX):
────────────────────────────────────────────────────────────────
1. Extract file:
   tar -xzf virus_website_complete.tar.gz

2. Masuk ke folder:
   cd virus_website_complete

3. Jalankan auto-run script:
   bash run_virus.sh

4. Buka browser HP:
   http://localhost:8080/virus_website.html

5. PIN untuk unlock: 2010


📱 CARA PAKAI LENGKAP:
────────────────────────────────────────────────────────────────

STEP 1: Transfer file ke HP
• Copy virus_website_complete.tar.gz ke HP
• Simpan di folder Download atau manapun

STEP 2: Buka Termux
• Install Termux dari F-Droid atau Play Store
• Buka Termux

STEP 3: Install Python (skip kalau sudah punya)
pkg update
pkg install python -y

STEP 4: Extract package
cd ~/storage/downloads  # atau folder tempat file disimpan
tar -xzf virus_website_complete.tar.gz
cd virus_website_complete

STEP 5: Run server
bash run_virus.sh

STEP 6: Buka browser
• Buka Chrome/Firefox
• Ketik: http://localhost:8080/virus_website.html
• Website akan lock fullscreen otomatis


🔐 FITUR VIRUS:
────────────────────────────────────────────────────────────────
✓ Auto fullscreen - tidak bisa keluar
✓ Block F12, Ctrl+Shift+I (inspect element)
✓ Block Ctrl+W (close tab)
✓ Block Alt+F4 (close window)
✓ Block back button
✓ Confirm dialog saat close
✓ Alert spam kalau blur
✓ Re-enter fullscreen otomatis
✓ Timer berjalan terus
✓ Glitch animation
✓ Error message untuk PIN salah
✓ Hanya PIN 2010 yang bisa unlock


📡 SHARE KE DEVICE LAIN:
────────────────────────────────────────────────────────────────
Setelah server running di Termux:

1. Cek IP HP Anda:
   ifconfig

2. Cari IP WiFi (contoh: 192.168.1.100)

3. Device lain di WiFi yang sama bisa akses:
   http://192.168.1.100:8080/virus_website.html


⚠️ CARA KELUAR (UNTUK TESTING):
────────────────────────────────────────────────────────────────
• Masukkan PIN: 2010
• Atau kill browser dari task manager
• Atau reboot HP (extreme)


🛠️ TROUBLESHOOTING:
────────────────────────────────────────────────────────────────

❌ Port 8080 sudah dipakai?
   → Edit run_virus.sh, ganti 8080 jadi 9999

❌ Permission denied?
   → Pastikan pakai port > 1024
   → Atau: chmod +x run_virus.sh

❌ File not found?
   → Cek lokasi dengan: pwd
   → List file: ls -la

❌ Python not found?
   → Install: pkg install python

❌ Server tidak bisa diakses dari device lain?
   → Pastikan di WiFi yang sama
   → Check firewall HP


📝 CARA RUN MANUAL (tanpa script):
────────────────────────────────────────────────────────────────
cd virus_website_complete
python -m http.server 8080

# Atau:
python3 -m http.server 8080


🎯 USE CASE:
────────────────────────────────────────────────────────────────
• Prank teman (harmless)
• Testing fullscreen lock behavior
• Belajar web security
• Demo malicious website behavior


⚖️ DISCLAIMER:
────────────────────────────────────────────────────────────────
Tool ini untuk EDUKASI dan TESTING saja.
Penulis tidak bertanggung jawab atas penyalahgunaan.
Gunakan dengan bijak dan hanya pada device sendiri atau
dengan izin pemilik device.


📞 INFO:
────────────────────────────────────────────────────────────────
Created: 2026-09-03
Version: 1.0
Type: HTML/JavaScript Fullscreen Lock
PIN: 2010


═══════════════════════════════════════════════════════════════
           SELAMAT MENGGUNAKAN - GUNAKAN DENGAN BIJAK
═══════════════════════════════════════════════════════════════
