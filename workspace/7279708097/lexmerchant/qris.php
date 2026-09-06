<?php
require_once 'config.php';
requireLogin();

$user_id = $_SESSION['user_id'];

// Check if user has GoPay credentials
$stmt = $pdo->prepare("SELECT gopay_merchant_id, gopay_terminal_id, gopay_api_key FROM users WHERE id = ?");
$stmt->execute([$user_id]);
$user = $stmt->fetch();

if (empty($user['gopay_merchant_id']) || empty($user['gopay_api_key'])) {
    header('Location: gopay_setup.php');
    exit;
}

$error = '';
$success = '';

// Handle QRIS upload
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action']) && $_POST['action'] === 'add_qris') {
    $qris_name = trim($_POST['qris_name'] ?? '');
    $qris_code = trim($_POST['qris_code'] ?? '');
    $amount = floatval($_POST['amount'] ?? 0);
    $callback_url = trim($_POST['callback_url'] ?? '');
    
    if (empty($qris_name) || empty($qris_code)) {
        $error = 'Nama QRIS dan kode QRIS wajib diisi';
    } else {
        try {
            $stmt = $pdo->prepare("
                INSERT INTO qris_codes (user_id, qris_name, qris_code, amount, callback_url, merchant_id, terminal_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ");
            $stmt->execute([
                $user_id, 
                $qris_name, 
                $qris_code, 
                $amount, 
                $callback_url,
                $user['gopay_merchant_id'],
                $user['gopay_terminal_id']
            ]);
            $success = 'QRIS berhasil ditambahkan!';
        } catch(PDOException $e) {
            $error = 'Error: ' . $e->getMessage();
        }
    }
}

// Handle delete
if (isset($_GET['delete'])) {
    $qris_id = intval($_GET['delete']);
    try {
        $stmt = $pdo->prepare("DELETE FROM qris_codes WHERE id = ? AND user_id = ?");
        $stmt->execute([$qris_id, $user_id]);
        $success = 'QRIS berhasil dihapus!';
    } catch(PDOException $e) {
        $error = 'Error: ' . $e->getMessage();
    }
}

// Get all QRIS
$stmt = $pdo->prepare("SELECT * FROM qris_codes WHERE user_id = ? ORDER BY created_at DESC");
$stmt->execute([$user_id]);
$qris_list = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kelola QRIS - LexMerchant</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; }
        .navbar { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .navbar h2 { font-size: 24px; }
        .navbar a { color: white; text-decoration: none; padding: 8px 16px; background: rgba(255,255,255,0.2); border-radius: 5px; transition: background 0.3s; margin-left: 10px; }
        .navbar a:hover { background: rgba(255,255,255,0.3); }
        .container { padding: 30px; max-width: 1400px; margin: 0 auto; }
        .section { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .section h2 { margin-bottom: 20px; color: #333; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #333; font-weight: 500; }
        input, textarea { width: 100%; padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 14px; }
        input:focus, textarea:focus { outline: none; border-color: #667eea; }
        textarea { resize: vertical; min-height: 100px; font-family: monospace; }
        .btn { padding: 12px 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: transform 0.2s; }
        .btn:hover { transform: translateY(-2px); }
        .btn-danger { background: linear-gradient(135deg, #f56565 0%, #c53030 100%); }
        .btn-small { padding: 6px 12px; font-size: 12px; }
        .error { background: #fee; color: #c33; padding: 12px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #c33; }
        .success { background: #efe; color: #2d7a2d; padding: 12px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #2d7a2d; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }
        th { background: #f8f9fa; font-weight: 600; color: #666; }
        .badge { padding: 5px 10px; border-radius: 5px; font-size: 12px; font-weight: 600; }
        .badge.active { background: #c6f6d5; color: #22543d; }
        .badge.inactive { background: #fed7d7; color: #742a2a; }
        .actions { display: flex; gap: 10px; }
        .qris-code { font-family: monospace; font-size: 11px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    </style>
</head>
<body>
    <div class="navbar">
        <h2>🚀 LexMerchant</h2>
        <div>
            <a href="dashboard.php">Dashboard</a>
            <a href="transactions.php">Transaksi</a>
            <a href="api.php">API</a>
            <a href="gopay_setup.php">GoPay Setup</a>
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
        
        <div class="section">
            <h2>Tambah QRIS Baru</h2>
            <form method="POST">
                <input type="hidden" name="action" value="add_qris">
                
                <div class="form-group">
                    <label>Nama QRIS *</label>
                    <input type="text" name="qris_name" placeholder="Contoh: QRIS Toko A" required>
                </div>
                
                <div class="form-group">
                    <label>Kode QRIS (String QRIS) *</label>
                    <textarea name="qris_code" placeholder="00020101021226..." required></textarea>
                    <small style="color: #666;">Paste kode QRIS manual dari GoPay Merchant</small>
                </div>
                
                <div class="form-group">
                    <label>Amount (Opsional, 0 = dynamic)</label>
                    <input type="number" name="amount" placeholder="10000" min="0" step="1">
                </div>
                
                <div class="form-group">
                    <label>Callback URL (Opsional)</label>
                    <input type="url" name="callback_url" placeholder="https://yourdomain.com/webhook">
                    <small style="color: #666;">URL untuk menerima notifikasi pembayaran</small>
                </div>
                
                <button type="submit" class="btn">Tambah QRIS</button>
            </form>
        </div>
        
        <div class="section">
            <h2>Daftar QRIS</h2>
            <?php if (count($qris_list) > 0): ?>
            <table>
                <thead>
                    <tr>
                        <th>Nama QRIS</th>
                        <th>Kode QRIS</th>
                        <th>Amount</th>
                        <th>Transaksi</th>
                        <th>Revenue</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($qris_list as $qris): ?>
                    <tr>
                        <td><strong><?= htmlspecialchars($qris['qris_name']) ?></strong></td>
                        <td><div class="qris-code" title="<?= htmlspecialchars($qris['qris_code']) ?>"><?= htmlspecialchars(substr($qris['qris_code'], 0, 30)) ?>...</div></td>
                        <td><?= $qris['amount'] > 0 ? 'Rp ' . number_format($qris['amount'], 0, ',', '.') : 'Dynamic' ?></td>
                        <td><?= number_format($qris['total_transactions']) ?></td>
                        <td>Rp <?= number_format($qris['total_revenue'], 0, ',', '.') ?></td>
                        <td><span class="badge <?= $qris['status'] ?>"><?= strtoupper($qris['status']) ?></span></td>
                        <td class="actions">
                            <a href="qris_detail.php?id=<?= $qris['id'] ?>" class="btn btn-small">Detail</a>
                            <a href="?delete=<?= $qris['id'] ?>" class="btn btn-small btn-danger" onclick="return confirm('Hapus QRIS ini?')">Hapus</a>
                        </td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
            <?php else: ?>
            <p style="text-align: center; color: #666; padding: 40px;">Belum ada QRIS. Tambahkan QRIS pertama Anda!</p>
            <?php endif; ?>
        </div>
    </div>
</body>
</html>