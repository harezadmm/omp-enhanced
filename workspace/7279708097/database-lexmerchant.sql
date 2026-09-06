-- ============================================================================
-- LexMerchant Database Schema
-- Professional QRIS Payment Gateway
-- Version: 1.0
-- Date: 2026-09-03
-- ============================================================================

-- Drop database if exists (CAREFUL: THIS DELETES ALL DATA!)
-- DROP DATABASE IF EXISTS lexmerchant;

-- Create database
CREATE DATABASE IF NOT EXISTS lexmerchant CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE lexmerchant;

-- ============================================================================
-- TABLE: users
-- Stores user accounts, API credentials, and GoPay Merchant settings
-- ============================================================================
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    
    -- API Credentials (auto-generated on registration)
    api_key VARCHAR(100) UNIQUE NOT NULL,
    api_secret VARCHAR(100) NOT NULL,
    
    -- GoPay Merchant Settings (user input required)
    gopay_merchant_id VARCHAR(100) DEFAULT NULL,
    gopay_terminal_id VARCHAR(100) DEFAULT NULL,
    gopay_api_key VARCHAR(255) DEFAULT NULL,
    
    -- Account info
    balance DECIMAL(15,2) DEFAULT 0.00,
    status ENUM('active', 'suspended', 'pending') DEFAULT 'active',
    role ENUM('user', 'admin') DEFAULT 'user',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL DEFAULT NULL,
    
    -- Indexes for performance
    INDEX idx_api_key (api_key),
    INDEX idx_email (email),
    INDEX idx_username (username),
    INDEX idx_status (status),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: qris_codes
-- Stores QRIS codes uploaded by users
-- ============================================================================
CREATE TABLE qris_codes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    
    -- QRIS Info
    qris_name VARCHAR(100) NOT NULL,
    qris_code TEXT NOT NULL,
    qris_image VARCHAR(255) DEFAULT NULL,
    
    -- GoPay Merchant Info (copied from user on creation)
    merchant_id VARCHAR(100) DEFAULT NULL,
    terminal_id VARCHAR(100) DEFAULT NULL,
    
    -- Payment Settings
    amount DECIMAL(15,2) DEFAULT 0.00 COMMENT '0 = dynamic amount',
    is_dynamic BOOLEAN DEFAULT TRUE,
    
    -- Webhook
    callback_url VARCHAR(255) DEFAULT NULL,
    
    -- Status
    status ENUM('active', 'inactive') DEFAULT 'active',
    
    -- Statistics
    total_transactions INT DEFAULT 0,
    total_revenue DECIMAL(15,2) DEFAULT 0.00,
    last_transaction_at TIMESTAMP NULL DEFAULT NULL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_user_qris (user_id, status),
    INDEX idx_status (status),
    INDEX idx_merchant (merchant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: transactions
-- Stores all payment transactions
-- ============================================================================
CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    qris_id INT NOT NULL,
    user_id INT NOT NULL,
    
    -- Amount Info
    amount DECIMAL(15,2) NOT NULL,
    admin_fee DECIMAL(15,2) DEFAULT 0.00,
    net_amount DECIMAL(15,2) NOT NULL COMMENT 'amount - admin_fee',
    
    -- Customer Info
    customer_name VARCHAR(100) DEFAULT NULL,
    customer_phone VARCHAR(20) DEFAULT NULL,
    customer_email VARCHAR(100) DEFAULT NULL,
    
    -- Payment Info
    payment_method VARCHAR(50) DEFAULT 'QRIS',
    payment_status ENUM('pending', 'success', 'failed', 'expired') DEFAULT 'pending',
    payment_time TIMESTAMP NULL DEFAULT NULL,
    
    -- GoPay Reference
    reference_id VARCHAR(100) DEFAULT NULL COMMENT 'GoPay transaction reference',
    issuer VARCHAR(50) DEFAULT NULL COMMENT 'Payment issuer (GoPay, OVO, etc)',
    
    -- Webhook
    callback_sent BOOLEAN DEFAULT FALSE,
    callback_attempts INT DEFAULT 0,
    callback_last_attempt TIMESTAMP NULL DEFAULT NULL,
    
    -- Request Info
    ip_address VARCHAR(45) DEFAULT NULL,
    user_agent TEXT DEFAULT NULL,
    
    -- Additional Data (JSON format)
    metadata JSON DEFAULT NULL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expired_at TIMESTAMP NULL DEFAULT NULL,
    
    -- Foreign Keys
    FOREIGN KEY (qris_id) REFERENCES qris_codes(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Indexes for performance
    INDEX idx_transaction (transaction_id),
    INDEX idx_user_transactions (user_id, payment_status),
    INDEX idx_qris_transactions (qris_id, payment_status),
    INDEX idx_payment_status (payment_status),
    INDEX idx_payment_time (payment_time),
    INDEX idx_reference (reference_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: api_logs
-- Logs all API requests for monitoring and debugging
-- ============================================================================
CREATE TABLE api_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT DEFAULT NULL,
    api_key VARCHAR(100) DEFAULT NULL,
    
    -- Request Info
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL COMMENT 'GET, POST, PUT, DELETE',
    request_body TEXT DEFAULT NULL,
    request_headers TEXT DEFAULT NULL,
    
    -- Response Info
    response_code INT DEFAULT NULL,
    response_body TEXT DEFAULT NULL,
    
    -- Performance
    execution_time FLOAT DEFAULT NULL COMMENT 'Execution time in seconds',
    
    -- Request Meta
    ip_address VARCHAR(45) DEFAULT NULL,
    user_agent TEXT DEFAULT NULL,
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Key
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    
    -- Indexes
    INDEX idx_api_user (user_id, created_at),
    INDEX idx_api_key (api_key, created_at),
    INDEX idx_endpoint (endpoint),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: webhooks
-- Tracks webhook delivery attempts
-- ============================================================================
CREATE TABLE webhooks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL,
    
    -- Webhook Info
    url VARCHAR(255) NOT NULL,
    payload TEXT NOT NULL,
    
    -- Response
    response_code INT DEFAULT NULL,
    response_body TEXT DEFAULT NULL,
    
    -- Retry Logic
    attempt INT DEFAULT 1,
    max_attempts INT DEFAULT 3,
    status ENUM('pending', 'success', 'failed') DEFAULT 'pending',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP NULL DEFAULT NULL,
    next_retry_at TIMESTAMP NULL DEFAULT NULL,
    
    -- Indexes
    INDEX idx_transaction (transaction_id),
    INDEX idx_status (status, next_retry_at),
    INDEX idx_webhook_status (status, attempt)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: settings
-- System-wide configuration settings
-- ============================================================================
CREATE TABLE settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(50) UNIQUE NOT NULL,
    setting_value TEXT DEFAULT NULL,
    setting_type ENUM('string', 'number', 'boolean', 'json') DEFAULT 'string',
    description VARCHAR(255) DEFAULT NULL,
    is_public BOOLEAN DEFAULT FALSE COMMENT 'Can be accessed via API',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Index
    INDEX idx_key (setting_key),
    INDEX idx_public (is_public)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: notifications
-- User notifications (optional feature)
-- ============================================================================
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    
    -- Notification Info
    title VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    type ENUM('info', 'success', 'warning', 'error') DEFAULT 'info',
    
    -- Link
    link VARCHAR(255) DEFAULT NULL,
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP NULL DEFAULT NULL,
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Key
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_user_notifications (user_id, is_read, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: payment_methods
-- Supported payment methods configuration
-- ============================================================================
CREATE TABLE payment_methods (
    id INT AUTO_INCREMENT PRIMARY KEY,
    method_code VARCHAR(50) UNIQUE NOT NULL,
    method_name VARCHAR(100) NOT NULL,
    description TEXT DEFAULT NULL,
    icon_url VARCHAR(255) DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INT DEFAULT 0,
    
    -- Configuration (JSON)
    config JSON DEFAULT NULL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Index
    INDEX idx_active (is_active, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: withdrawals
-- User withdrawal requests
-- ============================================================================
CREATE TABLE withdrawals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    
    -- Withdrawal Info
    withdrawal_id VARCHAR(50) UNIQUE NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    admin_fee DECIMAL(15,2) DEFAULT 0.00,
    net_amount DECIMAL(15,2) NOT NULL,
    
    -- Bank Info
    bank_name VARCHAR(100) NOT NULL,
    account_number VARCHAR(50) NOT NULL,
    account_name VARCHAR(100) NOT NULL,
    
    -- Status
    status ENUM('pending', 'processing', 'completed', 'rejected') DEFAULT 'pending',
    
    -- Admin Notes
    processed_by INT DEFAULT NULL COMMENT 'Admin user ID',
    admin_notes TEXT DEFAULT NULL,
    
    -- Proof
    proof_image VARCHAR(255) DEFAULT NULL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NULL DEFAULT NULL,
    
    -- Foreign Keys
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (processed_by) REFERENCES users(id) ON DELETE SET NULL,
    
    -- Indexes
    INDEX idx_user_withdrawals (user_id, status),
    INDEX idx_status (status, created_at),
    INDEX idx_withdrawal_id (withdrawal_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- INSERT DEFAULT DATA
-- ============================================================================

-- Default Admin User
-- Password: admin123 (hashed with bcrypt)
INSERT INTO users (
    username, 
    email, 
    password, 
    full_name, 
    api_key, 
    api_secret, 
    role,
    status
) VALUES (
    'admin',
    'admin@lexmerchant.com',
    '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi',
    'Administrator',
    'lex_admin_master_key_2026',
    'lex_admin_secret_2026',
    'admin',
    'active'
);

-- Default System Settings
INSERT INTO settings (setting_key, setting_value, setting_type, description, is_public) VALUES
('site_name', 'LexMerchant', 'string', 'Site name', TRUE),
('admin_fee_percentage', '1.5', 'number', 'Admin fee percentage per transaction', FALSE),
('min_transaction', '1000', 'number', 'Minimum transaction amount in IDR', TRUE),
('max_transaction', '10000000', 'number', 'Maximum transaction amount in IDR', TRUE),
('qris_check_interval', '10', 'number', 'QRIS payment check interval in seconds', FALSE),
('transaction_timeout', '3600', 'number', 'Transaction expiry time in seconds (1 hour)', FALSE),
('webhook_retry_attempts', '3', 'number', 'Maximum webhook retry attempts', FALSE),
('webhook_retry_delay', '60', 'number', 'Webhook retry delay in seconds', FALSE),
('min_withdrawal', '50000', 'number', 'Minimum withdrawal amount', FALSE),
('withdrawal_fee', '2500', 'number', 'Withdrawal admin fee', FALSE),
('registration_enabled', 'true', 'boolean', 'Allow new user registration', TRUE),
('maintenance_mode', 'false', 'boolean', 'Enable maintenance mode', TRUE),
('gopay_merchant_id', '', 'string', 'Global GoPay Merchant ID (optional)', FALSE),
('gopay_api_key', '', 'string', 'Global GoPay API Key (optional)', FALSE),
('gopay_api_secret', '', 'string', 'Global GoPay API Secret (optional)', FALSE);

-- Default Payment Methods
INSERT INTO payment_methods (method_code, method_name, description, is_active, sort_order) VALUES
('qris', 'QRIS', 'Quick Response Code Indonesian Standard', TRUE, 1),
('gopay', 'GoPay', 'GoPay E-Wallet', TRUE, 2),
('ovo', 'OVO', 'OVO E-Wallet', TRUE, 3),
('dana', 'DANA', 'DANA E-Wallet', TRUE, 4),
('shopeepay', 'ShopeePay', 'ShopeePay E-Wallet', TRUE, 5),
('linkaja', 'LinkAja', 'LinkAja E-Wallet', TRUE, 6);

-- ============================================================================
-- VIEWS (Optional - for easier queries)
-- ============================================================================

-- View: User Statistics
CREATE OR REPLACE VIEW view_user_stats AS
SELECT 
    u.id,
    u.username,
    u.full_name,
    u.email,
    u.balance,
    u.status,
    COUNT(DISTINCT q.id) as total_qris,
    COUNT(DISTINCT t.id) as total_transactions,
    COALESCE(SUM(CASE WHEN t.payment_status = 'success' THEN t.amount ELSE 0 END), 0) as total_revenue,
    COALESCE(SUM(CASE WHEN t.payment_status = 'success' THEN t.net_amount ELSE 0 END), 0) as net_revenue,
    u.created_at
FROM users u
LEFT JOIN qris_codes q ON u.id = q.user_id AND q.status = 'active'
LEFT JOIN transactions t ON u.id = t.user_id
WHERE u.role = 'user'
GROUP BY u.id;

-- View: Transaction Summary
CREATE OR REPLACE VIEW view_transaction_summary AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_transactions,
    COUNT(CASE WHEN payment_status = 'success' THEN 1 END) as successful_transactions,
    COUNT(CASE WHEN payment_status = 'pending' THEN 1 END) as pending_transactions,
    COUNT(CASE WHEN payment_status = 'failed' THEN 1 END) as failed_transactions,
    COALESCE(SUM(CASE WHEN payment_status = 'success' THEN amount ELSE 0 END), 0) as total_amount,
    COALESCE(SUM(CASE WHEN payment_status = 'success' THEN admin_fee ELSE 0 END), 0) as total_admin_fee
FROM transactions
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- ============================================================================
-- TRIGGERS (Optional - for auto-updates)
-- ============================================================================

DELIMITER $$

-- Trigger: Update QRIS statistics on successful transaction
CREATE TRIGGER after_transaction_success
AFTER UPDATE ON transactions
FOR EACH ROW
BEGIN
    IF NEW.payment_status = 'success' AND OLD.payment_status != 'success' THEN
        UPDATE qris_codes
        SET 
            total_transactions = total_transactions + 1,
            total_revenue = total_revenue + NEW.amount,
            last_transaction_at = NEW.payment_time
        WHERE id = NEW.qris_id;
        
        UPDATE users
        SET balance = balance + NEW.net_amount
        WHERE id = NEW.user_id;
    END IF;
END$$

-- Trigger: Set transaction expiry time on creation
CREATE TRIGGER before_transaction_insert
BEFORE INSERT ON transactions
FOR EACH ROW
BEGIN
    DECLARE timeout_seconds INT;
    
    SELECT setting_value INTO timeout_seconds
    FROM settings
    WHERE setting_key = 'transaction_timeout';
    
    SET NEW.expired_at = DATE_ADD(NEW.created_at, INTERVAL timeout_seconds SECOND);
END$$

DELIMITER ;

-- ============================================================================
-- INDEXES SUMMARY
-- ============================================================================
-- users: api_key, email, username, status, role
-- qris_codes: user_id+status, status, merchant_id
-- transactions: transaction_id, user_id+status, qris_id+status, status, payment_time, reference_id, created_at
-- api_logs: user_id+created_at, api_key+created_at, endpoint, created_at
-- webhooks: transaction_id, status+next_retry_at
-- settings: setting_key, is_public
-- notifications: user_id+is_read+created_at
-- payment_methods: is_active+sort_order
-- withdrawals: user_id+status, status+created_at, withdrawal_id

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

-- Database created successfully!
-- Default admin credentials:
--   Username: admin
--   Password: admin123
--
-- IMPORTANT: Change the admin password immediately after first login!
-- ============================================================================