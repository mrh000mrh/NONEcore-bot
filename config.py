"""
تنظیمات NONEcore Bot
"""

from dotenv import load_dotenv
load_dotenv()  # خواندن .env

import os

class Config:
    """کلاس تنظیمات"""
    
    # توکن ربات تلگرام
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    
    # آیدی عددی ادمین
    ADMIN_ID = os.environ.get("ADMIN_ID", "")
    
    # کانال‌های مقصد
    CHANNELS = os.environ.get("CHANNELS", "@nonecorebot")
    
    # ارسال کلاینت‌ها
    SEND_CLIENTS = os.environ.get("SEND_CLIENTS", "true").lower() == "true"
    
    # حالت تأییدیه
    APPROVAL_MODE = os.environ.get("APPROVAL_MODE", "false").lower() == "true"
    
    # تعداد هر batch
    BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "10"))
    
    # فاصله بین batchها
    BATCH_INTERVAL = int(os.environ.get("BATCH_INTERVAL", "120"))
    
    # MongoDB (اختیاری)
    MONGODB_URI = os.environ.get("MONGODB_URI", "")
    
    # ipinfo (اختیاری)
    IPINFO_TOKEN = os.environ.get("IPINFO_TOKEN", "")
    
    # FPS.ms renewal
    FPS_RENEWAL_URL = os.environ.get("FPS_RENEWAL_URL", "https://fps.ms/dashboard")
    RENEWAL_HOUR = int(os.environ.get("RENEWAL_HOUR", "21"))
    
    # نام برند
    BRAND_NAME = os.environ.get("BRAND_NAME", "NONEcore")
    BRAND_CHANNEL = os.environ.get("BRAND_CHANNEL", "@nonecorebot")
    BRAND_BOT = os.environ.get("BRAND_BOT", "@nonecore_bot")
    
    @classmethod
    def validate(cls):
        """بررسی تنظیمات ضروری"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required!")
        if not cls.ADMIN_ID:
            raise ValueError("ADMIN_ID is required!")
