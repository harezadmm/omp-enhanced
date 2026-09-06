<?php
require_once '../config.php';
requireLogin();

if ($_SESSION['role'] !== 'admin') {
    die('Access denied. Admin only.');
}

// Get filter
$filter = $_GET['status'] ?? 'all';
$user_filter = $_GET['user_id'] ?? '';

$query = "
    SELECT t.*, u.username, q.qris_name
    FROM transactions t
    JOIN users u ON t.user_id = u.id
    JOIN qris_codes q ON t.qris_id = q.id
    WHERE 1=1
";

$params = [];

if ($filter !== 'all') {
    $query .= " AND t.payment_status = ?";
    $params[] = $filter;
}

if ($user_filter) {
    $query .= " AND t.user_id = ?";
    $params[] = $user_filter;
}

$query .= " ORDER BY t.created_at DESC LIMIT 200";

$stmt = $pdo->prepare($query);
$stmt->execute($params);
$transactions = $stmt->fetchAll();

// Get all users for filter
$stmt = $pdo->query("SELECT id, username FROM users WHERE role = 'user' ORDER BY username");
$users = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>All Transactions - LexMerchant Admin</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; }
        
        .sidebar { position: fixed; left: 0; top: 0; bottom: 0; width: 260px; background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%); color: white; overflow-y: auto; z-index: 1000; }
        .sidebar-header { padding: 25px 20px; background: rgba(255,255,255,0.05); border-bottom: 1px solid rgba(255,255,255,0.1); }
        .sidebar-header h2 { font-size: 22px; display: flex; align-items: center; gap: 10px; }
        .sidebar-menu { padding: 20px 0; }
        .menu-item { display: flex; align-items: center; gap: 12px; padding: 14px 25px; color: rgba(255,255,255,0.8); text-decoration: none; transition: all 0.3s; border-left: 3px solid transparent; }
        .menu-item:hover, .menu-item.active { background: rgba(255,255,255,0.1); color: white; border-left-color: #3b82f6; }
        .menu-item i { width: 20px; font-size: 16px; }
        
        .main-content { margin-left: 260px; min-height: 100vh; }
        .topbar { background: white; padding: 15px 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }
        .topbar h1 { font-size: 24px; color: #1e293b; }
        .topbar-right { display: flex; align-items: center; gap: 20px; }
        .user-info { display: flex; align-items: center; gap: 10px; }
        .user-avatar { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; }
        .btn-logout { padding: 8px 16px; background: #ef4444; color: white; text-decoration: none; border-radius: 6px; font-size: 14px; transition: background 0.3s; }
        .btn-logout:hover { background: #dc2626; }
        
        .container { padding: 30px; }
        .section-card { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 30px; overflow: hidden; }
        .section-header { padding: 20px 25px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
        .section-header h2 { font-size: 18px; color: #1e293b; display: flex; align-items: center; gap: 10px; }
        .section-body { padding: 25px; }
        
        .filters { display: flex; gap: 15px; margin-bottom: 25px; align-items: center; flex-wrap: wrap; }
        .filter-tabs { display: flex; gap: 10px; flex-wrap: wrap; }
        .filter-tabs a { padding: 10px 18px; text-decoration: none; color: #64748b; font-weight: 600; border-radius: 8px; transition: all 0.3s; font-size: 13px; background: #f1f5f9; }
        .filter-tabs a:hover { background: #e2e8f0; color: #1e293b; }
        .filter-tabs a.active { background: #3b82f6; color: white; }
        
        select { padding: 10px 15px; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 14px; }
        
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
        th { background: #f8fafc; font-weight: 600; color: #475569; text-transform: uppercase; font-size: 11px; }
        tbody tr:hover { background: #f8fafc; }
        
        .badge { padding: 5px 12px; border-radius: 20px; font-size: 11px; font-weight: 600; display: inline-block; }
        .badge.success { background: #d1fae5; color: #065f46; }
        .badge.pending { background: #fef3c7; color: #92400e; }
        .badge.failed { background: #fee2e2; color: #991b1b; }
        .badge.expired { background: #e2e8f0; color: #475569; }
        
        .empty { text-align: center; padding: 60px 20px; color: #94a3b8; }
        .empty i { font-size: 48px; margin-bottom: 15px; opacity: 0.5; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h2><i class="fas fa-rocket"></i> LexMerchant</h2>
        </div>
        <div class="sidebar-menu">
            <a href="index.php" class="menu-item">
                <i class="fas fa-home"></i>
                <span>Dashboard</span>
            </a>
            <a href="users.php" class="menu-item">
                <i class="fas fa-users"></i>
                <span>Users</span>
            </a>
            <a href="qris.php" class="menu-item">
                <i class="fas fa-qrcode"></i>
                <span>All QRIS</span>
            </a>
            <a href="transactions.php" class="menu-item active">
                <i class="fas fa-exchange-alt"></i>
                <span>Transactions</span>
            </a>
            <a href="api_logs.php" class="menu-item">
                <i class="fas fa-file-alt"></i>
                <span>API Logs</span>
            </a>
            <a href="settings.php" class="menu-item">
                <i class="fas fa-cog"></i>
                <span>Settings</span>
            </a>
            <a href="../dashboard.php" class="menu-item">
                <i class="fas fa-user"></i>
                <span>User View</span>
            </a>
        </div>
    </div>
    
    <div class="main-content">
        <div class="topbar">
            <h1>All Transactions</h1>
            <div class="topbar-right">
                <div class="user-info">
                    <div class="user-avatar">A</div>
                    <span><strong>Admin</strong></span>
                </div>
                <a href="../logout.php" class="btn-logout">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </a>
            </div>
        </div>
        
        <div class="container">
            <div class="section-card">
                <div class="section-header">
                    <h2><i class="fas fa-exchange-alt"></i> All Transactions (<?= count($transactions) ?>)</h2>
                </div>
                <div class="section-body">
                    <div class="filters">
                        <div class="filter-tabs">
                            <a href="?status=all<?= $user_filter ? '&user_id='.$user_filter : '' ?>" class="<?= $filter === 'all' ? 'active' : '' ?>">
                                <i class="fas fa-list"></i> All
                            </a>
                            <a href="?status=pending<?= $user_filter ? '&user_id='.$user_filter : '' ?>" class="<?= $filter === 'pending' ? 'active' : '' ?>">
                                <i class="fas fa-clock"></i> Pending
                            </a>
                            <a href="?status=success<?= $user_filter ? '&user_id='.$user_filter : '' ?>" class="<?= $filter === 'success' ? 'active' : '' ?>">
                                <i class="fas fa-check-circle"></i> Success
                            </a>
                            <a href="?status=failed<?= $user_filter ? '&user_id='.$user_filter : '' ?>" class="<?= $filter === 'failed' ? 'active' : '' ?>">
                                <i class="fas fa-times-circle"></i> Failed
                            </a>
                            <a href="?status=expired<?= $user_filter ? '&user_id='.$user_filter : '' ?>" class="<?= $filter === 'expired' ? 'active' : '' ?>">
                                <i class="fas fa-hourglass-end"></i> Expired
                            </a>
                        </div>
                        
                        <form method="GET" style="display: flex; gap: 10px; align-items: center;">
                            <input type="hidden" name="status" value="<?= htmlspecialchars($filter) ?>">
                            <select name="user_id" onchange="this.form.submit()">
                                <option value="">All Users</option>
                                <?php foreach ($users as $u): ?>
                                    <option value="<?= $u['id'] ?>" <?= $user_filter == $u['id'] ? 'selected' : '' ?>>
                                        <?= htmlspecialchars($u['username']) ?>
                                    </option>
                                <?php endforeach; ?>
                            </select>
                        </form>
                    </div>
                    
                    <?php if (count($transactions) > 0): ?>
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Transaction ID</th>
                                <th>User</th>
                                <th>QRIS</th>
                                <th>Customer</th>
                                <th>Amount</th>
                                <th>Admin Fee</th>
                                <th>Net</th>
                                <th>Status</th>
                                <th>Payment Time</th>
                                <th>Created</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($transactions as $trx): ?>
                            <tr>
                                <td><?= $trx['id'] ?></td>
                                <td><strong><?= htmlspecialchars($trx['transaction_id']) ?></strong></td>
                                <td><?= htmlspecialchars($trx['username']) ?></td>
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
                    <div class="empty">
                        <i class="fas fa-exchange-alt"></i>
                        <p>No transactions found</p>
                    </div>
                    <?php endif; ?>
                </div>
            </div>
        </div>
    </div>
</body>
</html>