<?php
require_once 'config.php';
requireLogin();

$user_id = $_SESSION['user_id'];

$error = '';
$success = '';

// Get current settings
$stmt = $pdo->prepare("SELECT gopay_merchant_id, gopay_terminal_id, gopay_api_key FROM users WHERE id = ?");
$stmt->execute([$user_id]);
$user = $stmt->fetch();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $merchant_id = trim($_POST['merchant_id'] ?? '');
    $terminal_id = trim($_POST['terminal_id'] ?? '');
    $api_key = trim($_POST['api_key'] ?? '');
    
    if (empty($merchant_id) || empty($api_key)) {
        $error = 'Merchant ID dan API Key wajib diisi';
    } else {
        try {
            $stmt = $pdo->prepare("
                UPDATE users 
                SET gopay_merchant_id = ?, gopay_terminal_id = ?, gopay_api_key = ?
                WHERE id = ?
            ");
            $stmt->execute([$merchant_id, $terminal_id, $api_key, $user_id]);
            $success = 'Konfigurasi GoPay Merchant berhasil disimpan!';
            
            // Refresh data
            $stmt = $pdo->prepare("SELECT gopay_merchant_id, gopay_terminal_id, gopay_api_key FROM users WHERE id = ?");
            $stmt->execute([$user_id]);
            $user = $stmt->fetch();
        } catch(PDOException $e) {
            $error = 'Error: ' . $e->getMessage();
        }
    }
}
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Setup GoPay Merchant - LexMerchant</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; }
        .navbar { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .navbar h2 { font-size: 24px; }
        .navbar a { color: white; text-decoration: none; padding: 8px 16px; background: rgba(255,255,255,0.2); border-radius: 5px; transition: background 0.3s; margin-left: 10px; }
        .navbar a:hover { background: rgba(255,255,255,0.3); }
        .container { padding: 30px; max-width: 800px; margin: 0 auto; }
        .section { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .section h2 { margin-bottom: 10px; color: #333; }
        .section p { color: #666; margin-bottom: 20px; line-height: 1.6; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; color: #333; font-weight: 500; }
        input { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 14px; font-family: monospace; }
        input:focus { outline: none; border-color: #667eea; }
        .btn { padding: 14px 28px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: transform 0.2s; }
        .btn:hover { transform: translateY(-2px); }
        .error { background: #fee; color: #c33; padding: 12px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #c33; }
        .success { background: #efe; color: #2d7a2d; padding: 12px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #2d7a2d; }
        .info-box { background: #e6f7ff; border-left: 4px solid #1890ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .info-box h3 { color: #1890ff; margin-bottom: 10px; font-size: 16px; }
        .info-box ol { margin-left: 20px; color: #333; }
        .info-box li { margin-bottom: 8px; line-height: 1.5; }
    </style>
</head>
<body>
    <div class="navbar">
        <h2>🚀 LexMerchant</h2>
        <div>
            <a href="dashboard.php">Dashboard</a>
            <a href="qris.php">QRIS</a>
            <a href="logout.php">Logout</a>
        </div>
    </div>
    
    <div class="container">
        <?php if ($error): ?>
            <div class="error"><?= htmlspecialchars($error) ?></div>
        <?php endif; ?>
        
        <?php if ($success): ?>
            <div class="success"><?= htmlspecialchars($success) ?></div>
        <?php endif; ?>
        
        <div class="info-box">
            <h3>📋 Cara Mendapatkan GoPay Merchant Credentials</h3>
            <ol>
                <li>Login ke <strong>GoPay Merchant Dashboard</strong> (dashboard.midtrans.com atau portal GoPay Anda)</li>
                <li>Masuk ke menu <strong>Settings → API Keys</strong></li>
                <li>Copy <strong>Merchant ID</strong> dan <strong>Server Key / API Key</strong></li>
                <li>Untuk Terminal ID, bisa ditemukan di menu <strong>QRIS Settings</strong> atau bisa dikosongkan</li>
                <li>Paste credentials ke form di bawah ini</li>
            </ol>
        </div>
        
        <div class="section">
            <h2>Konfigurasi GoPay Merchant</h2>
            <p>Masukkan credentials GoPay Merchant Anda untuk mengaktifkan auto-detect pembayaran QRIS.</p>
            
            <form method="POST">
                <div class="form-group">
                    <label>Merchant ID *</label>
                    <input type="text" name="merchant_id" placeholder="G123456789" value="<?= htmlspecialchars($user['gopay_merchant_id'] ?? '') ?>" required>
                </div>
                
                <div class="form-group">
                    <label>Terminal ID (Opsional)</label>
                    <input type="text" name="terminal_id" placeholder="T001" value="<?= htmlspecialchars($user['gopay_terminal_id'] ?? '') ?>">
                </div>
                
                <div class="form-group">
                    <label>API Key / Server Key *</label>
                    <input type="text" name="api_key" placeholder="SB-Mid-server-xxxxxxxxxxxxxxxx" value="<?= htmlspecialchars($user['gopay_api_key'] ?? '') ?>" required>
                </div>
                
                <button type="submit" class="btn">Simpan Konfigurasi</button>
            </form>
        </div>
        
        <?php if (!empty($user['gopay_merchant_id'])): ?>
        <div class="section" style="background: #f0fdf4; border-left: 4px solid #22c55e;">
            <h2 style="color: #16a34a;">✓ Status Konfigurasi</h2>
            <p style="color: #15803d;">GoPay Merchant Anda sudah terkonfigurasi. Sekarang Anda bisa menambahkan QRIS dan menerima pembayaran otomatis!</p>
            <a href="qris.php" class="btn">Kelola QRIS</a>
        </div>
        <?php endif; ?>
    </div>
</body>
</html>