<?php
require_once 'config.php';
requireLogin();

$user_id = $_SESSION['user_id'];

$stmt = $pdo->prepare("SELECT api_key, api_secret FROM users WHERE id = ?");
$stmt->execute([$user_id]);
$user = $stmt->fetch();
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Documentation - LexMerchant</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; }
        .navbar { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .navbar h2 { font-size: 24px; }
        .navbar a { color: white; text-decoration: none; padding: 8px 16px; background: rgba(255,255,255,0.2); border-radius: 5px; transition: background 0.3s; margin-left: 10px; }
        .navbar a:hover { background: rgba(255,255,255,0.3); }
        .container { padding: 30px; max-width: 1200px; margin: 0 auto; }
        .section { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .section h2 { margin-bottom: 15px; color: #333; }
        .section p { color: #666; line-height: 1.6; margin-bottom: 15px; }
        .credentials { background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; margin: 15px 0; }
        .credentials p { margin: 8px 0; font-family: monospace; }
        .credentials code { background: #e0e0e0; padding: 4px 8px; border-radius: 4px; }
        .endpoint { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #16a34a; }
        .endpoint h3 { color: #333; margin-bottom: 10px; }
        .endpoint .method { display: inline-block; padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 12px; margin-right: 10px; }
        .method.get { background: #3b82f6; color: white; }
        .method.post { background: #10b981; color: white; }
        .endpoint pre { background: #1e293b; color: #e2e8f0; padding: 15px; border-radius: 6px; overflow-x: auto; margin: 10px 0; font-size: 13px; }
        .endpoint code { font-family: 'Courier New', monospace; }
        h4 { color: #333; margin: 15px 0 10px 0; }
    </style>
</head>
<body>
    <div class="navbar">
        <h2>🚀 LexMerchant</h2>
        <div>
            <a href="dashboard.php">Dashboard</a>
            <a href="qris.php">QRIS</a>
            <a href="transactions.php">Transaksi</a>
            <a href="logout.php">Logout</a>
        </div>
    </div>
    
    <div class="container">
        <div class="section">
            <h2>🔑 API Credentials</h2>
            <p>Gunakan credentials berikut untuk autentikasi API request Anda:</p>
            
            <div class="credentials">
                <p><strong>API Key:</strong> <code><?= htmlspecialchars($user['api_key']) ?></code></p>
                <p><strong>API Secret:</strong> <code><?= htmlspecialchars($user['api_secret']) ?></code></p>
                <p><strong>Base URL:</strong> <code><?= SITE_URL ?>/api/v1/</code></p>
            </div>
            
            <p><strong>Authentication:</strong> Kirim credentials via HTTP headers atau query parameters:</p>
            <div class="credentials">
                <p>Headers: <code>X-API-Key</code> dan <code>X-API-Secret</code></p>
                <p>Query: <code>?api_key=xxx&api_secret=yyy</code></p>
            </div>
        </div>
        
        <div class="section">
            <h2>📚 API Endpoints</h2>
            
            <div class="endpoint">
                <h3><span class="method get">GET</span> /api/v1/</h3>
                <p>Get API info dan available endpoints</p>
                <h4>Example Request:</h4>
                <pre><code>curl -X GET "<?= SITE_URL ?>/api/v1/" \
  -H "X-API-Key: <?= htmlspecialchars($user['api_key']) ?>" \
  -H "X-API-Secret: <?= htmlspecialchars($user['api_secret']) ?>"</code></pre>
            </div>
            
            <div class="endpoint">
                <h3><span class="method get">GET</span> /api/v1/qris</h3>
                <p>List semua QRIS codes milik Anda</p>
                <h4>Example Request:</h4>
                <pre><code>curl -X GET "<?= SITE_URL ?>/api/v1/qris" \
  -H "X-API-Key: <?= htmlspecialchars($user['api_key']) ?>" \
  -H "X-API-Secret: <?= htmlspecialchars($user['api_secret']) ?>"</code></pre>
            </div>
            
            <div class="endpoint">
                <h3><span class="method post">POST</span> /api/v1/qris</h3>
                <p>Create QRIS baru</p>
                <h4>Request Body:</h4>
                <pre><code>{
  "qris_name": "QRIS Toko A",
  "qris_code": "00020101021226...",
  "amount": 10000,
  "callback_url": "https://yourdomain.com/webhook"
}</code></pre>
                <h4>Example Request:</h4>
                <pre><code>curl -X POST "<?= SITE_URL ?>/api/v1/qris" \
  -H "X-API-Key: <?= htmlspecialchars($user['api_key']) ?>" \
  -H "X-API-Secret: <?= htmlspecialchars($user['api_secret']) ?>" \
  -H "Content-Type: application/json" \
  -d '{"qris_name":"QRIS Test","qris_code":"00020101..."}'</code></pre>
            </div>
            
            <div class="endpoint">
                <h3><span class="method post">POST</span> /api/v1/transaction/create</h3>
                <p>Create transaksi baru</p>
                <h4>Request Body:</h4>
                <pre><code>{
  "qris_id": 1,
  "amount": 50000,
  "customer_name": "John Doe"
}</code></pre>
                <h4>Response:</h4>
                <pre><code>{
  "success": true,
  "transaction_id": "TRX20260903001234",
  "amount": 50000,
  "admin_fee": 750,
  "net_amount": 49250,
  "status": "pending",
  "qris_code": "00020101..."
}</code></pre>
            </div>
            
            <div class="endpoint">
                <h3><span class="method post">POST</span> /api/v1/transaction/check</h3>
                <p>Check status transaksi</p>
                <h4>Request Body:</h4>
                <pre><code>{
  "transaction_id": "TRX20260903001234"
}</code></pre>
                <h4>Response:</h4>
                <pre><code>{
  "success": true,
  "transaction_id": "TRX20260903001234",
  "amount": 50000,
  "status": "success",
  "payment_time": "2026-09-03 19:30:00",
  "reference_id": "GP123456789"
}</code></pre>
            </div>
        </div>
        
        <div class="section">
            <h2>📝 Webhook Callback</h2>
            <p>Jika Anda set <code>callback_url</code> pada QRIS, sistem akan mengirim POST request ke URL tersebut setiap ada perubahan status transaksi:</p>
            
            <h4>Webhook Payload:</h4>
            <pre style="background: #1e293b; color: #e2e8f0; padding: 15px; border-radius: 6px; overflow-x: auto;"><code>{
  "event": "transaction.success",
  "transaction_id": "TRX20260903001234",
  "qris_id": 1,
  "amount": 50000,
  "admin_fee": 750,
  "net_amount": 49250,
  "customer_name": "John Doe",
  "payment_status": "success",
  "payment_time": "2026-09-03 19:30:00",
  "reference_id": "GP123456789"
}</code></pre>
        </div>
    </div>
</body>
</html>