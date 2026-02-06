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
            ['⚙️ تنظیمات', '📱 کلاینت‌ها'],
            ['🔔 یادآوری', '❓ راهنما']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def settings_menu():
        """کیبورد تنظیمات"""
        keyboard = [
            ['✅/❌ ارسال کلاینت‌ها', '✅/❌ حالت تأییدیه'],
            ['✅/❌ یادآوری renewal', '🔢 تغییر batch size'],
            ['⏱️ تغییر فاصله', '📢 مدیریت کانال‌ها'],
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
    def inline_channels(channels):
        """دکمه‌های شیشه‌ای کانال‌ها"""
        keyboard = []
        for ch in channels:
            keyboard.append([InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.replace('@', '')}")])
        return InlineKeyboardMarkup(keyboard)
