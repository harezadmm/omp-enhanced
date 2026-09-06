<?php
require_once '../config.php';
requireLogin();

if ($_SESSION['role'] !== 'admin') {
    die('Access denied. Admin only.');
}

// Get all QRIS from all users
$query = "
    SELECT q.*, u.username, u.email
    FROM qris_codes q
    JOIN users u ON q.user_id = u.id
    ORDER BY q.created_at DESC
";
$stmt = $pdo->query($query);
$qris_list = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>All QRIS - LexMerchant Admin</title>
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
        
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 14px; }
        th { background: #f8fafc; font-weight: 600; color: #475569; text-transform: uppercase; font-size: 12px; }
        tbody tr:hover { background: #f8fafc; }
        
        .badge { padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block; }
        .badge.active { background: #d1fae5; color: #065f46; }
        .badge.inactive { background: #fee2e2; color: #991b1b; }
        
        .qris-code { font-family: monospace; font-size: 11px; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
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
            <a href="qris.php" class="menu-item active">
                <i class="fas fa-qrcode"></i>
                <span>All QRIS</span>
            </a>
            <a href="transactions.php" class="menu-item">
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
            <h1>All QRIS</h1>
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
                    <h2><i class="fas fa-qrcode"></i> All QRIS Codes (<?= count($qris_list) ?>)</h2>
                </div>
                <div class="section-body">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>User</th>
                                <th>QRIS Name</th>
                                <th>Code</th>
                                <th>Amount</th>
                                <th>Transactions</th>
                                <th>Revenue</th>
                                <th>Status</th>
                                <th>Created</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($qris_list as $qris): ?>
                            <tr>
                                <td><?= $qris['id'] ?></td>
                                <td>
                                    <strong><?= htmlspecialchars($qris['username']) ?></strong><br>
                                    <small><?= htmlspecialchars($qris['email']) ?></small>
                                </td>
                                <td><?= htmlspecialchars($qris['qris_name']) ?></td>
                                <td><div class="qris-code" title="<?= htmlspecialchars($qris['qris_code']) ?>"><?= htmlspecialchars(substr($qris['qris_code'], 0, 20)) ?>...</div></td>
                                <td><?= $qris['amount'] > 0 ? 'Rp ' . number_format($qris['amount'], 0, ',', '.') : 'Dynamic' ?></td>
                                <td><?= number_format($qris['total_transactions']) ?></td>
                                <td>Rp <?= number_format($qris['total_revenue'], 0, ',', '.') ?></td>
                                <td><span class="badge <?= $qris['status'] ?>"><?= strtoupper($qris['status']) ?></span></td>
                                <td><?= date('d/m/Y H:i', strtotime($qris['created_at'])) ?></td>
                            </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</body>
</html>