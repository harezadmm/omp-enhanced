from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import config
from database import Database
from payment import PaymentProcessor
from game import DiceGame

# Initialize
db = Database()
payment = PaymentProcessor()
game = DiceGame()

# Store temporary bet amounts (in-memory)
user_bets = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler /start command"""
    user = update.effective_user
    
    # Create user if not exists
    if not db.get_user(user.id):
        db.create_user(user.id, user.username)
    
    keyboard = [
        [InlineKeyboardButton("🎲 Main Dadu", callback_data="play")],
        [InlineKeyboardButton("💰 Saldo", callback_data="balance"),
         InlineKeyboardButton("📊 Statistik", callback_data="stats")],
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit"),
         InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"👋 Selamat datang {user.first_name}!\n\n"
        f"🎲 <b>GAME DADU BESAR/KECIL</b>\n\n"
        f"Aturan:\n"
        f"🔴 BESAR = Dadu 4, 5, 6\n"
        f"🔵 KECIL = Dadu 1, 2, 3\n\n"
        f"💰 Min bet: Rp {config.MIN_BET:,}\n"
        f"💰 Max bet: Rp {config.MAX_BET:,}\n"
        f"💵 Min deposit: Rp {config.MIN_DEPOSIT:,}\n\n"
        f"Pilih menu di bawah untuk mulai!"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk inline button"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "play":
        await show_bet_menu(query, user_id)
    elif data == "balance":
        await show_balance(query, user_id)
    elif data == "stats":
        await show_stats(query, user_id)
    elif data == "deposit":
        await show_deposit_menu(query, user_id)
    elif data == "withdraw":
        await show_withdraw_menu(query, user_id)
    elif data == "leaderboard":
        await show_leaderboard(query)
    elif data.startswith("bet_"):
        await handle_bet_amount(query, user_id, data)
    elif data.startswith("choose_"):
        await handle_bet_choice(query, user_id, data)
    elif data.startswith("deposit_"):
        await handle_deposit(query, user_id, data)
    elif data == "back":
        await show_main_menu(query, user_id)

async def show_main_menu(query, user_id):
    """Show main menu"""
    keyboard = [
        [InlineKeyboardButton("🎲 Main Dadu", callback_data="play")],
        [InlineKeyboardButton("💰 Saldo", callback_data="balance"),
         InlineKeyboardButton("📊 Statistik", callback_data="stats")],
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit"),
         InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("📋 Menu Utama", reply_markup=reply_markup)
