<?php
require_once '../config.php';
requireLogin();

if ($_SESSION['role'] !== 'admin') {
    die('Access denied. Admin only.');
}

$error = '';
$success = '';

// Handle settings update
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    foreach ($_POST as $key => $value) {
        if (strpos($key, 'setting_') === 0) {
            $setting_key = str_replace('setting_', '', $key);
            $stmt = $pdo->prepare("UPDATE settings SET setting_value = ? WHERE setting_key = ?");
            $stmt->execute([$value, $setting_key]);
        }
    }
    $success = 'Settings berhasil disimpan!';
}

// Get all settings
$stmt = $pdo->query("SELECT * FROM settings ORDER BY setting_key");
$settings = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Settings - LexMerchant Admin</title>
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
        
        .container { padding: 30px; max-width: 900px; }
        .alert { padding: 15px 20px; border-radius: 8px; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
        .alert.success { background: #d1fae5; color: #065f46; border-left: 4px solid #10b981; }
        .alert.error { background: #fee2e2; color: #991b1b; border-left: 4px solid #ef4444; }
        
        .section-card { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 30px; overflow: hidden; }
        .section-header { padding: 20px 25px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
        .section-header h2 { font-size: 18px; color: #1e293b; display: flex; align-items: center; gap: 10px; }
        .section-body { padding: 25px; }
        
        .form-group { margin-bottom: 25px; padding-bottom: 25px; border-bottom: 1px solid #e2e8f0; }
        .form-group:last-child { border-bottom: none; }
        label { display: block; margin-bottom: 8px; color: #1e293b; font-weight: 600; font-size: 14px; }
        .description { font-size: 13px; color: #64748b; margin-bottom: 10px; line-height: 1.5; }
        input { width: 100%; padding: 12px 15px; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 14px; font-family: monospace; transition: border-color 0.3s; }
        input:focus { outline: none; border-color: #3b82f6; }
        
        .btn { padding: 12px 24px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 600; display: inline-block; transition: all 0.3s; border: none; cursor: pointer; }
        .btn-primary { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); color: white; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4); }
        
        .setting-category { background: #f8fafc; padding: 12px 18px; border-radius: 8px; margin-bottom: 20px; }
        .setting-category h3 { font-size: 16px; color: #334155; display: flex; align-items: center; gap: 10px; }
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
            <a href="api_logs.php" class="menu-item">
                <i class="fas fa-file-alt"></i>
                <span>API Logs</span>
            </a>
            <a href="settings.php" class="menu-item active">
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
            <h1>System Settings</h1>
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
                    <h2><i class="fas fa-cog"></i> Configure System Settings</h2>
                </div>
                <div class="section-body">
                    <form method="POST">
                        <div class="setting-category">
                            <h3><i class="fas fa-dollar-sign"></i> Transaction Settings</h3>
                        </div>
                        
                        <?php 
                        $transaction_settings = ['admin_fee_percentage', 'min_transaction', 'max_transaction', 'transaction_timeout'];
                        foreach ($settings as $setting): 
                            if (in_array($setting['setting_key'], $transaction_settings)):
                        ?>
                        <div class="form-group">
                            <label><?= ucwords(str_replace('_', ' ', $setting['setting_key'])) ?></label>
                            <?php if ($setting['description']): ?>
                                <div class="description"><?= htmlspecialchars($setting['description']) ?></div>
                            <?php endif; ?>
                            <input 
                                type="text" 
                                name="setting_<?= htmlspecialchars($setting['setting_key']) ?>" 
                                value="<?= htmlspecialchars($setting['setting_value']) ?>"
                            >
                        </div>
                        <?php 
                            endif;
                        endforeach; 
                        ?>
                        
                        <div class="setting-category">
                            <h3><i class="fas fa-qrcode"></i> QRIS & Payment Settings</h3>
                        </div>
                        
                        <?php 
                        $qris_settings = ['qris_check_interval', 'gopay_merchant_id', 'gopay_api_key', 'gopay_api_secret'];
                        foreach ($settings as $setting): 
                            if (in_array($setting['setting_key'], $qris_settings)):
                        ?>
                        <div class="form-group">
                            <label><?= ucwords(str_replace('_', ' ', $setting['setting_key'])) ?></label>
                            <?php if ($setting['description']): ?>
                                <div class="description"><?= htmlspecialchars($setting['description']) ?></div>
                            <?php endif; ?>
                            <input 
                                type="<?= strpos($setting['setting_key'], 'secret') !== false || strpos($setting['setting_key'], 'api_key') !== false ? 'password' : 'text' ?>"
                                name="setting_<?= htmlspecialchars($setting['setting_key']) ?>" 
                                value="<?= htmlspecialchars($setting['setting_value']) ?>"
                            >
                        </div>
                        <?php 
                            endif;
                        endforeach; 
                        ?>
                        
                        <div class="setting-category">
                            <h3><i class="fas fa-bell"></i> Webhook Settings</h3>
                        </div>
                        
                        <?php 
                        $webhook_settings = ['webhook_retry_attempts', 'webhook_retry_delay'];
                        foreach ($settings as $setting): 
                            if (in_array($setting['setting_key'], $webhook_settings)):
                        ?>
                        <div class="form-group">
                            <label><?= ucwords(str_replace('_', ' ', $setting['setting_key'])) ?></label>
                            <?php if ($setting['description']): ?>
                                <div class="description"><?= htmlspecialchars($setting['description']) ?></div>
                            <?php endif; ?>
                            <input 
                                type="text" 
                                name="setting_<?= htmlspecialchars($setting['setting_key']) ?>" 
                                value="<?= htmlspecialchars($setting['setting_value']) ?>"
                            >
                        </div>
                        <?php 
                            endif;
                        endforeach; 
                        ?>
                        
                        <div class="setting-category">
                            <h3><i class="fas fa-wallet"></i> Withdrawal Settings</h3>
                        </div>
                        
                        <?php 
                        $withdrawal_settings = ['min_withdrawal', 'withdrawal_fee'];
                        foreach ($settings as $setting): 
                            if (in_array($setting['setting_key'], $withdrawal_settings)):
                        ?>
                        <div class="form-group">
                            <label><?= ucwords(str_replace('_', ' ', $setting['setting_key'])) ?></label>
                            <?php if ($setting['description']): ?>
                                <div class="description"><?= htmlspecialchars($setting['description']) ?></div>
                            <?php endif; ?>
                            <input 
                                type="text" 
                                name="setting_<?= htmlspecialchars($setting['setting_key']) ?>" 
                                value="<?= htmlspecialchars($setting['setting_value']) ?>"
                            >
                        </div>
                        <?php 
                            endif;
                        endforeach; 
                        ?>
                        
                        <div class="setting-category">
                            <h3><i class="fas fa-shield-alt"></i> System Settings</h3>
                        </div>
                        
                        <?php 
                        $system_settings = ['site_name', 'registration_enabled', 'maintenance_mode'];
                        foreach ($settings as $setting): 
                            if (in_array($setting['setting_key'], $system_settings)):
                        ?>
                        <div class="form-group">
                            <label><?= ucwords(str_replace('_', ' ', $setting['setting_key'])) ?></label>
                            <?php if ($setting['description']): ?>
                                <div class="description"><?= htmlspecialchars($setting['description']) ?></div>
                            <?php endif; ?>
                            <input 
                                type="text" 
                                name="setting_<?= htmlspecialchars($setting['setting_key']) ?>" 
                                value="<?= htmlspecialchars($setting['setting_value']) ?>"
                            >
                        </div>
                        <?php 
                            endif;
                        endforeach; 
                        ?>
                        
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save"></i> Save All Settings
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</body>
</html>