<?php
require_once '../config.php';
requireLogin();

if ($_SESSION['role'] !== 'admin') {
    die('Access denied. Admin only.');
}

// Get API logs with pagination
$page = isset($_GET['page']) ? max(1, intval($_GET['page'])) : 1;
$per_page = 50;
$offset = ($page - 1) * $per_page;

$stmt = $pdo->query("SELECT COUNT(*) FROM api_logs");
$total_logs = $stmt->fetchColumn();
$total_pages = ceil($total_logs / $per_page);

$query = "
    SELECT l.*, u.username
    FROM api_logs l
    LEFT JOIN users u ON l.user_id = u.id
    ORDER BY l.created_at DESC
    LIMIT $per_page OFFSET $offset
";
$stmt = $pdo->query($query);
$logs = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Logs - LexMerchant Admin</title>
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
        
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #e2e8f0; }
        th { background: #f8fafc; font-weight: 600; color: #475569; text-transform: uppercase; font-size: 11px; }
        tbody tr:hover { background: #f8fafc; }
        
        .badge { padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; display: inline-block; }
        .badge.success { background: #d1fae5; color: #065f46; }
        .badge.error { background: #fee2e2; color: #991b1b; }
        .badge.get { background: #dbeafe; color: #1e40af; }
        .badge.post { background: #d1fae5; color: #065f46; }
        
        .pagination { display: flex; gap: 10px; justify-content: center; margin-top: 20px; }
        .pagination a { padding: 8px 16px; background: white; border: 1px solid #e2e8f0; border-radius: 6px; text-decoration: none; color: #1e293b; }
        .pagination a:hover, .pagination a.active { background: #3b82f6; color: white; border-color: #3b82f6; }
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
            <a href="transactions.php" class="menu-item">
                <i class="fas fa-exchange-alt"></i>
                <span>Transactions</span>
            </a>
            <a href="api_logs.php" class="menu-item active">
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
            <h1>API Logs</h1>
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
                    <h2><i class="fas fa-file-alt"></i> API Request Logs (<?= number_format($total_logs) ?> total)</h2>
                </div>
                <div class="section-body">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>User</th>
                                <th>Method</th>
                                <th>Endpoint</th>
                                <th>Response</th>
                                <th>Exec Time</th>
                                <th>IP Address</th>
                                <th>Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($logs as $log): ?>
                            <tr>
                                <td><?= $log['id'] ?></td>
                                <td><?= htmlspecialchars($log['username'] ?? 'N/A') ?></td>
                                <td><span class="badge <?= strtolower($log['method']) ?>"><?= htmlspecialchars($log['method']) ?></span></td>
                                <td><small><?= htmlspecialchars($log['endpoint']) ?></small></td>
                                <td><span class="badge <?= $log['response_code'] >= 200 && $log['response_code'] < 300 ? 'success' : 'error' ?>"><?= $log['response_code'] ?></span></td>
                                <td><?= number_format($log['execution_time'], 3) ?>s</td>
                                <td><small><?= htmlspecialchars($log['ip_address']) ?></small></td>
                                <td><small><?= date('d/m/Y H:i:s', strtotime($log['created_at'])) ?></small></td>
                            </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                    
                    <?php if ($total_pages > 1): ?>
                    <div class="pagination">
                        <?php if ($page > 1): ?>
                            <a href="?page=<?= $page - 1 ?>">← Previous</a>
                        <?php endif; ?>
                        
                        <?php for ($i = max(1, $page - 2); $i <= min($total_pages, $page + 2); $i++): ?>
                            <a href="?page=<?= $i ?>" class="<?= $i === $page ? 'active' : '' ?>"><?= $i ?></a>
                        <?php endfor; ?>
                        
                        <?php if ($page < $total_pages): ?>
                            <a href="?page=<?= $page + 1 ?>">Next →</a>
                        <?php endif; ?>
                    </div>
                    <?php endif; ?>
                </div>
            </div>
        </div>
    </div>
</body>
</html>