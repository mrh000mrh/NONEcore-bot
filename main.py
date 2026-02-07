#!/usr/bin/env python3
"""
NONEcore Config Bot - نسخه کامل و نهایی
"""

import os
import logging
import asyncio
import io
import qrcode
from datetime import datetime, timedelta, time
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from config import Config
from bot.database import Database
from bot.processor import ConfigProcessor
from bot.sender import ConfigSender
from bot.keyboard import Keyboards

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# استیت‌ها
UPLOAD_FILE, UPLOAD_CONFIRM, SETTINGS_MENU, SETTING_VALUE, MANUAL_SEND = range(5)

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
                MessageHandler(filters.Regex('^⏱️ فاصله ارسال$'), set_interval_start),
                MessageHandler(filters.Regex('^🔢 تعداد هر batch$'), set_batch_start),
                MessageHandler(filters.Regex('^⏳ تأخیر باقیمانده$'), set_delay_start),
                MessageHandler(filters.Regex('^✅/❌ ارسال کلاینت‌ها$'), toggle_clients),
                MessageHandler(filters.Regex('^✅/❌ یادآوری renewal$'), toggle_reminder),
                MessageHandler(filters.Regex('^📢 مدیریت کانال‌ها$'), manage_channels),
            ],
            SETTING_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_setting_value)],
        },
        fallbacks=[MessageHandler(filters.Regex('^🔙 بازگشت$'), back_to_main)]
    )
    
    # کانورسیون ارسال دستی
    manual_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^📤 ارسال دستی باقیمانده$'), manual_send_start)],
        states={
            MANUAL_SEND: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_send_process)]
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(filters.Regex('^🔙 بازگشت$'), back_to_main)]
    )
    
    # هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(upload_conv)
    application.add_handler(settings_conv)
    application.add_handler(manual_conv)
    application.add_handler(MessageHandler(filters.Regex('^📊 آمار$'), stats))
    application.add_handler(MessageHandler(filters.Regex('^📱 کلاینت‌ها$'), clients))
    application.add_handler(MessageHandler(filters.Regex('^🔔 یادآوری$'), reminder_info))
    application.add_handler(MessageHandler(filters.Regex('^❓ راهنما$'), help_info))
    application.add_handler(MessageHandler(filters.Regex('^🔄 استارت مجدد$'), start))
    application.add_handler(CallbackQueryHandler(copy_config, pattern='^copy_'))
    application.add_handler(CallbackQueryHandler(report_bad, pattern='^bad_'))
    application.add_handler(CallbackQueryHandler(copy_group, pattern='^copy_group$'))
    
    # یادآوری renewal - هر 1.5 ساعت
    application.job_queue.run_repeating(reminder_job, interval=5400, first=10)
    
    # هشتگ لوکیشن - هر 6 ساعت
    application.job_queue.run_repeating(send_location_tags, interval=21600, first=300)
    
    # آمار روزانه - ساعت 23:59
    application.job_queue.run_daily(send_daily_stats, time=time(23, 59))
    
    # پاکسازی دیتابیس - ساعت 3:00 صبح
    application.job_queue.run_daily(cleanup_database, time=time(3, 0))
    
    application.run_polling()

@check_admin
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع"""
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی اصلی"""
    now = datetime.now()
    next_renewal = (now + timedelta(days=1)).replace(hour=Config.RENEWAL_HOUR, minute=0, second=0)
    hours_left = int((next_renewal - now).total_seconds() / 3600)
    reminder_on = db.get_setting('reminder_enabled', 'true') == 'true'
    
    # چک کردن کانفیگ‌های باقیمانده در صف
    pending_count = len(context.user_data.get('new_configs', []))
    pending_text = f"\n📋 کانفیگ در صف: {pending_count}" if pending_count > 0 else ""
    
    text = f"""🔷 <b>NONEcore Admin Panel</b>

⚡️ کانال: {Config.BRAND_CHANNEL}
🤖 ربات: {Config.BRAND_BOT}

⏰ <b>Renewal:</b> {hours_left} ساعت مانده
🔔 یادآوری: {'✅' if reminder_on else '❌'}{pending_text}

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
        
        await update.message.reply_text("✅ فایل دریافت شد. در حال پردازش...")
        
        processor = ConfigProcessor()
        configs = processor.extract_from_html(html_content)
        
        if not configs:
            await update.message.reply_text("❌ هیچ کانفیگی یافت نشد.", reply_markup=Keyboards.main_menu())
            return ConversationHandler.END
        
        context.user_data['configs'] = configs
        context.user_data['duplicate_count'] = 0
        new_configs = []
        
        for cfg in configs:
            if db.is_duplicate(cfg['link']):
                context.user_data['duplicate_count'] += 1
            else:
                new_configs.append(cfg)
        
        context.user_data['new_configs'] = new_configs
        
        batch_size = int(db.get_setting('batch_size', '5'))
        interval = int(db.get_setting('interval', '10'))
        
        text = f"""📊 <b>نتیجه اسکن:</b>

🔍 کل یافت شده: {len(configs)}
✅ جدید: {len(new_configs)}
🔄 تکراری: {context.user_data['duplicate_count']}

⚙️ <b>تنظیمات فعلی:</b>
• تعداد هر batch: {batch_size}
• فاصله: {interval} ثانیه

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
    
    # ارسال با تابع مشترک
    success = await send_configs_batch(update, context, configs)
    
    if success:
        # پاک کردن صف
        context.user_data['new_configs'] = []
        context.user_data['configs'] = []
    
    return ConversationHandler.END

async def send_configs_batch(update: Update, context: ContextTypes.DEFAULT_TYPE, configs: list) -> bool:
    """ارسال دسته‌ای کانفیگ‌ها - تابع مشترک"""
    batch_size = int(db.get_setting('batch_size', '5'))
    interval = int(db.get_setting('interval', '10'))
    delay = int(db.get_setting('delay', '300'))
    
    total = len(configs)
    batches = [configs[i:i+batch_size] for i in range(0, len(configs), batch_size)]
    
    await update.message.reply_text(
        f"🔄 در حال ارسال {total} کانفیگ در {len(batches)} batch...",
        reply_markup=Keyboards.remove_keyboard()
    )
    
    sender = ConfigSender(context.bot)
    channels = db.get_channels()
    sent = 0
    
    for i, batch in enumerate(batches):
        for cfg in batch:
            if db.add_config(cfg):
                for ch in channels:
                    try:
                        msg_id = await sender.send_config(ch, cfg)
                        sent += 1
                        db.increment_daily(cfg['location'])
                        
                        # ذخیره اطلاعات پیام برای گزارش خرابی
                        cfg['channel_id'] = ch
                        cfg['message_id'] = msg_id
                        
                    except Exception as e:
                        logger.error(f"Send error to {ch}: {e}")
        
        if i < len(batches) - 1:
            await update.message.reply_text(
                f"✅ Batch {i+1}/{len(batches)} ارسال شد. "
                f"تأخیر {delay} ثانیه برای batch بعدی..."
            )
            await asyncio.sleep(delay)
        else:
            await asyncio.sleep(interval)
    
    await update.message.reply_text(
        f"✅ <b>تمام شد!</b>\n\n"
        f"📤 ارسال شده: {sent}\n"
        f"❌ خطا: {total - sent}",
        parse_mode='HTML',
        reply_markup=Keyboards.main_menu()
    )
    
    return sent > 0

@check_admin
async def manual_send_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ارسال دستی"""
    pending = context.user_data.get('new_configs', [])
    
    if not pending:
        await update.message.reply_text(
            "❌ کانفیگی در صف نیست.\n\n"
            "ابتدا فایل HTML آپلود کنید.",
            reply_markup=Keyboards.main_menu()
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"📤 <b>ارسال دستی باقیمانده</b>\n\n"
        f"تعداد کل در صف: {len(pending)}\n\n"
        f"چه تعداد ارسال شود؟ (عدد وارد کنید)",
        parse_mode='HTML',
        reply_markup=Keyboards.remove_keyboard()
    )
    return MANUAL_SEND

@check_admin
async def manual_send_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش ارسال دستی"""
    try:
        count = int(update.message.text.strip())
        pending = context.user_data.get('new_configs', [])
        
        if count <= 0:
            await update.message.reply_text("❌ عدد باید بزرگتر از 0 باشد.")
            return MANUAL_SEND
        
        if count > len(pending):
            count = len(pending)
        
        # گرفتن تعداد مشخص شده
        to_send = pending[:count]
        remaining = pending[count:]
        
        await update.message.reply_text(f"🔄 در حال ارسال {count} کانفیگ...")
        
        # ارسال
        success = await send_configs_batch(update, context, to_send)
        
        if success:
            # به‌روزرسانی صف
            context.user_data['new_configs'] = remaining
            
            if remaining:
                await update.message.reply_text(
                    f"📋 <b>{len(remaining)} کانفیگ</b> هنوز در صف باقی مانده.\n"
                    f"می‌توانید دوباره ارسال دستی کنید.",
                    parse_mode='HTML'
                )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ لطفاً عدد وارد کنید.")
        return MANUAL_SEND

@check_admin
async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی تنظیمات"""
    settings = {
        'batch_size': db.get_setting('batch_size', '5'),
        'interval': db.get_setting('interval', '10'),
        'delay': db.get_setting('delay', '300'),
        'send_clients': db.get_setting('send_clients', 'true') == 'true',
        'reminder_enabled': db.get_setting('reminder_enabled', 'true') == 'true',
    }
    
    text = f"""⚙️ <b>تنظیمات فعلی:</b>

⏱️ فاصله ارسال: {settings['interval']} ثانیه
🔢 تعداد هر batch: {settings['batch_size']}
⏳ تأخیر باقیمانده: {settings['delay']} ثانیه
📱 ارسال کلاینت‌ها: {'✅' if settings['send_clients'] else '❌'}
🔔 یادآوری renewal: {'✅' if settings['reminder_enabled'] else '❌'}

روی گزینه‌ها کلیک کنید:"""
    
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=Keyboards.settings_menu())
    return SETTINGS_MENU

async def set_interval_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیم فاصله"""
    context.user_data['setting'] = 'interval'
    await update.message.reply_text("⏱️ فاصله جدید را به ثانیه وارد کنید (مثلاً: 10):")
    return SETTING_VALUE

async def set_batch_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیم batch"""
    context.user_data['setting'] = 'batch_size'
    await update.message.reply_text("🔢 تعداد هر batch را وارد کنید (مثلاً: 5):")
    return SETTING_VALUE

async def set_delay_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیم تأخیر"""
    context.user_data['setting'] = 'delay'
    await update.message.reply_text("⏳ تأخیر باقیمانده را به ثانیه وارد کنید (مثلاً: 300):")
    return SETTING_VALUE

async def process_setting_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش مقدار تنظیم"""
    setting = context.user_data.get('setting')
    value = update.message.text.strip()
    
    try:
        int(value)
        db.set_setting(setting, value)
        
        names = {
            'interval': 'فاصله ارسال',
            'batch_size': 'تعداد هر batch',
            'delay': 'تأخیر باقیمانده'
        }
        
        await update.message.reply_text(
            f"✅ <b>{names.get(setting, setting)}</b> به <b>{value}</b> تغییر یافت.",
            parse_mode='HTML'
        )
    except ValueError:
        await update.message.reply_text("❌ لطفاً عدد وارد کنید.")
    
    return await settings_menu(update, context)

async def toggle_clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر ارسال کلاینت‌ها"""
    new_val = db.toggle_setting('send_clients')
    status = "فعال" if new_val else "غیرفعال"
    await update.message.reply_text(f"✅ ارسال کلاینت‌ها: {status}")
    return await settings_menu(update, context)

async def toggle_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر یادآوری"""
    new_val = db.toggle_setting('reminder_enabled')
    status = "فعال" if new_val else "غیرفعال"
    await update.message.reply_text(f"🔔 یادآوری renewal: {status}")
    return await settings_menu(update, context)

async def manage_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کانال‌ها"""
    channels = db.get_channels()
    text = "📢 کانال‌های فعلی:\n\n" + "\n".join([f"• {c}" for c in channels])
    text += f"\n\n💡 برای تغییر، در فایل .env ویرایش کنید."
    await update.message.reply_text(text)
    return SETTINGS_MENU

@check_admin
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """آمار"""
    stats = db.get_stats()
    pending = len(context.user_data.get('new_configs', []))
    
    text = f"""📊 <b>آمار NONEcore</b>

📤 امروز: {stats['today']} کانفیگ
📈 کل: {stats['total']} کانفیگ
📋 در صف: {pending} کانفیگ

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
همه پارامترها قابل تغییر از داخل ربات است.

📊 <b>آمار:</b>
مشاهده تعداد کانفیگ‌های ارسال شده.

📤 <b>ارسال دستی:</b>
ارسال کانفیگ‌های باقیمانده در صف.

🔔 <b>یادآوری:</b>
اطلاعات renewal سرور.

🔄 <b>استارت مجدد:</b>
ری‌استارت کردن ربات بدون دستور.

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

async def copy_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کپی کانفیگ"""
    query = update.callback_query
    config_id = query.data.replace('copy_', '')
    config = db.get_config_by_id(config_id)
    
    if config:
        await query.answer("کپی شد!")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"📋 <code>{config['link']}</code>",
            parse_mode='HTML'
        )
    else:
        await query.answer("خطا!")

async def report_bad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """گزارش خرابی"""
    query = update.callback_query
    config_id = query.data.replace('bad_', '')
    
    reports = db.increment_bad_report(config_id)
    
    if reports >= 10:
        config = db.get_config_by_id(config_id)
        if config:
            try:
                await context.bot.delete_message(
                    chat_id=config['channel_id'],
                    message_id=config['message_id']
                )
                db.delete_config(config_id)
                await query.answer("این کانفیگ حذف شد.")
            except:
                await query.answer("خطا در حذف.")
    else:
        await query.answer(f"گزارش ثبت شد. ({reports}/10)")

async def copy_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کپی گروهی"""
    query = update.callback_query
    
    configs = db.get_last_configs(20)
    links = [c['link'] for c in configs]
    
    text = "📋 <b>۲۰ کانفیگ آخر:</b>\n\n" + "\n".join(links)
    
    await query.answer("کپی شد!")
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        parse_mode='HTML'
    )

async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    """یادآوری renewal"""
    if db.get_setting('reminder_enabled', 'true') != 'true':
        return
    
    now = datetime.now()
    next_renewal = (now + timedelta(days=1)).replace(hour=Config.RENEWAL_HOUR, minute=0, second=0)
    hours_left = int((next_renewal - now).total_seconds() / 3600)
    
    if hours_left <= 6:
        await context.bot.send_message(
            chat_id=Config.ADMIN_ID,
            text=f"⏰ <b>یادآوری Renewal</b>\n\n"
                 f"🔄 {hours_left} ساعت مانده تا renewal.\n"
                 f"🔗 <a href='{Config.FPS_RENEWAL_URL}'>کلیک کنید</a>",
            parse_mode='HTML'
        )

async def send_location_tags(context: ContextTypes.DEFAULT_TYPE):
    """ارسال هشتگ لوکیشن"""
    stats = db.get_stats()
    locations = list(stats['locations'].keys())[:10]
    
    hashtags = " ".join([f"#{loc.replace(' ', '_')}" for loc in locations])
    
    for channel in db.get_channels():
        try:
            await context.bot.send_message(
                chat_id=channel,
                text=f"🔍 <b>جستجو بر اساس لوکیشن:</b>\n\n{hashtags}\n\n⚡️ @nonecorebot",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error sending tags: {e}")

async def send_daily_stats(context: ContextTypes.DEFAULT_TYPE):
    """آمار روزانه"""
    stats = db.get_stats()
    
    if db.get_setting('send_clients', 'true') == 'true':
        sender = ConfigSender(context.bot)
        
        for channel in db.get_channels():
            try:
                loc_text = ""
                for loc, count in sorted(stats['locations'].items(), key=lambda x: x[1], reverse=True)[:5]:
                    loc_text += f"{loc}({count}) "
                
                text = f"""📊 <b>آمار امروز</b>

📤 {stats['today']} کانفیگ
📈 {stats['total']} کل

🌍 {loc_text}

⚡️ @nonecorebot"""
                
                await context.bot.send_message(chat_id=channel, text=text, parse_mode='HTML')
                
                await sender.send_clients(channel)
                
            except Exception as e:
                logger.error(f"Error daily stats: {e}")

async def cleanup_database(context: ContextTypes.DEFAULT_TYPE):
    """پاکسازی دیتابیس"""
    deleted = db.cleanup_old_configs(3)
    duplicates = db.remove_duplicates()
    
    logger.info(f"Cleanup: {deleted} old, {duplicates} duplicates removed")

if __name__ == "__main__":
    main()