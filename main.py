import os
import sys
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

from config import Config
from database import Database
from processor import ConfigProcessor
from sender import Sender
from keyboard import Keyboard

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO if not Config.DEBUG else logging.DEBUG
)
logger = logging.getLogger(__name__)

# States for ConversationHandler
SET_INTERVAL, SET_BATCH, SET_DELAY, SET_DAILY_LIMIT, CUSTOM_SEND = range(5)

class NonecoreBot:
    def __init__(self):
        self.config = Config()
        self.db = Database(self.config.DATABASE_PATH)
        self.processor = ConfigProcessor()
        self.sender = Sender(self.config)
        self.keyboard = Keyboard()
        self.application = None
    
    async def init(self):
        await self.db.init()
        await self.db.sync_channels_from_env(self.config.CHANNELS)
        logger.info("Database initialized")
    
    def run(self):
        self.application = Application.builder().token(self.config.BOT_TOKEN).build()
        
        self.application.bot_data['db'] = self.db
        self.application.bot_data['config'] = self.config
        self.application.bot_data['sender'] = self.sender
        self.application.bot_data['keyboard'] = self.keyboard
        self.application.bot_data['processor'] = self.processor
        
        conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.set_interval_callback, pattern='^set_interval$'),
                CallbackQueryHandler(self.set_batch_callback, pattern='^set_batch$'),
                CallbackQueryHandler(self.set_delay_callback, pattern='^set_delay$'),
                CallbackQueryHandler(self.set_daily_limit_callback, pattern='^set_daily_limit$'),
                CallbackQueryHandler(self.custom_send_callback, pattern='^custom_send$'),
            ],
            states={
                SET_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.save_interval)],
                SET_BATCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.save_batch)],
                SET_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.save_delay)],
                SET_DAILY_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.save_daily_limit)],
                CUSTOM_SEND: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.do_custom_send)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )
        
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('help', self.help_command))
        self.application.add_handler(CommandHandler('stats', self.stats_command))
        self.application.add_handler(conv_handler)
        
        self.application.add_handler(MessageHandler(filters.Document.FileExtension("html"), self.handle_html))
        
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    def is_admin(self, user_id: int) -> bool:
        return user_id == self.config.ADMIN_ID
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("⛔ شما دسترسی ندارید.")
            return
        
        await update.message.reply_text(
            f"👋 خوش آمدید به {self.config.BRAND_NAME} Bot\n\n"
            "از منوی زیر انتخاب کنید:",
            reply_markup=self.keyboard.main_menu()
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            return
        
        help_text = """
📖 راهنمای ربات:

📤 آپلود HTML - آپلود فایل HTML اکسپورت شده از کانال
📊 آمار - مشاهده آمار کامل کانال و کانفیگ‌ها
📤 ارسال دستی - ارسال سریع یا دستی کانفیگ‌های در صف
📱 کلاینت‌ها - دریافت لینک کلاینت‌های پیشنهادی
⚙️ تنظیمات - تغییر تنظیمات ربات
🔔 یادآوری - تنظیم یادآوری تمدید سرور
🔄 استارت مجدد - راه‌اندازی مجدد ربات
⛔ توقف ارسال - توقف فوری ارسال کانفیگ‌ها

⚠️ نکات مهم:
• فایل HTML باید از کانال تلگرام اکسپورت شده باشد
• حداکثر حجم فایل: 10 مگابایت
• کانفیگ‌ها به صورت رندوم ارسال می‌شوند
• محدودیت روزانه: 200 کانفیگ
        """
        await update.message.reply_text(help_text, reply_markup=self.keyboard.back_button())
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            return
        
        stats = await self.db.get_admin_stats()
        text = self.sender.format_admin_stats(stats)
        await update.message.reply_text(text, reply_markup=self.keyboard.back_button())
    
    async def handle_html(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            return
        
        document = update.message.document
        
        if document.file_size > self.config.MAX_HTML_SIZE:
            await update.message.reply_text("❌ فایل بیش از حد بزرگ است. حداکثر 10 مگابایت.")
            return
        
        processing_msg = await update.message.reply_text("⏳ در حال پردازش فایل...")
        
        try:
            file = await document.get_file()
            file_path = f"/tmp/{document.file_name}"
            await file.download_to_drive(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            configs = self.processor.extract_from_html(html_content)
            
            os.remove(file_path)
            
            if not configs:
                await processing_msg.edit_text("❌ هیچ کانفیگی یافت نشد.")
                return
            
            daily_limit = int(await self.db.get_setting('daily_limit', self.config.DAILY_LIMIT))
            daily_sent = await self.db.get_daily_sent_count()
            remaining_today = max(0, daily_limit - daily_sent)
            
            if len(configs) > remaining_today:
                queued = configs[remaining_today:]
                configs = configs[:remaining_today]
                await self.db.add_to_queue(queued)
                await update.message.reply_text(
                    f"⚠️ محدودیت امروز ({daily_limit}) رسید. "
                    f"{len(queued)} کانفیگ به فردا موکول شد."
                )
            
            for cfg in configs:
                cfg['message_id'] = None
                cfg['channel_id'] = None
                cfg['sent_at'] = None
                await self.db.add_config(cfg)
            
            await processing_msg.edit_text(
                f"✅ {len(configs)} کانفیگ استخراج و به صف اضافه شد.\n"
                f"📋 {await self.db.get_queue_count()} کانفیگ در صف\n"
                f"⚡ برای ارسال از دکمه 'ارسال دستی' استفاده کنید."
            )
            
        except Exception as e:
            logger.error(f"Error processing HTML: {e}")
            await processing_msg.edit_text(f"❌ خطا در پردازش: {str(e)}")
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        db = context.bot_data['db']
        
        if data == 'main_menu':
            await query.edit_message_text(
                "از منوی زیر انتخاب کنید:",
                reply_markup=self.keyboard.main_menu()
            )
        
        elif data == 'upload_html':
            await query.edit_message_text(
                "📤 لطفاً فایل HTML را ارسال کنید.\n\n"
                "⚠️ فایل باید از کانال تلگرام اکسپورت شده باشد.",
                reply_markup=self.keyboard.back_button()
            )
        
        elif data == 'stats':
            stats = await db.get_admin_stats()
            text = self.sender.format_admin_stats(stats)
            await query.edit_message_text(text, reply_markup=self.keyboard.back_button())
        
        elif data == 'manual_send':
            queue_count = await db.get_queue_count()
            settings = {
                'batch_size': await db.get_setting('batch_size', '5'),
                'interval': await db.get_setting('interval', '120'),
                'delay': await db.get_setting('delay', '0')
            }
            status_text = self.sender.format_queue_status(queue_count, int(settings['batch_size']), 
                                                          int(settings['interval']), int(settings['delay']))
            await query.edit_message_text(
                f"{status_text}\n\nروش ارسال را انتخاب کنید:",
                reply_markup=self.keyboard.manual_send_menu()
            )
        
        elif data == 'quick_send_10':
            await self.quick_send(update, context, 10)
        
        elif data == 'custom_send':
            return  # Handled by ConversationHandler
        
        elif data == 'clients':
            await query.edit_message_text(
                "📱 کلاینت‌های پیشنهادی:",
                reply_markup=self.keyboard.clients_menu()
            )
        
        elif data == 'settings':
            settings = {
                'interval': await db.get_setting('interval', '120'),
                'batch_size': await db.get_setting('batch_size', '5'),
                'delay': await db.get_setting('delay', '0'),
                'send_clients': await db.get_setting('send_clients', 'true'),
                'reminder_enabled': await db.get_setting('reminder_enabled', 'true'),
                'daily_limit': await db.get_setting('daily_limit', '200')
            }
            text = self.sender.format_settings(settings)
            await query.edit_message_text(text, reply_markup=self.keyboard.settings_menu())
        
        elif data == 'reminder':
            current = await db.get_setting('reminder_enabled', 'true')
            new_val = 'false' if current == 'true' else 'true'
            await db.set_setting('reminder_enabled', new_val)
            status = '✅ فعال' if new_val == 'true' else '❌ غیرفعال'
            await query.edit_message_text(
                f"🔔 یادآوری renewal {status} شد.",
                reply_markup=self.keyboard.back_button()
            )
        
        elif data == 'restart':
            await query.edit_message_text("🔄 در حال راه‌اندازی مجدد...")
            await self.notify_admin(context, "🔄 ربات توسط ادمین ری‌استارت شد.")
            os._exit(0)
        
        elif data == 'stop_sending':
            current = await db.get_setting('stop_sending', 'false')
            new_val = 'true' if current == 'false' else 'false'
            await db.set_setting('stop_sending', new_val)
            
            if new_val == 'true':
                queue = await db.get_queue_count()
                await query.edit_message_text(
                    f"⛔ ارسال متوقف شد. {queue} کانفیگ در صف مانده.",
                    reply_markup=self.keyboard.back_button()
                )
            else:
                await query.edit_message_text(
                    "✅ ارسال از سر گرفته شد.",
                    reply_markup=self.keyboard.back_button()
                )
        
        elif data == 'help':
            await self.show_help(query)
        
        elif data == 'toggle_clients':
            current = await db.get_setting('send_clients', 'true')
            new_val = 'false' if current == 'true' else 'true'
            await db.set_setting('send_clients', new_val)
            status = '✅ فعال' if new_val == 'true' else '❌ غیرفعال'
            await query.edit_message_text(
                f"📱 ارسال کلاینت‌ها {status} شد.",
                reply_markup=self.keyboard.back_button()
            )
        
        elif data == 'toggle_reminder':
            current = await db.get_setting('reminder_enabled', 'true')
            new_val = 'false' if current == 'true' else 'true'
            await db.set_setting('reminder_enabled', new_val)
            status = '✅ فعال' if new_val == 'true' else '❌ غیرفعال'
            await query.edit_message_text(
                f"🔔 یادآوری renewal {status} شد.",
                reply_markup=self.keyboard.back_button()
            )
        
        elif data == 'manage_channels':
            channels = await db.get_channels()
            text = "📢 کانال‌های فعال:\n" + "\n".join([f"• {ch}" for ch in channels])
            await query.edit_message_text(text, reply_markup=self.keyboard.back_button())
        
        elif data.startswith('copy_'):
            uuid = data.replace('copy_', '')
            await db.increment_copy_count(uuid)
            await query.answer("✅ کپی شد!", show_alert=False)
        
        elif data.startswith('report_'):
            uuid = data.replace('report_', '')
            await query.edit_message_reply_markup(
                reply_markup=self.keyboard.confirm_report(uuid)
            )
        
        elif data.startswith('confirm_report_'):
            uuid = data.replace('confirm_report_', '')
            new_count = await db.increment_bad_report(uuid)
            await query.answer("✅ گزارش ثبت شد", show_alert=True)
            
            if await db.should_delete_config(uuid):
                await self.delete_config(context, uuid)
                await query.edit_message_text("❌ کانفیگ به دلیل گزارش‌های متعدد حذف شد.")
            else:
                await query.edit_message_text(
                    f"⚠️ گزارش خرابی ثبت شد. ({new_count}/5)",
                    reply_markup=self.keyboard.back_button()
                )
        
        elif data.startswith('cancel_report_'):
            uuid = data.replace('cancel_report_', '')
            cfg = await db.get_config_by_uuid(uuid)
            if cfg:
                await query.edit_message_reply_markup(
                    reply_markup=self.keyboard.config_buttons(uuid)
                )
    
    async def quick_send(self, update: Update, context: ContextTypes.DEFAULT_TYPE, count: int):
        query = update.callback_query
        db = context.bot_data['db']
        
        stop_sending = await db.get_setting('stop_sending', 'false')
        if stop_sending == 'true':
            await query.edit_message_text(
                "⛔ ارسال در حال حاضر متوقف است.",
                reply_markup=self.keyboard.back_button()
            )
            return
        
        configs = await db.get_pending_configs(limit=count)
        if not configs:
            await query.edit_message_text(
                "❌ هیچ کانفیگی در صف نیست.",
                reply_markup=self.keyboard.back_button()
            )
            return
        
        await query.edit_message_text(f"⏳ در حال ارسال {len(configs)} کانفیگ...")
        
        await self.send_configs_batch(context, configs)
        
        remaining = await db.get_queue_count()
        await query.edit_message_text(
            f"✅ {len(configs)} کانفیگ ارسال شد.\n"
            f"📋 {remaining} کانفیگ در صف مانده.",
            reply_markup=self.keyboard.back_button()
        )
    
    async def send_configs_batch(self, context: ContextTypes.DEFAULT_TYPE, configs: List[Dict]):
        db = context.bot_data['db']
        config = context.bot_data['config']
        
        batch_size = int(await db.get_setting('batch_size', config.BATCH_SIZE))
        interval = int(await db.get_setting('interval', config.BATCH_INTERVAL))
        delay = int(await db.get_setting('delay', config.DELAY))
        
        random.shuffle(configs)
        
        batches = [configs[i:i + batch_size] for i in range(0, len(configs), batch_size)]
        
        for i, batch in enumerate(batches):
            for cfg in batch:
                stop_sending = await db.get_setting('stop_sending', 'false')
                if stop_sending == 'true':
                    logger.info("Sending stopped by admin")
                    return
                
                try:
                    daily_limit = int(await db.get_setting('daily_limit', config.DAILY_LIMIT))
                    daily_sent = await db.get_daily_sent_count()
                    
                    if daily_sent >= daily_limit:
                        logger.info(f"Daily limit reached: {daily_sent}/{daily_limit}")
                        return
                    
                    message = await self.send_single_config(context, cfg)
                    if message:
                        cfg['message_id'] = message.message_id
                        cfg['channel_id'] = str(message.chat.id)
                        cfg['sent_at'] = datetime.now().isoformat()
                        
                        config_id = await db.add_config(cfg)
                        cfg['id'] = config_id
                        
                        await db.increment_daily_count(cfg.get('location'))
                        
                        if delay > 0:
                            await asyncio.sleep(delay)
                            
                except Exception as e:
                    logger.error(f"Error sending config {cfg.get('uuid')}: {e}")
                    continue
            
            if i < len(batches) - 1:
                await asyncio.sleep(interval)
    
    async def send_single_config(self, context: ContextTypes.DEFAULT_TYPE, cfg: Dict) -> Any:
        sender = context.bot_data['sender']
        keyboard = context.bot_data['keyboard']
        config = context.bot_data['config']
        
        text = sender.format_config_text(cfg)
        channel_id = config.CHANNELS[0] if config.CHANNELS else None
        
        if not channel_id:
            logger.error("No channel configured")
            return None
        
        try:
            return await context.bot.send_message(
                chat_id=channel_id,
                text=text,
                parse_mode='HTML',
                reply_markup=keyboard.config_buttons(cfg['uuid'])
            )
        except Exception as e:
            logger.error(f"Failed to send to channel {channel_id}: {e}")
            return None
    
    async def delete_config(self, context: ContextTypes.DEFAULT_TYPE, uuid: str):
        db = context.bot_data['db']
        config = await db.get_config_by_uuid(uuid)
        
        if config and config.get('message_id') and config.get('channel_id'):
            try:
                await context.bot.delete_message(
                    chat_id=config['channel_id'],
                    message_id=config['message_id']
                )
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")
        
        await db.delete_config(uuid)
    
    async def notify_admin(self, context: ContextTypes.DEFAULT_TYPE, text: str):
        try:
            await context.bot.send_message(chat_id=self.config.ADMIN_ID, text=text)
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
    
    async def set_interval_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.callback_query.edit_message_text(
            "⏱️ فاصله ارسال را به ثانیه وارد کنید:",
            reply_markup=self.keyboard.back_button()
        )
        return SET_INTERVAL
    
    async def save_interval(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            value = int(update.message.text)
            await self.db.set_setting('interval', str(value))
            settings = {
                'interval': str(value),
                'batch_size': await self.db.get_setting('batch_size', '5'),
                'delay': await self.db.get_setting('delay', '0'),
                'daily_limit': await self.db.get_setting('daily_limit', '200')
            }
            await update.message.reply_text(
                self.sender.format_setting_changed('فاصله ارسال', f"{value} ثانیه", settings),
                reply_markup=self.keyboard.back_button()
            )
        except ValueError:
            await update.message.reply_text("❌ عدد وارد کنید.")
            return SET_INTERVAL
        return ConversationHandler.END
    
    async def set_batch_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.callback_query.edit_message_text(
            "🔢 تعداد هر batch را وارد کنید:",
            reply_markup=self.keyboard.back_button()
        )
        return SET_BATCH
    
    async def save_batch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            value = int(update.message.text)
            await self.db.set_setting('batch_size', str(value))
            settings = {
                'interval': await self.db.get_setting('interval', '120'),
                'batch_size': str(value),
                'delay': await self.db.get_setting('delay', '0'),
                'daily_limit': await self.db.get_setting('daily_limit', '200')
            }
            await update.message.reply_text(
                self.sender.format_setting_changed('تعداد batch', f"{value} عدد", settings),
                reply_markup=self.keyboard.back_button()
            )
        except ValueError:
            await update.message.reply_text("❌ عدد وارد کنید.")
            return SET_BATCH
        return ConversationHandler.END
    
    async def set_delay_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.callback_query.edit_message_text(
            "⏳ تأخیر بین هر کانفیگ را به ثانیه وارد کنید:",
            reply_markup=self.keyboard.back_button()
        )
        return SET_DELAY
    
    async def save_delay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            value = int(update.message.text)
            await self.db.set_setting('delay', str(value))
            settings = {
                'interval': await self.db.get_setting('interval', '120'),
                'batch_size': await self.db.get_setting('batch_size', '5'),
                'delay': str(value),
                'daily_limit': await self.db.get_setting('daily_limit', '200')
            }
            await update.message.reply_text(
                self.sender.format_setting_changed('تأخیر', f"{value} ثانیه", settings),
                reply_markup=self.keyboard.back_button()
            )
        except ValueError:
            await update.message.reply_text("❌ عدد وارد کنید.")
            return SET_DELAY
        return ConversationHandler.END
    
    async def set_daily_limit_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.callback_query.edit_message_text(
            "📊 محدودیت روزانه را وارد کنید:",
            reply_markup=self.keyboard.back_button()
        )
        return SET_DAILY_LIMIT
    
    async def save_daily_limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            value = int(update.message.text)
            await self.db.set_setting('daily_limit', str(value))
            settings = {
                'interval': await self.db.get_setting('interval', '120'),
                'batch_size': await self.db.get_setting('batch_size', '5'),
                'delay': await self.db.get_setting('delay', '0'),
                'daily_limit': str(value)
            }
            await update.message.reply_text(
                self.sender.format_setting_changed('محدودیت روزانه', f"{value} کانفیگ", settings),
                reply_markup=self.keyboard.back_button()
            )
        except ValueError:
            await update.message.reply_text("❌ عدد وارد کنید.")
            return SET_DAILY_LIMIT
        return ConversationHandler.END
    
    async def custom_send_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        queue = await self.db.get_queue_count()
        await update.callback_query.edit_message_text(
            f"📋 {queue} کانفیگ در صف است.\n\nتعداد مورد نظر برای ارسال را وارد کنید:",
            reply_markup=self.keyboard.back_button()
        )
        return CUSTOM_SEND
    
    async def do_custom_send(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            count = int(update.message.text)
            queue = await self.db.get_queue_count()
            
            if count > queue:
                await update.message.reply_text(f"❌ فقط {queue} کانفیگ در صف است.")
                return CUSTOM_SEND
            
            configs = await self.db.get_pending_configs(limit=count)
            
            processing_msg = await update.message.reply_text(f"⏳ در حال ارسال {len(configs)} کانفیگ...")
            
            await self.send_configs_batch(context, configs)
            
            remaining = await self.db.get_queue_count()
            await processing_msg.edit_text(
                f"✅ {len(configs)} کانفیگ ارسال شد.\n"
                f"📋 {remaining} کانفیگ در صف مانده.",
                reply_markup=self.keyboard.back_button()
            )
            
        except ValueError:
            await update.message.reply_text("❌ عدد وارد کنید.")
            return CUSTOM_SEND
        
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("❌ عملیات لغو شد.", reply_markup=self.keyboard.main_menu())
        return ConversationHandler.END
    
    async def show_help(self, query):
        help_text = """
📖 راهنمای ربات:

📤 آپلود HTML - آپلود فایل HTML اکسپورت شده از کانال
📊 آمار - مشاهده آمار کامل کانال و کانفیگ‌ها
📤 ارسال دستی - ارسال سریع یا دستی کانفیگ‌های در صف
📱 کلاینت‌ها - دریافت لینک کلاینت‌های پیشنهادی
⚙️ تنظیمات - تغییر تنظیمات ربات
🔔 یادآوری - تنظیم یادآوری تمدید سرور
🔄 استارت مجدد - راه‌اندازی مجدد ربات
⛔ توقف ارسال - توقف فوری ارسال کانفیگ‌ها

⚠️ نکات مهم:
• فایل HTML باید از کانال تلگرام اکسپورت شده باشد
• حداکثر حجم فایل: 10 مگابایت
• کانفیگ‌ها به صورت رندوم ارسال می‌شوند
• محدودیت روزانه: 200 کانفیگ
        """
        await query.edit_message_text(help_text, reply_markup=self.keyboard.back_button())

async def main():
    bot = NonecoreBot()
    await bot.init()
    bot.run()

if __name__ == '__main__':
    asyncio.run(main())
