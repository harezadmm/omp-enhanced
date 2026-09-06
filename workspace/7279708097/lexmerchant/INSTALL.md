# LexMerchant - Installation Guide

## 📋 Quick Installation Steps

### 1. Download & Extract
1. Download `lexmerchant.tar.gz`
2. Upload ke cPanel File Manager
3. Extract di folder `public_html/`

### 2. Create Database
1. Buka **cPanel → MySQL Databases**
2. Create database: `lexmerchant`
3. Create MySQL user dengan password
4. Add user ke database dengan **ALL PRIVILEGES**
5. Catat: database name, username, password

### 3. Import Database
1. Buka **phpMyAdmin**
2. Pilih database `lexmerchant`
3. Klik tab **Import**
4. Upload file `database.sql`
5. Klik **Go**

### 4. Configure
Edit file `config.php`:
```php
define('DB_HOST', 'localhost');
define('DB_NAME', 'lexmerchant');           // Database name dari step 2
define('DB_USER', 'your_db_user');          // MySQL username dari step 2
define('DB_PASS', 'your_db_password');      // MySQL password dari step 2
define('SITE_URL', 'https://yourdomain.com'); // Domain Anda (tanpa trailing slash)
```

### 5. Set Permissions (via cPanel Terminal atau SSH)
```bash
chmod 755 public_html/lexmerchant
chmod 644 public_html/lexmerchant/*.php
chmod 644 public_html/lexmerchant/.htaccess
```

### 6. Test Installation
1. Buka browser: `https://yourdomain.com/lexmerchant/`
2. Akan redirect ke login page
3. **Test admin login:**
   - Username: `admin`
   - Password: `admin123`
4. **PENTING:** Setelah login, segera ganti password admin!

---

## 🔐 Default Credentials

**Admin Panel:**
- URL: `https://yourdomain.com/lexmerchant/admin/`
- Username: `admin`
- Password: `admin123`

**⚠️ SECURITY:** Ganti password admin segera setelah login pertama!

---

## 👥 User Flow

### For Users:
1. **Register** → `https://yourdomain.com/lexmerchant/register.php`
2. **Login** → Input username & password
3. **Setup GoPay Merchant:**
   - Masuk menu "GoPay Setup"
   - Input Merchant ID, Terminal ID, API Key dari GoPay Merchant dashboard
4. **Add QRIS:**
   - Masuk menu "Kelola QRIS"
   - Upload QRIS code manual dari GoPay
   - Set amount (0 = dynamic)
   - Optional: callback URL untuk webhook
5. **Get API Credentials:**
   - Masuk menu "API Settings"
   - Copy API Key & API Secret
6. **Integration:**
   - Gunakan API untuk create transaction
   - System auto-detect payment dari GoPay
   - Webhook callback (jika diset)

---

## 🔑 API Integration Example

### Authentication
```bash
X-API-Key: lex_xxxxxxxxxxxxx
X-API-Secret: xxxxxxxxxxxxxx
```

### Create Transaction
```bash
curl -X POST "https://yourdomain.com/lexmerchant/api/v1/transaction/create" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "X-API-Secret: YOUR_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "qris_id": 1,
    "amount": 50000,
    "customer_name": "John Doe"
  }'
```

### Check Transaction Status
```bash
curl -X POST "https://yourdomain.com/lexmerchant/api/v1/transaction/check" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "X-API-Secret: YOUR_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TRX20260903001234"
  }'
```

---

## 📁 File Structure

```
lexmerchant/
├── config.php              # Database & site configuration
├── database.sql            # Database schema & default data
├── index.php               # Entry point (redirect to login)
├── login.php               # User login
├── register.php            # User registration
├── logout.php              # Logout handler
├── dashboard.php           # User dashboard
├── gopay_setup.php         # GoPay merchant setup
├── qris.php                # QRIS management
├── transactions.php        # Transaction list
├── api.php                 # API documentation page
├── .htaccess               # Apache rewrite rules
├── README.md               # Documentation
├── INSTALL.md              # This file
├── api/
│   └── v1/
│       └── index.php       # API endpoints
└── admin/
    ├── index.php           # Admin dashboard
    ├── users.php           # User management
    ├── transactions.php    # All transactions
    └── settings.php        # System settings
```

---

## ⚙️ Admin Panel Features

Access: `https://yourdomain.com/lexmerchant/admin/`

1. **Dashboard:**
   - Total users, QRIS, transactions, revenue
   - Recent users & transactions

2. **User Management:**
   - View all users
   - Suspend/Activate users
   - Delete users
   - View GoPay setup status

3. **Transactions:**
   - View all transactions
   - Filter by status & user
   - Export data (future feature)

4. **Settings:**
   - Admin fee percentage
   - Min/max transaction limits
   - QRIS check interval
   - GoPay global settings

---

## 🔧 Troubleshooting

### Database Connection Error
- Pastikan credentials di `config.php` benar
- Pastikan MySQL user punya akses ke database
- Test koneksi via phpMyAdmin

### 404 Error pada API
- Pastikan `.htaccess` ada dan readable
- Pastikan mod_rewrite enabled di Apache
- Cek file permissions

### QRIS Tidak Terdeteksi
- Pastikan user sudah setup GoPay Merchant credentials
- Cek API key & merchant ID valid
- Cek koneksi ke GoPay API

### Blank Page
- Enable error reporting di `config.php`:
  ```php
  ini_set('display_errors', 1);
  error_reporting(E_ALL);
  ```
- Cek PHP error log di cPanel

---

## 📞 Support

Untuk bantuan lebih lanjut:
- Email: support@lexmerchant.com
- Documentation: README.md

---

## ✅ Post-Installation Checklist

- [ ] Database imported successfully
- [ ] `config.php` configured with correct credentials
- [ ] Admin login works
- [ ] Admin password changed from default
- [ ] User registration works
- [ ] GoPay setup page accessible
- [ ] API endpoint returns response
- [ ] `.htaccess` rewrite rules working

---

**LexMerchant** © 2026 - Professional QRIS Payment Gateway