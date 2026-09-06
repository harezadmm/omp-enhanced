<?php
require_once 'config.php';
requireLogin();

$user_id = $_SESSION['user_id'];

// Get transactions
$filter = $_GET['status'] ?? 'all';
$query = "
    SELECT t.*, q.qris_name 
    FROM transactions t
    JOIN qris_codes q ON t.qris_id = q.id
    WHERE t.user_id = ?
";

if ($filter !== 'all') {
    $query .= " AND t.payment_status = ?";
}

$query .= " ORDER BY t.created_at DESC LIMIT 100";

$stmt = $pdo->prepare($query);
if ($filter !== 'all') {
    $stmt->execute([$user_id, $filter]);
} else {
    $stmt->execute([$user_id]);
}
$transactions = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transaksi - LexMerchant</title>
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
        .filter-tabs { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 2px solid #e0e0e0; }
        .filter-tabs a { padding: 12px 24px; text-decoration: none; color: #666; font-weight: 600; border-bottom: 3px solid transparent; transition: all 0.3s; }
        .filter-tabs a:hover { color: #667eea; }
        .filter-tabs a.active { color: #667eea; border-bottom-color: #667eea; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }
        th { background: #f8f9fa; font-weight: 600; color: #666; }
        .badge { padding: 5px 10px; border-radius: 5px; font-size: 12px; font-weight: 600; }
        .badge.success { background: #c6f6d5; color: #22543d; }
        .badge.pending { background: #feebc8; color: #7c2d12; }
        .badge.failed { background: #fed7d7; color: #742a2a; }
        .badge.expired { background: #e0e0e0; color: #666; }
        .empty { text-align: center; color: #666; padding: 40px; }
    </style>
</head>
<body>
    <div class="navbar">
        <h2>🚀 LexMerchant</h2>
        <div>
            <a href="dashboard.php">Dashboard</a>
            <a href="qris.php">QRIS</a>
            <a href="api.php">API</a>
            <a href="logout.php">Logout</a>
        </div>
    </div>
    
    <div class="container">
        <div class="section">
            <h2>Riwayat Transaksi</h2>
            
            <div class="filter-tabs">
                <a href="?status=all" class="<?= $filter === 'all' ? 'active' : '' ?>">Semua</a>
                <a href="?status=pending" class="<?= $filter === 'pending' ? 'active' : '' ?>">Pending</a>
                <a href="?status=success" class="<?= $filter === 'success' ? 'active' : '' ?>">Success</a>
                <a href="?status=failed" class="<?= $filter === 'failed' ? 'active' : '' ?>">Failed</a>
                <a href="?status=expired" class="<?= $filter === 'expired' ? 'active' : '' ?>">Expired</a>
            </div>
            
            <?php if (count($transactions) > 0): ?>
            <table>
                <thead>
                    <tr>
                        <th>Transaction ID</th>
                        <th>QRIS</th>
                        <th>Customer</th>
                        <th>Amount</th>
                        <th>Admin Fee</th>
                        <th>Net Amount</th>
                        <th>Status</th>
                        <th>Payment Time</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($transactions as $trx): ?>
                    <tr>
                        <td><strong><?= htmlspecialchars($trx['transaction_id']) ?></strong></td>
                        <td><?= htmlspecialchars($trx['qris_name']) ?></td>
                        <td><?= htmlspecialchars($trx['customer_name'] ?? '-') ?></td>
                        <td>Rp <?= number_format($trx['amount'], 0, ',', '.') ?></td>
                        <td>Rp <?= number_format($trx['admin_fee'], 0, ',', '.') ?></td>
                        <td>Rp <?= number_format($trx['net_amount'], 0, ',', '.') ?></td>
                        <td><span class="badge <?= $trx['payment_status'] ?>"><?= strtoupper($trx['payment_status']) ?></span></td>
                        <td><?= $trx['payment_time'] ? date('d/m/Y H:i', strtotime($trx['payment_time'])) : '-' ?></td>
                        <td><?= date('d/m/Y H:i', strtotime($trx['created_at'])) ?></td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
            <?php else: ?>
            <div class="empty">Belum ada transaksi</div>
            <?php endif; ?>
        </div>
    </div>
</body>
</html>