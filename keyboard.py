from telegram import InlineKeyboardMarkup, InlineKeyboardButton

class Keyboard:
    @staticmethod
    def main_menu():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 آپلود HTML", callback_data='upload_html')],
            [InlineKeyboardButton("📊 آمار", callback_data='stats'), InlineKeyboardButton("📤 ارسال دستی", callback_data='manual_send')],
            [InlineKeyboardButton("📱 کلاینت‌ها", callback_data='clients'), InlineKeyboardButton("⚙️ تنظیمات", callback_data='settings')],
            [InlineKeyboardButton("🔔 یادآوری", callback_data='reminder'), InlineKeyboardButton("🔄 استارت مجدد", callback_data='restart')],
            [InlineKeyboardButton("⛔ توقف ارسال", callback_data='stop_sending'), InlineKeyboardButton("❓ راهنما", callback_data='help')]
        ])
    
    @staticmethod
    def settings_menu():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⏱️ فاصله ارسال", callback_data='set_interval'), InlineKeyboardButton("🔢 تعداد batch", callback_data='set_batch')],
            [InlineKeyboardButton("⏳ تأخیر", callback_data='set_delay'), InlineKeyboardButton("📊 محدودیت روزانه", callback_data='set_daily_limit')],
            [InlineKeyboardButton("✅/❌ ارسال کلاینت‌ها", callback_data='toggle_clients'), InlineKeyboardButton("✅/❌ یادآوری", callback_data='toggle_reminder')],
            [InlineKeyboardButton("📢 مدیریت کانال‌ها", callback_data='manage_channels')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='main_menu')]
        ])
    
    @staticmethod
    def manual_send_menu():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ ارسال سریع ۱۰ تایی", callback_data='quick_send_10')],
            [InlineKeyboardButton("📝 ارسال دستی (تعداد دلخواه)", callback_data='custom_send')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='main_menu')]
        ])
    
    @staticmethod
    def config_buttons(uuid: str):
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📋 کپی", callback_data=f'copy_{uuid}'),
                InlineKeyboardButton("🔴 گزارش خرابی", callback_data=f'report_{uuid}')
            ]
        ])
    
    @staticmethod
    def confirm_report(uuid: str):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ بله، کار نمی‌کند", callback_data=f'confirm_report_{uuid}')],
            [InlineKeyboardButton("❌ خیر، اشتباه کردم", callback_data=f'cancel_report_{uuid}')]
        ])
    
    @staticmethod
    def back_button():
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='main_menu')]])
    
    @staticmethod
    def clients_menu():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 v2rayNG", url='https://play.google.com/store/apps/details?id=com.v2ray.ang')],
            [InlineKeyboardButton("📱 Streisand", url='https://apps.apple.com/app/streisand/id6450534064')],
            [InlineKeyboardButton("📱 V2RayN", url='https://github.com/2dust/v2rayN/releases')],
            [InlineKeyboardButton("📱 Nekoray", url='https://github.com/MatsuriDayo/nekoray/releases')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='main_menu')]
        ])
