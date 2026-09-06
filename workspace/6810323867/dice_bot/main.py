#!/usr/bin/env python3
"""
Telegram Dice Gambling Bot
Dadu Besar/Kecil dengan auto-deposit QRIS
"""

from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from flask import Flask, request, jsonify
import threading
import config
from database import Database
from payment import PaymentProcessor

# Import all handlers
from bot_handlers import start, button_handler
from game_handlers import show_bet_menu, handle_bet_amount
from game_results import handle_bet_choice, show_leaderboard
from payment_handlers import show_deposit_menu, handle_deposit, show_withdraw_menu

# Initialize
db = Database()
payment = PaymentProcessor()

# Flask app for webhook
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle payment callback from Tripay"""
    try:
        data = request.get_json()
        
        # Verify signature
        if not payment.verify_callback(data):
            return jsonify({"success": False, "message": "Invalid signature"}), 401
        
        payment_id = data.get('reference')
        status = data.get('status')
        
        # Get transaction
        tx = db.get_transaction(payment_id)
        if not tx:
            return jsonify({"success": False, "message": "Transaction not found"}), 404
        
        # Update transaction status
        db.update_transaction_status(payment_id, status)
        
        # If paid, add balance
        if status == 'PAID':
            db.update_balance(tx['user_id'], tx['amount'])
            
            # Send notification to user (optional - needs bot instance)
            print(f"✅ Payment success: User {tx['user_id']} +Rp {tx['amount']:,}")
        
        return jsonify({"success": True}), 200
        
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "bot": "running"}), 200

def run_flask():
    """Run Flask in separate thread"""
    app.run(host='0.0.0.0', port=config.WEBHOOK_PORT, debug=False)

async def admin_stats(update, context):
    """Admin command to view bot statistics"""
    user_id = update.effective_user.id
    
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    # Get statistics
    total_users = db.cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_balance = db.cursor.execute("SELECT SUM(balance) FROM users").fetchone()[0] or 0
    total_bets = db.cursor.execute("SELECT SUM(bet_amount) FROM game_history").fetchone()[0] or 0
    total_games = db.cursor.execute("SELECT COUNT(*) FROM game_history").fetchone()[0]
    
    text = (
        f"📊 <b>ADMIN STATISTICS</b>\n\n"
        f"👥 Total Users: {total_users}\n"
        f"💰 Total Balance: Rp {total_balance:,}\n"
        f"🎲 Total Games: {total_games}\n"
        f"💵 Total Bets: Rp {total_bets:,}\n"
    )
    
    await update.message.reply_text(text, parse_mode="HTML")

async def admin_broadcast(update, context):
    """Admin command to broadcast message"""
    user_id = update.effective_user.id
    
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = " ".join(context.args)
    
    # Get all users
    users = db.cursor.execute("SELECT user_id FROM users").fetchall()
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user[0],
                text=f"📢 <b>BROADCAST</b>\n\n{message}",
                parse_mode="HTML"
            )
            success += 1
        except:
            failed += 1
    
    await update.message.reply_text(
        f"✅ Broadcast complete!\n\n"
        f"Success: {success}\n"
        f"Failed: {failed}"
    )

def main():
    """Main function"""
    print("🤖 Starting Dice Gambling Bot...")
    
    # Start Flask webhook in background
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"🌐 Webhook server running on port {config.WEBHOOK_PORT}")
    
    # Create bot application
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ Bot started successfully!")
    print(f"📱 Bot username: @{application.bot.username}")
    
    # Start bot
    application.run_polling(allowed_updates=['message', 'callback_query'])

if __name__ == "__main__":
    main()
