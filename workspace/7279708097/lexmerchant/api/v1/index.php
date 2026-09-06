<?php
require_once '../../config.php';

header('Content-Type: application/json');

// Authentication
function authenticateRequest() {
    global $pdo;
    
    $headers = getallheaders();
    $api_key = $headers['X-API-Key'] ?? $_GET['api_key'] ?? '';
    $api_secret = $headers['X-API-Secret'] ?? $_GET['api_secret'] ?? '';
    
    if (empty($api_key) || empty($api_secret)) {
        jsonResponse(['error' => 'Missing API credentials'], 401);
    }
    
    $stmt = $pdo->prepare("SELECT * FROM users WHERE api_key = ? AND api_secret = ? AND status = 'active'");
    $stmt->execute([$api_key, $api_secret]);
    $user = $stmt->fetch();
    
    if (!$user) {
        jsonResponse(['error' => 'Invalid API credentials'], 401);
    }
    
    return $user;
}

// Log API request
function logApiRequest($user_id, $api_key, $endpoint, $method, $request_body, $response_code, $response_body, $exec_time) {
    global $pdo;
    
    $stmt = $pdo->prepare("
        INSERT INTO api_logs (user_id, api_key, endpoint, method, request_body, response_code, response_body, ip_address, execution_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ");
    $stmt->execute([
        $user_id,
        $api_key,
        $endpoint,
        $method,
        $request_body,
        $response_code,
        $response_body,
        $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0',
        $exec_time
    ]);
}

$start_time = microtime(true);
$method = $_SERVER['REQUEST_METHOD'];
$endpoint = $_SERVER['REQUEST_URI'];
$request_body = file_get_contents('php://input');
$user = authenticateRequest();

// Route handling
$path = parse_url($endpoint, PHP_URL_PATH);
$segments = array_filter(explode('/', $path));

// GET /api/v1/ - API Info
if ($method === 'GET' && count($segments) === 2) {
    $response = [
        'name' => 'LexMerchant API',
        'version' => API_VERSION,
        'status' => 'active',
        'user' => [
            'id' => $user['id'],
            'username' => $user['username'],
            'balance' => floatval($user['balance'])
        ],
        'endpoints' => [
            'GET /qris' => 'List all QRIS codes',
            'POST /qris' => 'Create new QRIS',
            'GET /qris/{id}' => 'Get QRIS detail',
            'POST /transaction/create' => 'Create transaction',
            'POST /transaction/check' => 'Check transaction status',
            'GET /transactions' => 'List transactions'
        ]
    ];
    
    $exec_time = microtime(true) - $start_time;
    logApiRequest($user['id'], $user['api_key'], $endpoint, $method, '', 200, json_encode($response), $exec_time);
    jsonResponse($response);
}

// GET /api/v1/qris - List QRIS
if ($method === 'GET' && in_array('qris', $segments) && count($segments) === 3) {
    $stmt = $pdo->prepare("SELECT * FROM qris_codes WHERE user_id = ? ORDER BY created_at DESC");
    $stmt->execute([$user['id']]);
    $qris_list = $stmt->fetchAll();
    
    $response = [
        'success' => true,
        'total' => count($qris_list),
        'data' => $qris_list
    ];
    
    $exec_time = microtime(true) - $start_time;
    logApiRequest($user['id'], $user['api_key'], $endpoint, $method, '', 200, json_encode($response), $exec_time);
    jsonResponse($response);
}

// POST /api/v1/qris - Create QRIS
if ($method === 'POST' && in_array('qris', $segments) && count($segments) === 3) {
    $data = json_decode($request_body, true);
    
    $qris_name = $data['qris_name'] ?? '';
    $qris_code = $data['qris_code'] ?? '';
    $amount = floatval($data['amount'] ?? 0);
    $callback_url = $data['callback_url'] ?? '';
    
    if (empty($qris_name) || empty($qris_code)) {
        $exec_time = microtime(true) - $start_time;
        logApiRequest($user['id'], $user['api_key'], $endpoint, $method, $request_body, 400, 'Missing required fields', $exec_time);
        jsonResponse(['error' => 'Missing required fields: qris_name, qris_code'], 400);
    }
    
    $stmt = $pdo->prepare("
        INSERT INTO qris_codes (user_id, qris_name, qris_code, amount, callback_url, merchant_id, terminal_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ");
    $stmt->execute([
        $user['id'],
        $qris_name,
        $qris_code,
        $amount,
        $callback_url,
        $user['gopay_merchant_id'],
        $user['gopay_terminal_id']
    ]);
    
    $qris_id = $pdo->lastInsertId();
    
    $response = [
        'success' => true,
        'message' => 'QRIS created successfully',
        'qris_id' => $qris_id
    ];
    
    $exec_time = microtime(true) - $start_time;
    logApiRequest($user['id'], $user['api_key'], $endpoint, $method, $request_body, 200, json_encode($response), $exec_time);
    jsonResponse($response);
}

// POST /api/v1/transaction/create - Create Transaction
if ($method === 'POST' && in_array('transaction', $segments) && in_array('create', $segments)) {
    $data = json_decode($request_body, true);
    
    $qris_id = intval($data['qris_id'] ?? 0);
    $amount = floatval($data['amount'] ?? 0);
    $customer_name = $data['customer_name'] ?? '';
    
    if ($qris_id <= 0 || $amount <= 0) {
        $exec_time = microtime(true) - $start_time;
        logApiRequest($user['id'], $user['api_key'], $endpoint, $method, $request_body, 400, 'Invalid data', $exec_time);
        jsonResponse(['error' => 'Invalid qris_id or amount'], 400);
    }
    
    // Verify QRIS belongs to user
    $stmt = $pdo->prepare("SELECT * FROM qris_codes WHERE id = ? AND user_id = ?");
    $stmt->execute([$qris_id, $user['id']]);
    $qris = $stmt->fetch();
    
    if (!$qris) {
        $exec_time = microtime(true) - $start_time;
        logApiRequest($user['id'], $user['api_key'], $endpoint, $method, $request_body, 404, 'QRIS not found', $exec_time);
        jsonResponse(['error' => 'QRIS not found'], 404);
    }
    
    // Get admin fee setting
    $stmt = $pdo->prepare("SELECT setting_value FROM settings WHERE setting_key = 'admin_fee_percentage'");
    $stmt->execute();
    $admin_fee_pct = floatval($stmt->fetchColumn() ?? 1.5);
    
    $admin_fee = $amount * ($admin_fee_pct / 100);
    $net_amount = $amount - $admin_fee;
    
    $transaction_id = generateTransactionId();
    
    $stmt = $pdo->prepare("
        INSERT INTO transactions (transaction_id, qris_id, user_id, amount, admin_fee, net_amount, customer_name, ip_address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ");
    $stmt->execute([
        $transaction_id,
        $qris_id,
        $user['id'],
        $amount,
        $admin_fee,
        $net_amount,
        $customer_name,
        $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0'
    ]);
    
    $response = [
        'success' => true,
        'transaction_id' => $transaction_id,
        'amount' => $amount,
        'admin_fee' => $admin_fee,
        'net_amount' => $net_amount,
        'status' => 'pending',
        'qris_code' => $qris['qris_code']
    ];
    
    $exec_time = microtime(true) - $start_time;
    logApiRequest($user['id'], $user['api_key'], $endpoint, $method, $request_body, 200, json_encode($response), $exec_time);
    jsonResponse($response);
}

// POST /api/v1/transaction/check - Check Transaction Status
if ($method === 'POST' && in_array('transaction', $segments) && in_array('check', $segments)) {
    $data = json_decode($request_body, true);
    $transaction_id = $data['transaction_id'] ?? '';
    
    if (empty($transaction_id)) {
        $exec_time = microtime(true) - $start_time;
        logApiRequest($user['id'], $user['api_key'], $endpoint, $method, $request_body, 400, 'Missing transaction_id', $exec_time);
        jsonResponse(['error' => 'Missing transaction_id'], 400);
    }
    
    $stmt = $pdo->prepare("SELECT * FROM transactions WHERE transaction_id = ? AND user_id = ?");
    $stmt->execute([$transaction_id, $user['id']]);
    $transaction = $stmt->fetch();
    
    if (!$transaction) {
        $exec_time = microtime(true) - $start_time;
        logApiRequest($user['id'], $user['api_key'], $endpoint, $method, $request_body, 404, 'Transaction not found', $exec_time);
        jsonResponse(['error' => 'Transaction not found'], 404);
    }
    
    $response = [
        'success' => true,
        'transaction_id' => $transaction['transaction_id'],
        'amount' => floatval($transaction['amount']),
        'status' => $transaction['payment_status'],
        'payment_time' => $transaction['payment_time'],
        'reference_id' => $transaction['reference_id']
    ];
    
    $exec_time = microtime(true) - $start_time;
    logApiRequest($user['id'], $user['api_key'], $endpoint, $method, $request_body, 200, json_encode($response), $exec_time);
    jsonResponse($response);
}

// Default 404
$exec_time = microtime(true) - $start_time;
logApiRequest($user['id'], $user['api_key'], $endpoint, $method, $request_body, 404, 'Endpoint not found', $exec_time);
jsonResponse(['error' => 'Endpoint not found'], 404);
?>