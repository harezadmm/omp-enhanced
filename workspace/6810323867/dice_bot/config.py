# Configuration file untuk Dice Gambling Bot

# Bot Settings
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Dari @BotFather
ADMIN_IDS = [7570665912]  # User ID admin, bisa tambah lebih dari 1

# Payment Gateway Settings (Pilih salah satu)
# Gunakan Tripay (https://tripay.co.id)
PAYMENT_PROVIDER = "tripay"  # atau "xendit" atau "midtrans"
TRIPAY_API_KEY = "YOUR_TRIPAY_API_KEY"
TRIPAY_PRIVATE_KEY = "YOUR_TRIPAY_PRIVATE_KEY"
TRIPAY_MERCHANT_CODE = "YOUR_MERCHANT_CODE"

# Game Settings
MIN_BET = 1000  # Minimal bet Rp 1.000
MAX_BET = 1000000  # Maksimal bet Rp 1.000.000
MIN_DEPOSIT = 10000  # Minimal deposit Rp 10.000
HOUSE_EDGE = 0.05  # 5% house edge (profit bot)

# Database
DATABASE_PATH = "/root/workspace/6810323867/dice_bot/gambling.db"

# Webhook (untuk auto-detect payment)
WEBHOOK_URL = "https://your-domain.com/webhook"  # Ganti dengan domain VPS kamu
WEBHOOK_PORT = 8443
