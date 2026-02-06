#!/usr/bin/env python3
"""
NONEcore Config Bot - نسخه کامل و نهایی
"""

import os
import logging
import asyncio
import io
import qrcode
from datetime import datetime, timedelta
from telegram import Update, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)
from config import Config
from bot.database import Database
from bot.processor import ConfigProcessor
from bot.sender import ConfigSender
from bot.keyboard import Keyboards

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# استیت‌ها
UPLOAD_FILE, UPLOAD_CONFIRM, SETTINGS_MENU, ADD_CHANNEL, REMOVE_CHANNEL = range(5)

db = Database()

def check_admin(func):
    """دکوراتور چک ادمین"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        if user_id != Config.ADMIN_ID:
            if update.message:
                await update.message.reply_text("⛔ شما ادمین نیستید.")
            return
        return await func(update, context)
    return wrapper

def main():
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # کانورسیون آپلود
    upload_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^📤 آپلود HTML$'), upload_start)],
        states={
            UPLOAD_FILE: [MessageHandler(filters.Document.ALL, upload_receive)],
            UPLOAD_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, upload_confirm)]
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(filters.Regex('^🔙 بازگشت$'), back_to_main)]
    )
    
    # کانورسیون تنظیمات
    settings_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^⚙️ تنظیمات$'), settings_menu)],
        states={
            SETTINGS_MENU: [
                MessageHandler(filters.Regex('^✅/❌ ارسال کلاینت‌ها$'), toggle_clients),
                MessageHandler(filters.Regex('^✅/❌ حالت تأییدیه$'), toggle_approval),
                MessageHandler(filters.Regex('^✅/❌ یادآوری renewal$'), toggle_reminder),
                MessageHandler(filters.Regex('^🔢 تغییر batch size$'), change_batch),
                MessageHandler(filters.Regex('^⏱️ تغییر فاصله$'), change_interval),
                MessageHandler(filters.Regex('^📢 مدیریت کانال‌ها$'), manage_channels),
            ],
            ADD_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_channel)],
            REMOVE_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_channel)],
        },
        fallbacks=[MessageHandler(filters.Regex('^🔙 بازگشت$'), back_to_main)]
    )
    
    # هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(upload_conv)
    application.add_handler(settings_conv)
    application.add_handler(MessageHandler(filters.Regex('^📊 آمار$'), stats))
    application.add_handler(MessageHandler(filters.Regex('^📱 کلاینت‌ها$'), clients))
    application.add_handler(MessageHandler(filters.Regex('^🔔 یادآوری$'), reminder_info))
    application.add_handler(MessageHandler(filters.Regex('^❓ راهنما$'), help_info))
    
    application.run_polling()

@check_admin
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع"""
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی اصلی"""
    # محاسبه renewal
    now = datetime.now()
    next_renewal = (now + timedelta(days=1)).replace(hour=Config.RENEWAL_HOUR, minute=0, second=0)
    hours_left = int((next_renewal - now).total_seconds() / 3600)
    
    reminder_on = db.get_setting('reminder_enabled', 'true') == 'true'
    
    text = f"""🔷 <b>NONEcore Admin Panel</b>

⚡️ کانال: {Config.BRAND_CHANNEL}
🤖 ربات: {Config.BRAND_BOT}

⏰ <b>Renewal:</b> {hours_left} ساعت مانده
🔔 یادآوری: {'✅' if reminder_on else '❌'}

از دکمه‌های زیر استفاده کنید:"""
    
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=Keyboards.main_menu())

@check_admin
async def upload_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع آپلود"""
    await update.message.reply_text(
        "📁 فایل HTML را ارسال کنید:\n\n"
        "راهنما: Telegram Desktop → کانال → Export chat history → HTML",
        reply_markup=Keyboards.remove_keyboard()
    )
    return UPLOAD_FILE

@check_admin
async def upload_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت فایل"""
    try:
        document = update.message.document
        if not document.file_name.endswith('.html'):
            await update.message.reply_text("❌ فقط فایل HTML قبول است.")
            return UPLOAD_FILE
        
        file = await document.get_file()
        file_content = await file.download_as_bytearray()
        html_content = file_content.decode('utf-8', errors='ignore')
        
        # استخراج کانفیگ‌ها
        processor = ConfigProcessor()
        configs = processor.extract_from_html(html_content)
        
        if not configs:
            await update.message.reply_text("❌ هیچ کانفیگی یافت نشد.", reply_markup=Keyboards.main_menu())
            return ConversationHandler.END
        
        # ذخیره موقت
        context.user_data['configs'] = configs
        context.user_data['duplicate_count'] = 0
        
        # شمارش تکراری‌ها
        new_configs = []
        for cfg in configs:
            if db.is_duplicate(cfg['link']):
                context.user_data['duplicate_count'] += 1
            else:
                new_configs.append(cfg)
        
        context.user_data['new_configs'] = new_configs
        
        text = f"""📊 <b>نتیجه اسکن:</b>

🔍 کل یافت شده: {len(configs)}
✅ جدید: {len(new_configs)}
🔄 تکراری: {context.user_data['duplicate_count']}

آیا ارسال شود؟"""
        
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=Keyboards.upload_confirm())
        return UPLOAD_CONFIRM
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        await update.message.reply_text(f"❌ خطا: {str(e)}", reply_markup=Keyboards.main_menu())
        return ConversationHandler.END

@check_admin
async def upload_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأیید آپلود"""
    text = update.message.text
    
    if 'لغو' in text or 'بازگشت' in text:
        await update.message.reply_text("❌ لغو شد.", reply_markup=Keyboards.main_menu())
        return ConversationHandler.END
    
    if 'تأیید' not in text:
        return UPLOAD_CONFIRM
    
    configs = context.user_data.get('new_configs', [])
    if not configs:
        await update.message.reply_text("❌ کانفیگ جدیدی برای ارسال نیست.", reply_markup=Keyboards.main_menu())
        return ConversationHandler.END
    
    await update.message.reply_text(f"🔄 در حال ارسال {len(configs)} کانفیگ...", reply_markup=Keyboards.remove_keyboard())
    
    # ارسال
    sender = ConfigSender(context.bot)
    channels = db.get_channels()
    sent = 0
    
    for cfg in configs:
        if db.add_config(cfg):
            for ch in channels:
                try:
                    await sender.send_config(ch, cfg)
                    sent += 1
                    db.increment_daily(cfg['location'])
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Send error: {e}")
    
    # گزارش
    await update.message.reply_text(
        f"✅ <b>تمام شد!</b>\n\n"
        f"📤 ارسال شده: {sent}\n"
        f"🔄 تکراری: {context.user_data.get('duplicate_count', 0)}",
        parse_mode='HTML',
        reply_markup=Keyboards.main_menu()
    )
    
    return ConversationHandler.END

@check_admin
async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی تنظیمات"""
    settings = {
        'send_clients': db.get_setting('send_clients', 'true') == 'true',
        'approval_mode': db.get_setting('approval_mode', 'false') == 'true',
        'reminder_enabled': db.get_setting('reminder_enabled', 'true') == 'true',
        'batch_size': db.get_setting('batch_size', '10'),
        'batch_interval': db.get_setting('batch_interval', '120')
    }
    
    text = f"""⚙️ <b>تنظیمات فعلی:</b>

📱 ارسال کلاینت‌ها: {'✅' if settings['send_clients'] else '❌'}
✅ حالت تأییدیه: {'✅' if settings['approval_mode'] else '❌'}
🔔 یادآوری renewal: {'✅' if settings['reminder_enabled'] else '❌'}
🔢 Batch size: {settings['batch_size']}
⏱️ فاصله: {settings['batch_interval']} ثانیه

روی گزینه‌ها کلیک کنید:"""
    
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=Keyboards.settings_menu())
    return SETTINGS_MENU

async def toggle_clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر ارسال کلاینت‌ها"""
    new_val = db.toggle_setting('send_clients')
    await update.message.reply_text(f"📱 ارسال کلاینت‌ها: {'✅ فعال' if new_val else '❌ غیرفعال'}")
    return await settings_menu(update, context)

async def toggle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر حالت تأییدیه"""
    new_val = db.toggle_setting('approval_mode')
    await update.message.reply_text(f"✅ حالت تأییدیه: {'✅ فعال' if new_val else '❌ غیرفعال'}")

async def toggle_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر یادآوری"""
    new_val = db.toggle_setting('reminder_enabled')
    await update.message.reply_text(f"🔔 یادآوری renewal: {'✅ فعال' if new_val else '❌ غیرفعال'}")

async def change_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر batch size"""
    await update.message.reply_text("🔢 عدد جدید batch size را وارد کنید (مثلاً: 5):")
    # TODO: دریافت مقدار
    return SETTINGS_MENU

async def change_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر فاصله"""
    await update.message.reply_text("⏱️ فاصله جدید را به ثانیه وارد کنید (مثلاً: 60):")
    # TODO: دریافت مقدار
    return SETTINGS_MENU

async def manage_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کانال‌ها"""
    channels = db.get_channels()
    text = "📢 کانال‌های فعلی:\n\n" + "\n".join([f"• {c}" for c in channels])
    text += "\n\nبرای اضافه کردن: /addchannel @channel\nبرای حذف: /removechannel @channel"
    await update.message.reply_text(text)

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اضافه کردن کانال"""
    text = update.message.text.strip()
    if text.startswith('@'):
        if db.add_channel(text):
            await update.message.reply_text(f"✅ کانال {text} اضافه شد.")
        else:
            await update.message.reply_text("❌ خطا در اضافه کردن.")
    else:
        await update.message.reply_text("❌ فرمت اشتباه. با @ شروع کنید.")
    return SETTINGS_MENU

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف کانال"""
    text = update.message.text.strip()
    if db.remove_channel(text):
        await update.message.reply_text(f"✅ کانال {text} حذف شد.")
    else:
        await update.message.reply_text("❌ خطا در حذف.")
    return SETTINGS_MENU

@check_admin
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """آمار"""
    stats = db.get_stats()
    settings = db.get_all_settings()
    
    text = f"""📊 <b>آمار NONEcore</b>

📤 امروز: {stats['today']} کانفیگ
📈 کل: {stats['total']} کانفیگ

🌍 لوکیشن‌های امروز:"""
    
    for loc, count in sorted(stats['locations'].items(), key=lambda x: x[1], reverse=True)[:5]:
        text += f"\n• {loc}: {count}"
    
    await update.message.reply_text(text, parse_mode='HTML')

@check_admin
async def clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کلاینت‌ها"""
    text = """📱 <b>کلاینت‌های پیشنهادی:</b>

🤖 <b>اندروید:</b>
• V2RayNG - github.com/2dust/v2rayNG
• SagerNet - github.com/SagerNet/SagerNet

🍎 <b>iOS:</b>
• Streisand - App Store
• Shadowrocket - App Store

💻 <b>ویندوز:</b>
• v2rayN - github.com/2dust/v2rayN
• Nekoray - github.com/MatsuriDayo/nekoray

🐧 <b>لینوکس/macOS:</b>
• Nekoray - github.com/MatsuriDayo/nekoray

🔒 <b>فیلترشکن‌های ضدسانسور:</b>
• Psiphon - psiphon.ca
• Tor Browser - torproject.org
• Tails - tails.boum.org
• Lantern - getlantern.org
• Outline - getoutline.org

⚡️ @nonecorebot"""
    
    await update.message.reply_text(text, parse_mode='HTML')

@check_admin
async def reminder_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اطلاعات renewal"""
    text = f"""⏰ <b>یادآوری Renewal</b>

🔄 هر ۲۴ ساعت یکبار باید renewal کنید.

📋 <b>آموزش:</b>
۱. به <a href="{Config.FPS_RENEWAL_URL}">FPS.ms</a> بروید
۲. روی NONEcore-bot کلیک کنید
۳. دکمه "🔄 Renew" را بزنید
۴. کپچا را حل کنید
۵. تأیید کنید ✅

⚠️ اگر renewal نکنید، ربات خاموش می‌شود!"""
    
    await update.message.reply_text(text, parse_mode='HTML', disable_web_page_preview=True)

@check_admin
async def help_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنما"""
    text = """❓ <b>راهنمای NONEcore Bot</b>

📤 <b>آپلود HTML:</b>
فایل Export شده از کانال تلگرام را ارسال کنید.

⚙️ <b>تنظیمات:</b>
همه پارامترها را می‌توانید از داخل ربات تغییر دهید.

📊 <b>آمار:</b>
مشاهده تعداد کانفیگ‌های ارسال شده.

🔔 <b>یادآوری:</b>
اطلاعات renewal سرور.

⚡️ @nonecorebot"""
    
    await update.message.reply_text(text, parse_mode='HTML')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو"""
    await update.message.reply_text("❌ لغو شد.", reply_markup=Keyboards.main_menu())
    return ConversationHandler.END

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازگشت به منوی اصلی"""
    await show_main_menu(update, context)
    return ConversationHandler.END

if __name__ == "__main__":
    main()
