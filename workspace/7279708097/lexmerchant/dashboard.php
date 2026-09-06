<?php
require_once 'config.php';
requireLogin();

$user_id = $_SESSION['user_id'];

// Get user data
$stmt = $pdo->prepare("SELECT * FROM users WHERE id = ?");
$stmt->execute([$user_id]);
$user = $stmt->fetch();

// Get statistics
$stmt = $pdo->prepare("SELECT COUNT(*) as total FROM qris_codes WHERE user_id = ? AND status = 'active'");
$stmt->execute([$user_id]);
$total_qris = $stmt->fetch()['total'];

$stmt = $pdo->prepare("SELECT COUNT(*) as total FROM transactions WHERE user_id = ? AND payment_status = 'success'");
$stmt->execute([$user_id]);
$total_transactions = $stmt->fetch()['total'];

$stmt = $pdo->prepare("SELECT COALESCE(SUM(net_amount), 0) as total FROM transactions WHERE user_id = ? AND payment_status = 'success'");
$stmt->execute([$user_id]);
$total_revenue = $stmt->fetch()['total'];

$stmt = $pdo->prepare("
    SELECT COUNT(*) as total 
    FROM transactions 
    WHERE user_id = ? 
    AND payment_status = 'success' 
    AND DATE(payment_time) = CURDATE()
");
$stmt->execute([$user_id]);
$today_transactions = $stmt->fetch()['total'];

// Recent transactions
$stmt = $pdo->prepare("
    SELECT t.*, q.qris_name 
    FROM transactions t
    JOIN qris_codes q ON t.qris_id = q.id
    WHERE t.user_id = ?
    ORDER BY t.created_at DESC
    LIMIT 10
");
$stmt->execute([$user_id]);
$recent_transactions = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - LexMerchant</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; }
        .navbar { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .navbar h2 { font-size: 24px; }
        .navbar .user-info { display: flex; align-items: center; gap: 20px; }
        .navbar a { color: white; text-decoration: none; padding: 8px 16px; background: rgba(255,255,255,0.2); border-radius: 5px; transition: background 0.3s; }
        .navbar a:hover { background: rgba(255,255,255,0.3); }
        .container { padding: 30px; max-width: 1400px; margin: 0 auto; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .stat-card h3 { color: #666; font-size: 14px; margin-bottom: 10px; text-transform: uppercase; }
        .stat-card .value { font-size: 32px; font-weight: bold; color: #333; }
        .stat-card.primary .value { color: #667eea; }
        .stat-card.success .value { color: #48bb78; }
        .stat-card.warning .value { color: #ed8936; }
        .stat-card.info .value { color: #4299e1; }
        .menu-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .menu-card { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); text-align: center; cursor: pointer; transition: transform 0.3s, box-shadow 0.3s; text-decoration: none; color: #333; display: block; }
        .menu-card:hover { transform: translateY(-5px); box-shadow: 0 5px 20px rgba(0,0,0,0.1); }
        .menu-card .icon { font-size: 40px; margin-bottom: 10px; }
        .menu-card h3 { margin-bottom: 5px; }
        .menu-card p { font-size: 13px; color: #666; }
        .section { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .section h2 { margin-bottom: 20px; color: #333; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }
        th { background: #f8f9fa; font-weight: 600; color: #666; }
        .badge { padding: 5px 10px; border-radius: 5px; font-size: 12px; font-weight: 600; }
        .badge.success { background: #c6f6d5; color: #22543d; }
        .badge.pending { background: #feebc8; color: #7c2d12; }
        .badge.failed { background: #fed7d7; color: #742a2a; }
        .api-box { background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; margin-top: 15px; }
        .api-box code { background: #e0e0e0; padding: 2px 8px; border-radius: 4px; font-family: monospace; }
    </style>
</head>
<body>
    <div class="navbar">
        <h2>🚀 LexMerchant</h2>
        <div class="user-info">
            <span>Hi, <?= htmlspecialchars($user['full_name']) ?></span>
            <a href="logout.php">Logout</a>
        </div>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat-card primary">
                <h3>Total QRIS Aktif</h3>
                <div class="value"><?= $total_qris ?></div>
            </div>
            <div class="stat-card success">
                <h3>Total Transaksi</h3>
                <div class="value"><?= number_format($total_transactions) ?></div>
            </div>
            <div class="stat-card warning">
                <h3>Total Revenue</h3>
                <div class="value">Rp <?= number_format($total_revenue, 0, ',', '.') ?></div>
            </div>
            <div class="stat-card info">
                <h3>Transaksi Hari Ini</h3>
                <div class="value"><?= $today_transactions ?></div>
            </div>
        </div>
        
        <div class="menu-grid">
            <a href="qris.php" class="menu-card">
                <div class="icon">📱</div>
                <h3>Kelola QRIS</h3>
                <p>Upload & manage QRIS codes</p>
            </a>
            <a href="transactions.php" class="menu-card">
                <div class="icon">💳</div>
                <h3>Transaksi</h3>
                <p>Lihat semua transaksi</p>
            </a>
            <a href="api.php" class="menu-card">
                <div class="icon">🔑</div>
                <h3>API Settings</h3>
                <p>API Key & dokumentasi</p>
            </a>
            <a href="profile.php" class="menu-card">
                <div class="icon">⚙️</div>
                <h3>Profile</h3>
                <p>Edit profil & password</p>
            </a>
        </div>
        
        <div class="section">
            <h2>API Credentials</h2>
            <p>Gunakan credentials berikut untuk integrasi API:</p>
            <div class="api-box">
                <p><strong>API Key:</strong> <code><?= htmlspecialchars($user['api_key']) ?></code></p>
                <p style="margin-top: 10px;"><strong>API Secret:</strong> <code><?= htmlspecialchars($user['api_secret']) ?></code></p>
                <p style="margin-top: 10px;"><strong>Base URL:</strong> <code><?= SITE_URL ?>/api/</code></p>
            </div>
        </div>
        
        <div class="section">
            <h2>Transaksi Terakhir</h2>
            <?php if (count($recent_transactions) > 0): ?>
            <table>
                <thead>
                    <tr>
                        <th>Transaction ID</th>
                        <th>QRIS</th>
                        <th>Amount</th>
                        <th>Status</th>
                        <th>Waktu</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($recent_transactions as $trx): ?>
                    <tr>
                        <td><?= htmlspecialchars($trx['transaction_id']) ?></td>
                        <td><?= htmlspecialchars($trx['qris_name']) ?></td>
                        <td>Rp <?= number_format($trx['amount'], 0, ',', '.') ?></td>
                        <td>
                            <?php
                            $badge_class = $trx['payment_status'] === 'success' ? 'success' : ($trx['payment_status'] === 'pending' ? 'pending' : 'failed');
                            ?>
                            <span class="badge <?= $badge_class ?>"><?= strtoupper($trx['payment_status']) ?></span>
                        </td>
                        <td><?= date('d/m/Y H:i', strtotime($trx['created_at'])) ?></td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
            <?php else: ?>
            <p style="text-align: center; color: #666; padding: 40px;">Belum ada transaksi</p>
            <?php endif; ?>
        </div>
    </div>
</body>
</html>