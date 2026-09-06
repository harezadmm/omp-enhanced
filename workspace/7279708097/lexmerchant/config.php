<?php
// LexMerchant Configuration
define('DB_HOST', 'localhost');
define('DB_NAME', 'lexmerchant');
define('DB_USER', 'root');
define('DB_PASS', '');

define('SITE_NAME', 'LexMerchant');
define('SITE_URL', 'https://yourdomain.com');
define('API_VERSION', 'v1');

// Session configuration
ini_set('session.cookie_httponly', 1);
session_start();

// Database connection
try {
    $pdo = new PDO("mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4", DB_USER, DB_PASS);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
} catch(PDOException $e) {
    die("Database connection failed: " . $e->getMessage());
}

// Helper functions
function generateApiKey() {
    return 'lex_' . bin2hex(random_bytes(32));
}

function generateTransactionId() {
    return 'TRX' . date('YmdHis') . rand(1000, 9999);
}

function jsonResponse($data, $status = 200) {
    http_response_code($status);
    header('Content-Type: application/json');
    echo json_encode($data);
    exit;
}

function isLoggedIn() {
    return isset($_SESSION['user_id']);
}

function requireLogin() {
    if (!isLoggedIn()) {
        header('Location: login.php');
        exit;
    }
}

function hashPassword($password) {
    return password_hash($password, PASSWORD_BCRYPT);
}

function verifyPassword($password, $hash) {
    return password_verify($password, $hash);
}
?>