# WhatsApp Nokos Auto Farmer

Script otomatis untuk farming nomor WhatsApp (nokos) menggunakan layanan SMS gratis.

## 🚀 Cara Pakai

### Install Dependencies
```bash
pip3 install requests
```

### Jalankan Script
```bash
cd /root/workspace/6810323867
python3 whatsapp_nokos_farmer.py
```

## ⚙️ Konfigurasi

Edit di bagian bawah file `whatsapp_nokos_farmer.py`:

```python
TARGET_ACCOUNTS = 5   # Jumlah akun yang mau dibuat
DELAY_SECONDS = 30    # Jeda antar attempt (detik)
```

## 📊 Fitur

- ✅ Auto dapat nomor gratis dari multiple provider
- ✅ Auto request kode verifikasi WhatsApp
- ✅ Auto tunggu dan ambil kode OTP
- ✅ Auto register akun WhatsApp
- ✅ Real-time statistics (success rate, timing, dll)
- ✅ Save semua akun berhasil ke JSON
- ✅ Anti rate-limit dengan delay otomatis
- ✅ Retry multiple providers kalau satu gagal

## 🌐 SMS Providers

Script ini support beberapa provider SMS gratis:

1. **receive-smss.com** - Gratis total, tapi limited
2. **freeonlinephone.org** - Public numbers
3. **sms-activate.ru** - Perlu API key (ada free trial)

### Tambah API Key SMS-Activate (Opsional)

Kalau punya API key dari sms-activate.ru, edit baris ini:

```python
self.providers: List[SMSProvider] = [
    ReceiveSMSFree(),
    FreeOnlinePhone(),
    SMSActivateRU(api_key="PASTE_API_KEY_DISINI")  # Uncomment baris ini
]
```

## 📁 Output

Semua akun yang berhasil disimpan di:
```
/root/workspace/6810323867/whatsapp_accounts.json
```

Format:
```json
[
  {
    "phone": "12016327663",
    "registered_at": "2026-09-02T15:21:58.342Z",
    "data": {
      "id": "12016327663",
      "number": "12016327663",
      "provider": "freeonlinephone"
    }
  }
]
```

## ⚠️ Catatan Penting

- Provider gratis sering rate-limit keras, jadi success rate bisa rendah
- Delay 30-60 detik antar attempt disarankan
- WhatsApp bisa ban IP kalau terlalu aggressive
- Nomor public kadang sudah dipakai orang lain
- Untuk production farming, pakai provider berbayar (SMS-Activate, 5SIM, dll)

## 🔧 Troubleshooting

**"No providers available"**
→ Semua provider lagi offline/rate-limited, tunggu beberapa menit

**"Timeout waiting for code"**
→ SMS belum masuk atau nomor invalid, coba lagi

**"Verification failed"**
→ Kode salah atau sudah expired, coba nomor baru

**Rate limiting dari WhatsApp**
→ Tambah DELAY_SECONDS, atau pakai proxy/VPN

## 🎯 Tips Maksimalkan Success Rate

1. Pakai API key berbayar (SMS-Activate ~$0.05/nomor)
2. Tambah delay 60-120 detik antar attempt
3. Pakai rotating proxy untuk bypass IP limit
4. Jalankan di VPS/cloud biar 24/7
5. Monitor `whatsapp_accounts.json` untuk track progress
