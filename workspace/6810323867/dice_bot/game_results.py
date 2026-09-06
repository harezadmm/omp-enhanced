from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import Database
from game import DiceGame

db = Database()
game = DiceGame()
user_bets = {}

async def handle_bet_choice(query, user_id, data):
    """Handle besar/kecil choice and play game"""
    bet_type = data.split("_")[1]  # "besar" or "kecil"
    
    # Get stored bet amount
    bet_amount = user_bets.get(user_id)
    if not bet_amount:
        await query.answer("❌ Error: Bet tidak ditemukan", show_alert=True)
        return
    
    user = db.get_user(user_id)
    
    # Validate again (safety check)
    valid, msg = game.validate_bet(user['balance'], bet_amount)
    if not valid:
        await query.answer(msg, show_alert=True)
        return
    
    # Deduct bet from balance
    db.update_balance(user_id, -bet_amount)
    
    # Play game
    dice_result, win_amount, result_text = game.calculate_result(bet_type, bet_amount)
    
    # Add winnings if won
    if win_amount > 0:
        db.update_balance(user_id, bet_amount + win_amount)
    
    # Record game
    db.add_game(user_id, bet_type, bet_amount, dice_result, win_amount)
    
    # Get new balance
    user = db.get_user(user_id)
    new_balance = user['balance']
    
    # Build result message
    dice_emoji = game.get_dice_emoji(dice_result)
    
    full_text = (
        f"{dice_emoji} <b>HASIL</b> {dice_emoji}\n\n"
        f"{result_text}\n\n"
        f"💰 Saldo sekarang: Rp {new_balance:,}"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Main Lagi", callback_data="play")],
        [InlineKeyboardButton("📊 Statistik", callback_data="stats"),
         InlineKeyboardButton("💰 Saldo", callback_data="balance")],
        [InlineKeyboardButton("◀️ Menu Utama", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Clear stored bet
    if user_id in user_bets:
        del user_bets[user_id]
    
    await query.edit_message_text(full_text, reply_markup=reply_markup, parse_mode="HTML")

async def show_leaderboard(query):
    """Show top players leaderboard"""
    top_players = db.get_top_players(10)
    
    text = "🏆 <b>LEADERBOARD TOP 10</b>\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    for i, player in enumerate(top_players):
        rank = medals[i] if i < 3 else f"{i+1}."
        username = player['username'] or f"User{player['user_id']}"
        balance = player['balance']
        text += f"{rank} {username} - Rp {balance:,}\n"
    
    keyboard = [[InlineKeyboardButton("◀️ Kembali", callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
