from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import config
from database import Database
from payment import PaymentProcessor
from game import DiceGame

db = Database()
payment = PaymentProcessor()
game = DiceGame()
user_bets = {}

async def show_balance(query, user_id):
    """Show user balance"""
    user = db.get_user(user_id)
    
    text = (
        f"💰 <b>SALDO KAMU</b>\n\n"
        f"💵 Saldo: Rp {user['balance']:,}\n"
        f"📊 Total Bet: Rp {user['total_bet']:,}\n"
        f"✅ Total Win: Rp {user['total_win']:,}\n"
        f"❌ Total Loss: Rp {user['total_loss']:,}\n"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Kembali", callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")

async def show_stats(query, user_id):
    """Show user statistics"""
    stats = db.get_user_stats(user_id)
    
    total_games = stats.get('total_games', 0)
    wins = stats.get('wins', 0)
    losses = stats.get('losses', 0)
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    
    text = (
        f"📊 <b>STATISTIK KAMU</b>\n\n"
        f"🎲 Total Game: {total_games}\n"
        f"✅ Menang: {wins}\n"
        f"❌ Kalah: {losses}\n"
        f"📈 Win Rate: {win_rate:.1f}%\n\n"
        f"💰 Saldo: Rp {stats['balance']:,}\n"
        f"💵 Total Bet: Rp {stats['total_bet']:,}\n"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Kembali", callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")

async def show_bet_menu(query, user_id):
    """Show betting amount menu"""
    user = db.get_user(user_id)
    balance = user['balance']
    
    if balance < config.MIN_BET:
        text = f"❌ Saldo tidak cukup!\n\n💰 Saldo: Rp {balance:,}\n💳 Min bet: Rp {config.MIN_BET:,}\n\nSilahkan deposit terlebih dahulu."
        keyboard = [
            [InlineKeyboardButton("💳 Deposit", callback_data="deposit")],
            [InlineKeyboardButton("◀️ Kembali", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return
    
    text = (
        f"💰 Saldo: Rp {balance:,}\n\n"
        f"Pilih jumlah bet:"
    )
    
    keyboard = [
        [InlineKeyboardButton("Rp 1K", callback_data="bet_1000"),
         InlineKeyboardButton("Rp 5K", callback_data="bet_5000"),
         InlineKeyboardButton("Rp 10K", callback_data="bet_10000")],
        [InlineKeyboardButton("Rp 50K", callback_data="bet_50000"),
         InlineKeyboardButton("Rp 100K", callback_data="bet_100000")],
        [InlineKeyboardButton("Rp 500K", callback_data="bet_500000"),
         InlineKeyboardButton("Rp 1JT", callback_data="bet_1000000")],
        [InlineKeyboardButton("◀️ Kembali", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def handle_bet_amount(query, user_id, data):
    """Handle bet amount selection"""
    bet_amount = int(data.split("_")[1])
    user = db.get_user(user_id)
    
    # Validate bet
    valid, msg = game.validate_bet(user['balance'], bet_amount)
    if not valid:
        await query.answer(msg, show_alert=True)
        return
    
    # Store bet amount
    user_bets[user_id] = bet_amount
    
    text = (
        f"🎲 <b>PILIH BESAR ATAU KECIL</b>\n\n"
        f"💰 Bet: Rp {bet_amount:,}\n\n"
        f"🔴 BESAR = Dadu 4, 5, 6\n"
        f"🔵 KECIL = Dadu 1, 2, 3\n\n"
        f"Pilih tebakan kamu:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔴 BESAR", callback_data="choose_besar"),
         InlineKeyboardButton("🔵 KECIL", callback_data="choose_kecil")],
        [InlineKeyboardButton("◀️ Kembali", callback_data="play")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
