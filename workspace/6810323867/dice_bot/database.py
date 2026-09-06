import sqlite3
from typing import Optional, Dict, List
from datetime import datetime
import config

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(config.DATABASE_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        """Create all necessary tables"""
        # Users table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 0,
                total_bet INTEGER DEFAULT 0,
                total_win INTEGER DEFAULT 0,
                total_loss INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Transactions table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount INTEGER,
                status TEXT,
                payment_id TEXT,
                qris_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Game history table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bet_type TEXT,
                bet_amount INTEGER,
                dice_result INTEGER,
                win_amount INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        self.conn.commit()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data"""
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def create_user(self, user_id: int, username: str = None):
        """Create new user"""
        try:
            self.cursor.execute(
                "INSERT INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def update_balance(self, user_id: int, amount: int):
        """Update user balance"""
        self.cursor.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        self.conn.commit()
    
    def add_transaction(self, user_id: int, tx_type: str, amount: int, 
                       status: str = "pending", payment_id: str = None, 
                       qris_url: str = None) -> int:
        """Add transaction record"""
        self.cursor.execute("""
            INSERT INTO transactions (user_id, type, amount, status, payment_id, qris_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, tx_type, amount, status, payment_id, qris_url))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_transaction_status(self, payment_id: str, status: str):
        """Update transaction status"""
        self.cursor.execute(
            "UPDATE transactions SET status = ? WHERE payment_id = ?",
            (status, payment_id)
        )
        self.conn.commit()
    
    def get_transaction(self, payment_id: str) -> Optional[Dict]:
        """Get transaction by payment ID"""
        self.cursor.execute(
            "SELECT * FROM transactions WHERE payment_id = ?",
            (payment_id,)
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def add_game(self, user_id: int, bet_type: str, bet_amount: int, 
                 dice_result: int, win_amount: int):
        """Record game result"""
        self.cursor.execute("""
            INSERT INTO game_history (user_id, bet_type, bet_amount, dice_result, win_amount)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, bet_type, bet_amount, dice_result, win_amount))
        
        # Update user stats
        if win_amount > 0:
            self.cursor.execute("""
                UPDATE users 
                SET total_bet = total_bet + ?, total_win = total_win + ?
                WHERE user_id = ?
            """, (bet_amount, win_amount, user_id))
        else:
            self.cursor.execute("""
                UPDATE users 
                SET total_bet = total_bet + ?, total_loss = total_loss + ?
                WHERE user_id = ?
            """, (bet_amount, bet_amount, user_id))
        
        self.conn.commit()
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get user statistics"""
        user = self.get_user(user_id)
        if not user:
            return {}
        
        self.cursor.execute("""
            SELECT COUNT(*) as total_games,
                   SUM(CASE WHEN win_amount > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN win_amount = 0 THEN 1 ELSE 0 END) as losses
            FROM game_history WHERE user_id = ?
        """, (user_id,))
        
        stats = dict(self.cursor.fetchone())
        stats.update(user)
        return stats
    
    def get_top_players(self, limit: int = 10) -> List[Dict]:
        """Get leaderboard"""
        self.cursor.execute("""
            SELECT user_id, username, balance, total_win, total_loss
            FROM users
            ORDER BY balance DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in self.cursor.fetchall()]
