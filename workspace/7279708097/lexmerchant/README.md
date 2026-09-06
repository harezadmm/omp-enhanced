# LexMerchant - QRIS Payment Gateway

Professional QRIS payment system dengan auto-detection dari GoPay Merchant.

## 🚀 Features

- ✅ User registration & login system
- ✅ GoPay Merchant integration (setiap user input sendiri)
- ✅ QRIS code management (upload manual QRIS)
- ✅ Auto payment detection
- ✅ Transaction management
- ✅ RESTful API dengan API key authentication
- ✅ Webhook callback support
- ✅ Admin panel lengkap (manage users, transactions, settings)
- ✅ API request logging
- ✅ Responsive design

## 📦 Installation

### 1. Upload ke cPanel

1. Zip folder `lexmerchant/`
2. Upload ke cPanel File Manager
3. Extract di folder `public_html/`

### 2. Setup Database

1. Buka **cPanel → phpMyAdmin**
2. Import file `database.sql`
3. Database `lexmerchant` akan terbuat otomatis dengan semua table

### 3. Configuration

Edit file `config.php`:

```php
define('DB_HOST', 'localhost');
define('DB_NAME', 'lexmerchant');
define('DB_USER', 'root');          // Ganti dengan DB user cPanel Anda
define('DB_PASS', '');               // Ganti dengan DB password cPanel Anda
define('SITE_URL', 'https://yourdomain.com'); // Ganti dengan domain Anda
```

### 4. Set Permissions

```bash
chmod 755 lexmerchant/
chmod 644 lexmerchant/*.php
chmod 644 lexmerchant/.htaccess
```

## 👤 Default Login

**Admin:**
- Username: `admin`
- Password: `admin123`
- Admin panel: `https://yourdomain.com/admin/`

**User Registration:**
- Register di: `https://yourdomain.com/register.php`

## 🔧 User Flow

1. **Register** → User daftar akun baru
2. **Setup GoPay** → Input Merchant ID, Terminal ID, API Key dari GoPay Merchant
3. **Add QRIS** → Upload QRIS code manual
4. **Integration** → Gunakan API untuk create transaction & check payment status
5. **Auto-detect** → System auto-detect payment dari GoPay dan update status

## 🔑 API Usage

### Authentication

Kirim credentials via HTTP headers:
```bash
X-API-Key: lex_xxxxxxxxxxxxx
X-API-Secret: xxxxxxxxxxxxxx
```

### Base URL
```
https://yourdomain.com/api/v1/
```

### Endpoints

**1. Get API Info**
```bash
GET /api/v1/
```

**2. List QRIS**
```bash
GET /api/v1/qris
```

**3. Create QRIS**
```bash
POST /api/v1/qris
{
  "qris_name": "QRIS Toko A",
  "qris_code": "00020101021226...",
  "amount": 10000,
  "callback_url": "https://yourdomain.com/webhook"
}
```

**4. Create Transaction**
```bash
POST /api/v1/transaction/create
{
  "qris_id": 1,
  "amount": 50000,
  "customer_name": "John Doe"
}
```

**5. Check Transaction**
```bash
POST /api/v1/transaction/check
{
  "transaction_id": "TRX20260903001234"
}
```

## 📊 Admin Panel

Access: `https://yourdomain.com/admin/`

Features:
- Dashboard dengan statistics
- Manage users (suspend, activate, delete)
- View all transactions
- System settings (admin fee, limits)
- API logs monitoring

## 🗂️ File Structure

```
lexmerchant/
├── config.php              # Configuration
├── database.sql            # Database schema
├── index.php               # Redirect to login
├── login.php               # User login
├── register.php            # User registration
├── logout.php              # Logout
├── dashboard.php           # User dashboard
├── gopay_setup.php         # GoPay credentials setup
├── qris.php                # QRIS management
├── api.php                 # API documentation
├── .htaccess               # Apache config
├── api/
│   └── v1/
│       └── index.php       # API endpoint handler
├── admin/
│   ├── index.php           # Admin dashboard
│   ├── users.php           # User management
│   └── transactions.php    # Transaction management
└── README.md               # This file
```

## 🔐 Security

- ✅ Password hashing dengan bcrypt
- ✅ SQL injection protection (PDO prepared statements)
- ✅ XSS protection (htmlspecialchars)
- ✅ API key authentication
- ✅ Rate limiting ready (via API logs)
- ✅ Session security

## 📝 Requirements

- PHP 7.4+
- MySQL 5.7+
- Apache dengan mod_rewrite
- cURL support
- JSON support

## 🛠️ Development

Local development:
```bash
php -S localhost:8000
```

Production: Upload ke cPanel dengan Apache + PHP + MySQL

## 📧 Support

Email: support@lexmerchant.com

---

**LexMerchant** © 2026 - Professional QRIS Payment Gateway