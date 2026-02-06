"""
تنظیمات NONEcore Bot
"""

import os

class Config:
    """کلاس تنظیمات"""
    
    # توکن ربات تلگرام (از @BotFather)
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    
    # آیدی عددی ادمین (از @userinfobot)
    ADMIN_ID = os.environ.get("ADMIN_ID", "")
    
    # کانال‌های مقصد (با کاما جدا شوند)
    # مثال: @nonecorebot,@channel2,@channel3
    CHANNELS = os.environ.get("CHANNELS", "@nonecorebot")
    
    # ارسال کلاینت‌ها (true/false)
    SEND_CLIENTS = os.environ.get("SEND_CLIENTS", "true").lower() == "true"
    
    # حالت تأییدیه (true/false)
    APPROVAL_MODE = os.environ.get("APPROVAL_MODE", "false").lower() == "true"
    
    # تعداد هر batch
    BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "10"))
    
    # فاصله بین batchها (ثانیه)
    BATCH_INTERVAL = int(os.environ.get("BATCH_INTERVAL", "120"))
    
    # MongoDB (اختیاری - برای Northflank addon)
    MONGODB_URI = os.environ.get("MONGODB_URI", "")
    
    # ipinfo (اختیاری - برای تست لوکیشن واقعی)
    IPINFO_TOKEN = os.environ.get("IPINFO_TOKEN", "")
    
    # نام برند
    BRAND_NAME = "NONEcore"
    BRAND_CHANNEL = "@nonecorebot"
    BRAND_BOT = "@nonecore_bot"
    
    @classmethod
    def validate(cls):
        """بررسی تنظیمات ضروری"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required!")
        if not cls.ADMIN_ID:
            raise ValueError("ADMIN_ID is required!")
