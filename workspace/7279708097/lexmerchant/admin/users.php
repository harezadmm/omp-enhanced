<?php
require_once '../config.php';
requireLogin();

if ($_SESSION['role'] !== 'admin') {
    die('Access denied. Admin only.');
}

$error = '';
$success = '';

// Handle user actions
if (isset($_GET['action']) && isset($_GET['user_id'])) {
    $user_id = intval($_GET['user_id']);
    $action = $_GET['action'];
    
    if ($action === 'suspend') {
        $stmt = $pdo->prepare("UPDATE users SET status = 'suspended' WHERE id = ? AND role = 'user'");
        $stmt->execute([$user_id]);
        $success = 'User berhasil di-suspend';
    } elseif ($action === 'activate') {
        $stmt = $pdo->prepare("UPDATE users SET status = 'active' WHERE id = ? AND role = 'user'");
        $stmt->execute([$user_id]);
        $success = 'User berhasil diaktifkan';
    } elseif ($action === 'delete') {
        $stmt = $pdo->prepare("DELETE FROM users WHERE id = ? AND role = 'user'");
        $stmt->execute([$user_id]);
        $success = 'User berhasil dihapus';
    }
}

// Get filters
$search = $_GET['search'] ?? '';
$status_filter = $_GET['status'] ?? '';

$query = "SELECT * FROM users WHERE role = 'user'";
$params = [];

if ($search) {
    $query .= " AND (username LIKE ? OR email LIKE ? OR full_name LIKE ?)";
    $search_param = "%$search%";
    $params[] = $search_param;
    $params[] = $search_param;
    $params[] = $search_param;
}

if ($status_filter) {
    $query .= " AND status = ?";
    $params[] = $status_filter;
}

$query .= " ORDER BY created_at DESC";

$stmt = $pdo->prepare($query);
$stmt->execute($params);
$users = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Management - LexMerchant Admin</title>
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
        .alert { padding: 15px 20px; border-radius: 8px; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
        .alert.success { background: #d1fae5; color: #065f46; border-left: 4px solid #10b981; }
        .alert.error { background: #fee2e2; color: #991b1b; border-left: 4px solid #ef4444; }
        
        .section-card { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 30px; overflow: hidden; }
        .section-header { padding: 20px 25px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
        .section-header h2 { font-size: 18px; color: #1e293b; display: flex; align-items: center; gap: 10px; }
        .section-body { padding: 25px; }
        
        .filters { display: flex; gap: 15px; margin-bottom: 25px; flex-wrap: wrap; }
        .search-box { flex: 1; min-width: 250px; display: flex; gap: 10px; }
        .search-box input { flex: 1; padding: 12px 15px; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 14px; }
        .search-box input:focus { outline: none; border-color: #3b82f6; }
        .filter-select { padding: 12px 15px; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 14px; }
        
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 14px; }
        th { background: #f8fafc; font-weight: 600; color: #475569; text-transform: uppercase; font-size: 12px; }
        tbody tr:hover { background: #f8fafc; }
        
        .badge { padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block; }
        .badge.active { background: #d1fae5; color: #065f46; }
        .badge.suspended { background: #fee2e2; color: #991b1b; }
        .badge.pending { background: #fef3c7; color: #92400e; }
        
        .btn { padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block; transition: all 0.3s; border: none; cursor: pointer; }
        .btn-primary { background: #3b82f6; color: white; }
        .btn-primary:hover { background: #2563eb; }
        .btn-success { background: #10b981; color: white; }
        .btn-success:hover { background: #059669; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-danger:hover { background: #dc2626; }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        
        .actions { display: flex; gap: 8px; }
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
            <a href="users.php" class="menu-item active">
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
            <h1>User Management</h1>
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
            <?php if ($error): ?>
                <div class="alert error">
                    <i class="fas fa-exclamation-circle"></i>
                    <?= htmlspecialchars($error) ?>
                </div>
            <?php endif; ?>
            
            <?php if ($success): ?>
                <div class="alert success">
                    <i class="fas fa-check-circle"></i>
                    <?= htmlspecialchars($success) ?>
                </div>
            <?php endif; ?>
            
            <div class="section-card">
                <div class="section-header">
                    <h2><i class="fas fa-users"></i> All Users (<?= count($users) ?>)</h2>
                </div>
                <div class="section-body">
                    <form method="GET" class="filters">
                        <div class="search-box">
                            <input type="text" name="search" placeholder="Search by username, email, or name..." value="<?= htmlspecialchars($search) ?>">
                            <button type="submit" class="btn btn-primary">Search</button>
                        </div>
                        <select name="status" class="filter-select" onchange="this.form.submit()">
                            <option value="">All Status</option>
                            <option value="active" <?= $status_filter === 'active' ? 'selected' : '' ?>>Active</option>
                            <option value="suspended" <?= $status_filter === 'suspended' ? 'selected' : '' ?>>Suspended</option>
                            <option value="pending" <?= $status_filter === 'pending' ? 'selected' : '' ?>>Pending</option>
                        </select>
                    </form>
                    
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Username</th>
                                <th>Email</th>
                                <th>Full Name</th>
                                <th>Balance</th>
                                <th>GoPay Setup</th>
                                <th>Status</th>
                                <th>Registered</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($users as $u): ?>
                            <tr>
                                <td><?= $u['id'] ?></td>
                                <td><strong><?= htmlspecialchars($u['username']) ?></strong></td>
                                <td><?= htmlspecialchars($u['email']) ?></td>
                                <td><?= htmlspecialchars($u['full_name']) ?></td>
                                <td>Rp <?= number_format($u['balance'], 0, ',', '.') ?></td>
                                <td><?= !empty($u['gopay_merchant_id']) ? '<span class="badge active">✓ Setup</span>' : '<span class="badge pending">✗ Not Setup</span>' ?></td>
                                <td><span class="badge <?= $u['status'] ?>"><?= strtoupper($u['status']) ?></span></td>
                                <td><?= date('d/m/Y H:i', strtotime($u['created_at'])) ?></td>
                                <td class="actions">
                                    <a href="user_detail.php?id=<?= $u['id'] ?>" class="btn btn-primary btn-sm">Detail</a>
                                    <?php if ($u['status'] === 'active'): ?>
                                        <a href="?action=suspend&user_id=<?= $u['id'] ?>" class="btn btn-danger btn-sm" onclick="return confirm('Suspend user ini?')">Suspend</a>
                                    <?php else: ?>
                                        <a href="?action=activate&user_id=<?= $u['id'] ?>" class="btn btn-success btn-sm" onclick="return confirm('Aktifkan user ini?')">Activate</a>
                                    <?php endif; ?>
                                </td>
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