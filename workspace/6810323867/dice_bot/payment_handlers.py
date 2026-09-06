from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import config
from database import Database
from payment import PaymentProcessor

db = Database()
payment = PaymentProcessor()

async def show_deposit_menu(query, user_id):
    """Show deposit menu"""
    text = (
        f"💳 <b>DEPOSIT VIA QRIS</b>\n\n"
        f"💵 Minimal deposit: Rp {config.MIN_DEPOSIT:,}\n\n"
        f"Pilih nominal deposit:"
    )
    
    keyboard = [
        [InlineKeyboardButton("Rp 10K", callback_data="deposit_10000"),
         InlineKeyboardButton("Rp 20K", callback_data="deposit_20000"),
         InlineKeyboardButton("Rp 50K", callback_data="deposit_50000")],
        [InlineKeyboardButton("Rp 100K", callback_data="deposit_100000"),
         InlineKeyboardButton("Rp 200K", callback_data="deposit_200000"),
         InlineKeyboardButton("Rp 500K", callback_data="deposit_500000")],
        [InlineKeyboardButton("Rp 1JT", callback_data="deposit_1000000"),
         InlineKeyboardButton("Rp 2JT", callback_data="deposit_2000000")],
        [InlineKeyboardButton("◀️ Kembali", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")

async def handle_deposit(query, user_id, data):
    """Handle deposit request"""
    amount = int(data.split("_")[1])
    
    if amount < config.MIN_DEPOSIT:
        await query.answer(f"❌ Minimal deposit Rp {config.MIN_DEPOSIT:,}", show_alert=True)
        return
    
    # Create payment
    await query.edit_message_text("⏳ Membuat QRIS payment...", parse_mode="HTML")
    
    payment_data = payment.create_qris_payment(user_id, amount)
    
    if not payment_data:
        text = "❌ <b>GAGAL</b>\n\nTidak bisa membuat payment. Coba lagi nanti."
        keyboard = [[InlineKeyboardButton("◀️ Kembali", callback_data="deposit")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
        return
    
    # Save transaction
    db.add_transaction(
        user_id=user_id,
        tx_type="deposit",
        amount=amount,
        status="pending",
        payment_id=payment_data['payment_id'],
        qris_url=payment_data['qris_url']
    )
    
    text = (
        f"💳 <b>DEPOSIT QRIS</b>\n\n"
        f"💰 Jumlah: Rp {amount:,}\n"
        f"🆔 Payment ID: {payment_data['payment_id']}\n\n"
        f"📱 <b>Cara Bayar:</b>\n"
        f"1. Screenshot QR code di bawah\n"
        f"2. Buka aplikasi e-wallet/mobile banking\n"
        f"3. Scan QRIS\n"
        f"4. Bayar sesuai nominal\n"
        f"5. Saldo otomatis masuk\n\n"
        f"⏰ Expired dalam 60 menit\n"
        f"✅ Auto-detect payment"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔗 Lihat QR Code", url=payment_data['qris_url'])],
        [InlineKeyboardButton("◀️ Menu Utama", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")

async def show_withdraw_menu(query, user_id):
    """Show withdraw menu"""
    user = db.get_user(user_id)
    balance = user['balance']
    
    text = (
        f"💸 <b>WITHDRAW</b>\n\n"
        f"💰 Saldo: Rp {balance:,}\n\n"
        f"Untuk withdraw, hubungi admin:\n"
        f"👤 @admin_username\n\n"
        f"Info yang perlu disiapkan:\n"
        f"• Nama rekening\n"
        f"• Nomor rekening\n"
        f"• Bank\n"
        f"• Jumlah withdraw\n\n"
        f"⏱️ Proses 1-24 jam kerja"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Kembali", callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
