<?php
require_once '../config.php';
requireLogin();

if ($_SESSION['role'] !== 'admin') {
    die('Access denied. Admin only.');
}

// Get statistics
$stmt = $pdo->query("SELECT COUNT(*) as total FROM users WHERE role = 'user'");
$total_users = $stmt->fetch()['total'];

$stmt = $pdo->query("SELECT COUNT(*) as total FROM users WHERE role = 'user' AND status = 'active'");
$active_users = $stmt->fetch()['total'];

$stmt = $pdo->query("SELECT COUNT(*) as total FROM qris_codes WHERE status = 'active'");
$total_qris = $stmt->fetch()['total'];

$stmt = $pdo->query("SELECT COUNT(*) as total FROM transactions");
$total_transactions = $stmt->fetch()['total'];

$stmt = $pdo->query("SELECT COUNT(*) as total FROM transactions WHERE payment_status = 'success'");
$success_transactions = $stmt->fetch()['total'];

$stmt = $pdo->query("SELECT COUNT(*) as total FROM transactions WHERE payment_status = 'pending'");
$pending_transactions = $stmt->fetch()['total'];

$stmt = $pdo->query("SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE payment_status = 'success'");
$total_revenue = $stmt->fetch()['total'];

$stmt = $pdo->query("SELECT COALESCE(SUM(admin_fee), 0) as total FROM transactions WHERE payment_status = 'success'");
$total_admin_fee = $stmt->fetch()['total'];

$stmt = $pdo->query("SELECT COUNT(*) as total FROM transactions WHERE payment_status = 'success' AND DATE(payment_time) = CURDATE()");
$today_transactions = $stmt->fetch()['total'];

$stmt = $pdo->query("SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE payment_status = 'success' AND DATE(payment_time) = CURDATE()");
$today_revenue = $stmt->fetch()['total'];

// Recent users
$stmt = $pdo->query("SELECT * FROM users WHERE role = 'user' ORDER BY created_at DESC LIMIT 5");
$recent_users = $stmt->fetchAll();

// Recent transactions
$stmt = $pdo->query("
    SELECT t.*, u.username, q.qris_name
    FROM transactions t
    JOIN users u ON t.user_id = u.id
    JOIN qris_codes q ON t.qris_id = q.id
    ORDER BY t.created_at DESC
    LIMIT 10
");
$recent_transactions = $stmt->fetchAll();

// Transaction chart data (last 7 days)
$stmt = $pdo->query("
    SELECT 
        DATE(created_at) as date,
        COUNT(*) as total,
        COUNT(CASE WHEN payment_status = 'success' THEN 1 END) as success,
        COALESCE(SUM(CASE WHEN payment_status = 'success' THEN amount ELSE 0 END), 0) as revenue
    FROM transactions
    WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
    GROUP BY DATE(created_at)
    ORDER BY date ASC
");
$chart_data = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - LexMerchant</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; }
        
        /* Sidebar */
        .sidebar { position: fixed; left: 0; top: 0; bottom: 0; width: 260px; background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%); color: white; overflow-y: auto; z-index: 1000; }
        .sidebar-header { padding: 25px 20px; background: rgba(255,255,255,0.05); border-bottom: 1px solid rgba(255,255,255,0.1); }
        .sidebar-header h2 { font-size: 22px; display: flex; align-items: center; gap: 10px; }
        .sidebar-menu { padding: 20px 0; }
        .menu-item { display: flex; align-items: center; gap: 12px; padding: 14px 25px; color: rgba(255,255,255,0.8); text-decoration: none; transition: all 0.3s; border-left: 3px solid transparent; }
        .menu-item:hover, .menu-item.active { background: rgba(255,255,255,0.1); color: white; border-left-color: #3b82f6; }
        .menu-item i { width: 20px; font-size: 16px; }
        
        /* Main Content */
        .main-content { margin-left: 260px; min-height: 100vh; }
        .topbar { background: white; padding: 15px 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }
        .topbar h1 { font-size: 24px; color: #1e293b; }
        .topbar-right { display: flex; align-items: center; gap: 20px; }
        .user-info { display: flex; align-items: center; gap: 10px; }
        .user-avatar { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; }
        .btn-logout { padding: 8px 16px; background: #ef4444; color: white; text-decoration: none; border-radius: 6px; font-size: 14px; transition: background 0.3s; }
        .btn-logout:hover { background: #dc2626; }
        
        .container { padding: 30px; }
        
        /* Stats Grid */
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); position: relative; overflow: hidden; }
        .stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; }
        .stat-card.primary::before { background: linear-gradient(90deg, #3b82f6, #2563eb); }
        .stat-card.success::before { background: linear-gradient(90deg, #10b981, #059669); }
        .stat-card.warning::before { background: linear-gradient(90deg, #f59e0b, #d97706); }
        .stat-card.danger::before { background: linear-gradient(90deg, #ef4444, #dc2626); }
        .stat-card.info::before { background: linear-gradient(90deg, #06b6d4, #0891b2); }
        .stat-icon { width: 50px; height: 50px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px; margin-bottom: 15px; }
        .stat-card.primary .stat-icon { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
        .stat-card.success .stat-icon { background: rgba(16, 185, 129, 0.1); color: #10b981; }
        .stat-card.warning .stat-icon { background: rgba(245, 158, 11, 0.1); color: #f59e0b; }
        .stat-card.danger .stat-icon { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
        .stat-card.info .stat-icon { background: rgba(6, 182, 212, 0.1); color: #06b6d4; }
        .stat-label { color: #64748b; font-size: 13px; text-transform: uppercase; font-weight: 600; margin-bottom: 8px; }
        .stat-value { font-size: 28px; font-weight: bold; color: #1e293b; }
        .stat-change { font-size: 13px; margin-top: 8px; }
        .stat-change.up { color: #10b981; }
        .stat-change.down { color: #ef4444; }
        
        /* Section Card */
        .section-card { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 30px; overflow: hidden; }
        .section-header { padding: 20px 25px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
        .section-header h2 { font-size: 18px; color: #1e293b; display: flex; align-items: center; gap: 10px; }
        .section-body { padding: 25px; }
        
        /* Table */
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 14px; }
        th { background: #f8fafc; font-weight: 600; color: #475569; text-transform: uppercase; font-size: 12px; }
        tbody tr:hover { background: #f8fafc; }
        
        /* Badge */
        .badge { padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block; }
        .badge.success { background: #d1fae5; color: #065f46; }
        .badge.pending { background: #fef3c7; color: #92400e; }
        .badge.failed { background: #fee2e2; color: #991b1b; }
        .badge.active { background: #dbeafe; color: #1e40af; }
        .badge.suspended { background: #fee2e2; color: #991b1b; }
        
        /* Button */
        .btn { padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block; transition: all 0.3s; border: none; cursor: pointer; }
        .btn-primary { background: #3b82f6; color: white; }
        .btn-primary:hover { background: #2563eb; }
        .btn-success { background: #10b981; color: white; }
        .btn-success:hover { background: #059669; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-danger:hover { background: #dc2626; }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        
        /* Empty State */
        .empty-state { text-align: center; padding: 60px 20px; color: #94a3b8; }
        .empty-state i { font-size: 48px; margin-bottom: 15px; opacity: 0.5; }
        
        /* Chart Container */
        .chart-container { height: 300px; }
    </style>
</head>
<body>
    <!-- Sidebar -->
    <div class="sidebar">
        <div class="sidebar-header">
            <h2><i class="fas fa-rocket"></i> LexMerchant</h2>
        </div>
        <div class="sidebar-menu">
            <a href="index.php" class="menu-item active">
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
    
    <!-- Main Content -->
    <div class="main-content">
        <!-- Topbar -->
        <div class="topbar">
            <h1>Admin Dashboard</h1>
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
        
        <!-- Container -->
        <div class="container">
            <!-- Stats Grid -->
            <div class="stats-grid">
                <div class="stat-card primary">
                    <div class="stat-icon"><i class="fas fa-users"></i></div>
                    <div class="stat-label">Total Users</div>
                    <div class="stat-value"><?= number_format($total_users) ?></div>
                    <div class="stat-change up"><i class="fas fa-arrow-up"></i> <?= $active_users ?> active</div>
                </div>
                
                <div class="stat-card info">
                    <div class="stat-icon"><i class="fas fa-qrcode"></i></div>
                    <div class="stat-label">Active QRIS</div>
                    <div class="stat-value"><?= number_format($total_qris) ?></div>
                </div>
                
                <div class="stat-card success">
                    <div class="stat-icon"><i class="fas fa-check-circle"></i></div>
                    <div class="stat-label">Success Transactions</div>
                    <div class="stat-value"><?= number_format($success_transactions) ?></div>
                    <div class="stat-change"><i class="fas fa-clock"></i> <?= $pending_transactions ?> pending</div>
                </div>
                
                <div class="stat-card warning">
                    <div class="stat-icon"><i class="fas fa-money-bill-wave"></i></div>
                    <div class="stat-label">Total Revenue</div>
                    <div class="stat-value">Rp <?= number_format($total_revenue, 0, ',', '.') ?></div>
                </div>
                
                <div class="stat-card danger">
                    <div class="stat-icon"><i class="fas fa-coins"></i></div>
                    <div class="stat-label">Admin Fee Collected</div>
                    <div class="stat-value">Rp <?= number_format($total_admin_fee, 0, ',', '.') ?></div>
                </div>
                
                <div class="stat-card success">
                    <div class="stat-icon"><i class="fas fa-calendar-day"></i></div>
                    <div class="stat-label">Today's Revenue</div>
                    <div class="stat-value">Rp <?= number_format($today_revenue, 0, ',', '.') ?></div>
                    <div class="stat-change up"><i class="fas fa-arrow-up"></i> <?= $today_transactions ?> transactions</div>
                </div>
            </div>
            
            <!-- Recent Users -->
            <div class="section-card">
                <div class="section-header">
                    <h2><i class="fas fa-user-plus"></i> Recent Users</h2>
                    <a href="users.php" class="btn btn-primary btn-sm">View All</a>
                </div>
                <div class="section-body">
                    <?php if (count($recent_users) > 0): ?>
                    <table>
                        <thead>
                            <tr>
                                <th>Username</th>
                                <th>Email</th>
                                <th>Full Name</th>
                                <th>Balance</th>
                                <th>Status</th>
                                <th>Registered</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($recent_users as $u): ?>
                            <tr>
                                <td><strong><?= htmlspecialchars($u['username']) ?></strong></td>
                                <td><?= htmlspecialchars($u['email']) ?></td>
                                <td><?= htmlspecialchars($u['full_name']) ?></td>
                                <td>Rp <?= number_format($u['balance'], 0, ',', '.') ?></td>
                                <td><span class="badge <?= $u['status'] ?>"><?= strtoupper($u['status']) ?></span></td>
                                <td><?= date('d/m/Y H:i', strtotime($u['created_at'])) ?></td>
                                <td><a href="user_detail.php?id=<?= $u['id'] ?>" class="btn btn-primary btn-sm">View</a></td>
                            </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                    <?php else: ?>
                    <div class="empty-state">
                        <i class="fas fa-users"></i>
                        <p>No users yet</p>
                    </div>
                    <?php endif; ?>
                </div>
            </div>
            
            <!-- Recent Transactions -->
            <div class="section-card">
                <div class="section-header">
                    <h2><i class="fas fa-exchange-alt"></i> Recent Transactions</h2>
                    <a href="transactions.php" class="btn btn-primary btn-sm">View All</a>
                </div>
                <div class="section-body">
                    <?php if (count($recent_transactions) > 0): ?>
                    <table>
                        <thead>
                            <tr>
                                <th>Transaction ID</th>
                                <th>User</th>
                                <th>QRIS</th>
                                <th>Amount</th>
                                <th>Admin Fee</th>
                                <th>Status</th>
                                <th>Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($recent_transactions as $trx): ?>
                            <tr>
                                <td><strong><?= htmlspecialchars($trx['transaction_id']) ?></strong></td>
                                <td><?= htmlspecialchars($trx['username']) ?></td>
                                <td><?= htmlspecialchars($trx['qris_name']) ?></td>
                                <td>Rp <?= number_format($trx['amount'], 0, ',', '.') ?></td>
                                <td>Rp <?= number_format($trx['admin_fee'], 0, ',', '.') ?></td>
                                <td><span class="badge <?= $trx['payment_status'] ?>"><?= strtoupper($trx['payment_status']) ?></span></td>
                                <td><?= date('d/m/Y H:i', strtotime($trx['created_at'])) ?></td>
                            </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                    <?php else: ?>
                    <div class="empty-state">
                        <i class="fas fa-exchange-alt"></i>
                        <p>No transactions yet</p>
                    </div>
                    <?php endif; ?>
                </div>
            </div>
        </div>
    </div>
</body>
</html>