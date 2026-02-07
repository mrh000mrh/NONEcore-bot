import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
    CHANNELS = [c.strip() for c in os.getenv('CHANNELS', '@nonecorebot').split(',') if c.strip()]
    
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', 5))
    BATCH_INTERVAL = int(os.getenv('BATCH_INTERVAL', 120))
    DELAY = int(os.getenv('DELAY', 0))
    DAILY_LIMIT = int(os.getenv('DAILY_LIMIT', 200))
    
    SEND_CLIENTS = os.getenv('SEND_CLIENTS', 'true').lower() == 'true'
    APPROVAL_MODE = os.getenv('APPROVAL_MODE', 'false').lower() == 'true'
    REMINDER_ENABLED = os.getenv('REMINDER_ENABLED', 'true').lower() == 'true'
    
    BRAND_NAME = os.getenv('BRAND_NAME', 'NONEcore')
    BRAND_CHANNEL = os.getenv('BRAND_CHANNEL', '@nonecorebot')
    BRAND_BOT = os.getenv('BRAND_BOT', '@nonecore_bot')
    FPS_RENEWAL_URL = os.getenv('FPS_RENEWAL_URL', 'https://fps.ms/dashboard')
    
    CONFIG_TEXT_TEMPLATE = os.getenv('CONFIG_TEXT_TEMPLATE', '')
    CONFIG_REMARK = os.getenv('CONFIG_REMARK', 'NONEcore | تلگرام: @nonecorebot')
    
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'nonecore.db')
    MAX_HTML_SIZE = 10 * 1024 * 1024
    
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    TIMEZONE = os.getenv('TIMEZONE', 'Asia/Tehran')
