"""
کیبوردهای ربات
"""

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

class Keyboards:
    """کیبوردهای ربات"""
    
    @staticmethod
    def main_menu():
        """کیبورد اصلی ادمین"""
        keyboard = [
            ['📤 آپلود HTML', '📊 آمار'],
            ['📤 ارسال دستی باقیمانده', '📱 کلاینت‌ها'],
            ['⚙️ تنظیمات', '🔔 یادآوری'],
            ['🔄 استارت مجدد', '❓ راهنما']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def settings_menu():
        """کیبورد تنظیمات"""
        keyboard = [
            ['⏱️ فاصله ارسال', '🔢 تعداد هر batch'],
            ['⏳ تأخیر باقیمانده', '✅/❌ ارسال کلاینت‌ها'],
            ['✅/❌ یادآوری renewal', '📢 مدیریت کانال‌ها'],
            ['🔙 بازگشت']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def upload_confirm():
        """تأیید آپلود"""
        keyboard = [
            ['✅ تأیید و ارسال', '❌ لغو'],
            ['🔙 بازگشت']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def remove_keyboard():
        """حذف کیبورد"""
        return ReplyKeyboardRemove()
    
    @staticmethod
    def config_buttons(config_id):
        """دکمه‌های زیر کانفیگ"""
        keyboard = [
            [
                InlineKeyboardButton("📋 کپی", callback_data=f'copy_{config_id}'),
                InlineKeyboardButton("🔴 گزارش خرابی", callback_data=f'bad_{config_id}')
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def copy_group_button():
        """دکمه کپی گروهی"""
        keyboard = [[InlineKeyboardButton("📋 کپی ۲۰ کانفیگ آخر", callback_data='copy_group')]]
        return InlineKeyboardMarkup(keyboard)