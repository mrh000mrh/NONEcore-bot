#!/usr/bin/env python3
"""
NONEcore Config Bot - کامل
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from config import Config
from bot.database import Database
from bot.processor import ConfigProcessor
from bot.sender import ConfigSender

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# استیت‌ها
UPLOAD_HTML, SETTINGS_VALUE = range(2)

# دیتابیس global
db = Database()

def main():
    """نقطه ورود"""
    logger.info("Starting NONEcore Bot...")
    
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # هندلرها
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("channels", channels_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("clients", clients_command))
    application.add_handler(CommandHandler("toggle_reminder", toggle_reminder_command))
    
    # کانورسیون آپلود
    upload_conv = ConversationHandler(
        entry_points=[CommandHandler("upload", upload_start)],
        states={
            UPLOAD_HTML: [MessageHandler(filters.Document.ALL, upload_process)]
        },
        fallbacks=[CommandHandler("cancel", upload_cancel)]
    )
    application.add_handler(upload_conv)
    
    # callback ها
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # شروع
    application.run_polling(allowed_updates=Update.ALL_TYPES)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
    user_id = str(update.effective_user.id)
    
    if user_id != Config.ADMIN_ID:
        await update.message.reply_text("⛔ شما ادمین نیستید.")
        return
    
    # محاسبه زمان renewal
    now = datetime.now()
    next_renewal = (now + timedelta(days=1)).replace(hour=Config.RENEWAL_HOUR, minute=0, second=0)
    hours_left = int((next_renewal - now).total_seconds() / 3600)
    
    # چک کردن یادآوری
    reminder_enabled = db.get_setting('reminder_enabled', 'true') == 'true'
    
    keyboard = [
        [InlineKeyboardButton("📤 آپلود HTML", callback_data='upload')],
        [InlineKeyboardButton("📊 آمار", callback_data='stats')],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data='settings')],
        [InlineKeyboardButton("🔔 یادآوری: " + ("✅" if reminder_enabled else "❌"), callback_data='toggle_reminder')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    renewal_msg = ""
    if reminder_enabled:
        renewal_msg = f"""
⏰ <b>یادآوری مهم!</b>

🔄 <b>Renewal سرور FPS.ms</b>
⏳ {hours_left} ساعت مانده تا renewal بعدی
🕐 زمان: هر روز ساعت {Config.RENEWAL_HOUR}:۰۰

🔗 <a href="{Config.FPS_RENEWAL_URL}">کلیک کنید برای renewal</a>

📋 <b>آموزش renewal:</b>
۱. روی لینک بالا کلیک کنید
۲. وارد Dashboard FPS.ms شوید
۳. روی ربات "NONEcore-bot" کلیک کنید
۴. دکمه "🔄 Renew" را بزنید
۵. کپچا (اگر بود) را حل کنید
۶. تأیید کنید ✅

⚠️ اگر renewal نکنید، ربات خاموش می‌شود!
"""
    
    await update.message.reply_text(
        f"🔷 <b>NONEcore Admin Panel</b>\n\n"
        f"ربات مدیریت کانفیگ VPN\n"
        f"کانال: @nonecorebot\n\n"
        f"{renewal_msg}",
        parse_mode='HTML',
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'upload':
        await upload_start(update, context)
    elif data == 'stats':
        await stats_command(update, context)
    elif data == 'settings':
        await settings_command(update, context)
    elif data == 'toggle_reminder':
        await toggle_reminder(update, context)
    elif data == 'clients':
        await clients_command(update, context)

async def upload_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع آپلود"""
    user_id = str(update.effective_user.id)
    if user_id != Config.ADMIN_ID:
        return ConversationHandler.END
    
    await update.callback_query.message.reply_text(
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
    user_id = str(update.effective_user.id)
    if user_id != Config.ADMIN_ID:
        return ConversationHandler.END
    
    try:
        # دریافت فایل
        document = update.message.document
        file = await document.get_file()
        file_content = await file.download_as_bytearray()
        html_content = file_content.decode('utf-8', errors='ignore')
        
        await update.message.reply_text("✅ فایل دریافت شد. در حال پردازش...")
        
        # استخراج کانفیگ‌ها
        processor = ConfigProcessor()
        configs = processor.extract_from_html(html_content)
        
        if not configs:
            await update.message.reply_text("❌ هیچ کانفیگی در فایل یافت نشد.")
            return ConversationHandler.END
        
        await update.message.reply_text(f"🔄 {len(configs)} کانفیگ یافت شد. در حال ارسال...")
        
        # ارسال به کانال
        sender = ConfigSender(context.bot)
        channels = Config.CHANNELS.split(',')
        
        sent_count = 0
        duplicate_count = 0
        
        for config in configs:
            # چک تکراری
            if db.is_duplicate(config['link']):
                duplicate_count += 1
                continue
            
            # ذخیره در دیتابیس
            if db.add_config(config):
                # ارسال به کانال‌ها
                for channel in channels:
                    try:
                        await sender.send_config(channel.strip(), config)
                        sent_count += 1
                        
                        # آپدیت آمار
                        db.increment_daily(config['location'])
                        
                        # تاخیر برای جلوگیری از flood
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error sending to {channel}: {e}")
        
        # گزارش نهایی
        await update.message.reply_text(
            f"✅ پردازش تمام شد!\n\n"
            f"📤 ارسال شده: {sent_count}\n"
            f"🔄 تکراری: {duplicate_count}\n"
            f"❌ خطا: {len(configs) - sent_count - duplicate_count}"
        )
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        await update.message.reply_text(f"❌ خطا در پردازش: {str(e)}")
    
    return ConversationHandler.END

async def upload_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو آپلود"""
    await update.message.reply_text("❌ لغو شد.")
    return ConversationHandler.END

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """آمار"""
    user_id = str(update.effective_user.id)
    if user_id != Config.ADMIN_ID:
        return
    
    stats = db.get_stats()
    settings = db.get_all_settings()
    
    reminder_status = "✅ فعال" if settings.get('reminder_enabled', 'true') == 'true' else "❌ غیرفعال"
    
    await update.message.reply_text(
        f"📊 آمار {Config.BRAND_NAME}\n\n"
        f"📤 امروز: {stats['today']} کانفیگ\n"
        f"📈 کل: {stats['total']} کانفیگ\n\n"
        f"🔔 یادآوری renewal: {reminder_status}\n"
        f"📦 Batch size: {settings.get('batch_size', '10')}\n"
        f"⏱️ Batch interval: {settings.get('batch_interval', '120')}s\n"
        f"✅ Approval mode: {'روشن' if settings.get('approval_mode', 'false') == 'true' else 'خاموش'}\n"
        f"📱 ارسال کلاینت‌ها: {'روشن' if settings.get('send_clients', 'true') == 'true' else 'خاموش'}"
    )

async def channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کانال‌ها"""
    user_id = str(update.effective_user.id)
    if user_id != Config.ADMIN_ID:
        return
    
    channels = [c.strip() for c in Config.CHANNELS.split(',') if c.strip()]
    
    text = "📢 کانال‌های مقصد:\n\n"
    for i, ch in enumerate(channels, 1):
        text += f"{i}. {ch}\n"
    
    text += f"\n💡 برای تغییر، متغیر CHANNELS را در فایل .env ویرایش کنید."
    
    await update.message.reply_text(text)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیمات"""
    user_id = str(update.effective_user.id)
    if user_id != Config.ADMIN_ID:
        return
    
    settings = db.get_all_settings()
    
    keyboard = [
        [InlineKeyboardButton(f"ارسال کلاینت‌ها: {'✅' if settings.get('send_clients') == 'true' else '❌'}", callback_data='toggle_clients')],
        [InlineKeyboardButton(f"حالت تأییدیه: {'✅' if settings.get('approval_mode') == 'true' else '❌'}", callback_data='toggle_approval')],
        [InlineKeyboardButton(f"یادآوری renewal: {'✅' if settings.get('reminder_enabled') == 'true' else '❌'}", callback_data='toggle_reminder')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚙️ تنظیمات NONEcore\n\n"
        "روی هر گزینه کلیک کنید تا روشن/خاموش شود:",
        reply_markup=reply_markup
    )

async def toggle_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر وضعیت یادآوری"""
    query = update.callback_query
    current = db.get_setting('reminder_enabled', 'true')
    new_value = 'false' if current == 'true' else 'true'
    db.set_setting('reminder_enabled', new_value)
    
    await query.answer(f"یادآوری: {'فعال' if new_value == 'true' else 'غیرفعال'}")
    await start_command(update, context)

async def toggle_reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور خاموش/روشن یادآوری"""
    user_id = str(update.effective_user.id)
    if user_id != Config.ADMIN_ID:
        return
    
    current = db.get_setting('reminder_enabled', 'true')
    new_value = 'false' if current == 'true' else 'true'
    db.set_setting('reminder_enabled', new_value)
    
    await update.message.reply_text(
        f"🔔 یادآوری renewal: {'✅ فعال' if new_value == 'true' else '❌ غیرفعال'}"
    )

async def clients_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لیست کلاینت‌ها"""
    user_id = str(update.effective_user.id)
    if user_id != Config.ADMIN_ID:
        return
    
    sender = ConfigSender(context.bot)
    await sender.send_clients(user_id)

if __name__ == "__main__":
    main()
