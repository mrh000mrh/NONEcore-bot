#!/usr/bin/env python3
"""
NONEcore Config Bot
ربات اهدای کانفیگ VPN
"""

import os
import logging
import re
import base64
import json
import requests
import qrcode
import io
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
from config import Config

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# استیت‌های کانورسیشن
UPLOAD_HTML = 1

def main():
    """نقطه ورود اصلی"""
    logger.info("Starting NONEcore Bot...")
    
    # ساخت اپلیکیشن
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # هندلرها
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("channels", channels_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("clients", clients_command))
    
    # کانورسیشن آپلود
    upload_conv = ConversationHandler(
        entry_points=[CommandHandler("upload", upload_start)],
        states={
            UPLOAD_HTML: [MessageHandler(filters.Document.ALL, upload_process)]
        },
        fallbacks=[CommandHandler("cancel", upload_cancel)]
    )
    application.add_handler(upload_conv)
    
    # شروع ربات
    application.run_polling(allowed_updates=Update.ALL_TYPES)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع - فقط ادمین"""
    user_id = str(update.effective_user.id)
    
    if user_id != Config.ADMIN_ID:
        await update.message.reply_text("⛔ شما ادمین نیستید.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📤 آپلود HTML", callback_data='upload')],
        [InlineKeyboardButton("📊 آمار", callback_data='stats')],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data='settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔷 <b>NONEcore Admin Panel</b>\n\n"
        "ربات مدیریت کانفیگ VPN\n"
        "کانال: @nonecorebot\n\n"
        "دستورات:\n"
        "/upload - آپلود فایل HTML\n"
        "/stats - آمار کانفیگ‌ها\n"
        "/channels - مدیریت کانال‌ها\n"
        "/settings - تنظیمات\n"
        "/clients - ارسال لیست کلاینت‌ها",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def upload_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع آپلود"""
    user_id = str(update.effective_user.id)
    if user_id != Config.ADMIN_ID:
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📁 لطفاً فایل HTML اکسپورت شده را ارسال کنید:\n\n"
        "راهنما:\n"
        "۱. Telegram Desktop باز کنید\n"
        "۲. کانال مورد نظر را باز کنید\n"
        "۳. سه نقطه بالا → Export chat history\n"
        "۴. فرمت HTML را انتخاب کنید\n"
        "۵. فایل را اینجا ارسال کنید\n\n"
        "یا /cancel برای لغو"
    )
    return UPLOAD_HTML

async def upload_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش فایل HTML"""
    # TODO: پیاده‌سازی کامل در فایل‌های بعدی
    await update.message.reply_text("✅ فایل دریافت شد. در حال پردازش...")
    return ConversationHandler.END

async def upload_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو آپلود"""
    await update.message.reply_text("❌ لغو شد.")
    return ConversationHandler.END

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار"""
    user_id = str(update.effective_user.id)
    if user_id != Config.ADMIN_ID:
        return
    
    await update.message.reply_text(
        "📊 آمار NONEcore\n\n"
        "📤 امروز: 0 کانفیگ\n"
        "📈 کل: 0 کانفیگ\n\n"
        "🔄 آمار واقعی پس از پردازش اولین فایل نمایش داده می‌شود."
    )

async def channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کانال‌ها"""
    user_id = str(update.effective_user.id)
    if user_id != Config.ADMIN_ID:
        return
    
    channels = Config.CHANNELS.split(',') if Config.CHANNELS else []
    text = "📢 کانال‌های مقصد:\n\n"
    for ch in channels:
        text += f"• {ch}\n"
    
    text += "\nبرای تغییر، در config.py ویرایش کنید."
    await update.message.reply_text(text)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیمات"""
    user_id = str(update.effective_user.id)
    if user_id != Config.ADMIN_ID:
        return
    
    await update.message.reply_text(
        "⚙️ تنظیمات NONEcore\n\n"
        f"ارسال کلاینت‌ها: {'✅' if Config.SEND_CLIENTS else '❌'}\n"
        f"حالت تأییدیه: {'✅' if Config.APPROVAL_MODE else '❌'}\n"
        f"تعداد هر batch: {Config.BATCH_SIZE}\n"
        f"فاصله: {Config.BATCH_INTERVAL} ثانیه\n\n"
        "برای تغییر، متغیرهای محیطی را ویرایش کنید."
    )

async def clients_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال لیست کلاینت‌ها"""
    user_id = str(update.effective_user.id)
    if user_id != Config.ADMIN_ID:
        return
    
    text = """📱 کلاینت‌های پیشنهادی:

🤖 اندروید:
• V2RayNG - github.com/2dust/v2rayNG
• SagerNet - github.com/SagerNet/SagerNet

🍎 iOS:
• Streisand - App Store
• Shadowrocket - App Store

💻 ویندوز:
• v2rayN - github.com/2dust/v2rayN
• Nekoray - github.com/MatsuriDayo/nekoray

🐧 لینوکس/macOS:
• Nekoray - github.com/MatsuriDayo/nekoray

🔒 فیلترشکن‌های ضدسانسور:
• Psiphon - psiphon.ca
• Tor Browser - torproject.org
• Tails - tails.boum.org
• Lantern - getlantern.org
• Outline - getoutline.org

⚡️ کانال: @nonecorebot"""
    
    await update.message.reply_text(text)

if __name__ == "__main__":
    main()
