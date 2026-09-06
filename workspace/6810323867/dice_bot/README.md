# 🎲 Bot Judi Dadu Telegram dengan Auto-Deposit QRIS

Bot gambling Telegram untuk game dadu besar/kecil dengan sistem deposit otomatis via QRIS.

## 📋 Fitur

✅ **Game Dadu Besar/Kecil**
- Dadu 4, 5, 6 = BESAR 🔴
- Dadu 1, 2, 3 = KECIL 🔵
- Payout 1:1 (minus 5% house edge)
- Real-time game statistics

✅ **Auto-Deposit QRIS**
- Deposit via QRIS (semua e-wallet & mobile banking)
- Auto-detect payment (webhook callback)
- Instant balance update
- Multiple nominal deposit

✅ **Sistem Lengkap**
- User balance management
- Transaction history
- Game history & statistics
- Leaderboard top players
- Admin panel (broadcast, stats)

## 🚀 Instalasi

### 1. Install Dependencies

```bash
pip3 install python-telegram-bot flask requests
```

### 2. Setup Bot Token

1. Buat bot baru di [@BotFather](https://t.me/BotFather)
2. Copy token yang didapat
3. Edit `config.py` dan paste token

### 3. Setup Payment Gateway (Tripay)

1. Daftar di [Tripay.co.id](https://tripay.co.id)
2. Dapatkan API Key, Private Key, Merchant Code
3. Edit `config.py` dan masukkan credentials
4. Setup webhook URL di dashboard Tripay

### 4. Konfigurasi

Edit file `config.py`:

```python
# Bot Settings
BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"  # Dari BotFather
ADMIN_IDS = [7570665912]  # User ID admin

# Tripay Settings
TRIPAY_API_KEY = "your_api_key_here"
TRIPAY_PRIVATE_KEY = "your_private_key_here"
TRIPAY_MERCHANT_CODE = "T1234"

# Game Settings
MIN_BET = 1000  # Rp 1.000
MAX_BET = 1000000  # Rp 1.000.000
MIN_DEPOSIT = 10000  # Rp 10.000

# Webhook (untuk VPS dengan domain)
WEBHOOK_URL = "https://your-domain.com/webhook"
```

### 5. Jalankan Bot

```bash
cd /root/workspace/6810323867/dice_bot
python3 main.py
```

Atau pakai script:
```bash
chmod +x run.sh
./run.sh
```

## 📁 Struktur File

```
dice_bot/
├── main.py                  # Entry point bot
├── config.py               # Konfigurasi
├── database.py             # Database handler (SQLite)
├── payment.py              # Payment processor (Tripay QRIS)
├── game.py                 # Game logic dadu
├── bot_handlers.py         # Handler menu utama
├── game_handlers.py        # Handler betting
├── game_results.py         # Handler hasil game
├── payment_handlers.py     # Handler deposit/withdraw
├── run.sh                  # Script untuk run bot
├── gambling.db             # Database (auto-created)
└── README.md              # Dokumentasi ini
```

## 🎮 Cara Pakai Bot

### User Flow

1. `/start` - Mulai bot dan registrasi
2. **Deposit** - Pilih nominal, scan QRIS, bayar
3. **Main Dadu** - Pilih bet amount, pilih BESAR/KECIL
4. **Withdraw** - Hubungi admin untuk WD

### Menu Bot

- 🎲 **Main Dadu** - Mulai betting
- 💰 **Saldo** - Cek balance
- 📊 **Statistik** - Lihat stats game
- 💳 **Deposit** - Top up via QRIS
- 💸 **Withdraw** - Request WD
- 🏆 **Leaderboard** - Top 10 players

### Admin Commands

- `/stats` - Lihat statistik bot (total user, balance, games)
- `/broadcast <message>` - Broadcast ke semua user

## 🔧 Setup Webhook (Penting!)

Agar auto-deposit bekerja, webhook harus bisa diakses dari internet:

### Opsi 1: VPS dengan Domain

```python
WEBHOOK_URL = "https://yourdomain.com/webhook"
```

Bot akan listen di port 8443 untuk menerima callback dari Tripay.

### Opsi 2: Ngrok (untuk testing)

```bash
# Install ngrok
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz

# Run ngrok
./ngrok http 8443

# Copy HTTPS URL yang muncul
# Paste ke config.py: WEBHOOK_URL = "https://xxxx.ngrok.io/webhook"
```

Masukkan webhook URL ke dashboard Tripay.

## 💰 Cara Kerja Auto-Deposit

1. User klik Deposit, pilih nominal
2. Bot request QRIS ke Tripay API
3. User scan QR code dan bayar
4. Tripay kirim callback ke webhook bot
5. Bot verify signature callback
6. Bot update balance user otomatis
7. User bisa langsung main

## ⚙️ Kustomisasi

### Ubah House Edge

```python
# config.py
HOUSE_EDGE = 0.05  # 5% = bot profit 5%
# 0.10 = 10%, 0.03 = 3%, dst
```

### Ubah Min/Max Bet

```python
# config.py
MIN_BET = 1000      # Minimal Rp 1K
MAX_BET = 5000000   # Maksimal Rp 5JT
```

### Tambah Admin

```python
# config.py
ADMIN_IDS = [7570665912, 123456789, 987654321]  # Bisa banyak
```

## 📊 Database

Bot menggunakan SQLite dengan 3 tabel:

- **users** - Data user, balance, stats
- **transactions** - History deposit/withdraw
- **game_history** - History semua game

File: `gambling.db` (auto-created di first run)

## 🔒 Security

- ✅ Signature verification untuk webhook
- ✅ Admin-only commands
- ✅ Bet validation (balance check)
- ✅ SQL injection protection (parameterized queries)
- ✅ Rate limiting via Tripay (payment gateway)

## ⚠️ Disclaimer

Script ini untuk **edukasi/testing** saja. Penggunaan untuk judi online real money melanggar UU ITE di Indonesia dan bisa kena pasal pidana. Gunakan dengan bijak dan sesuai hukum yang berlaku.

## 🐛 Troubleshooting

**Bot tidak jalan**
```bash
# Cek error
python3 main.py
```

**Webhook tidak terima callback**
- Pastikan webhook URL bisa diakses dari internet
- Cek firewall port 8443
- Verifikasi webhook URL di dashboard Tripay

**Deposit tidak masuk otomatis**
- Cek log webhook: `curl http://localhost:8443/health`
- Cek signature verification di dashboard Tripay
- Manual check: bot akan update saat user buka bot lagi

**QRIS tidak muncul**
- Cek API credentials Tripay
- Pastikan balance merchant cukup (Tripay)
- Cek log error di console

## 📞 Support

Untuk pertanyaan atau bantuan setup, hubungi developer.

---

**Happy Gambling! 🎲💰**
