import logging
from datetime import datetime
from typing import Dict, Any, Optional
from io import BytesIO

logger = logging.getLogger(__name__)

class Sender:
    def __init__(self, config):
        self.config = config
    
    def format_config_text(self, cfg: Dict[str, Any]) -> str:
        if self.config.CONFIG_TEXT_TEMPLATE:
            try:
                return self.config.CONFIG_TEXT_TEMPLATE.format(
                    type=cfg['type'],
                    location=cfg['location'],
                    ping=cfg['ping'],
                    quality=cfg['quality'],
                    link=cfg['link'],
                    time=datetime.now().strftime('%Y-%m-%d %H:%M'),
                    brand=self.config.BRAND_NAME,
                    channel=self.config.BRAND_CHANNEL,
                    server=cfg['server'],
                    port=cfg['port']
                )
            except Exception as e:
                logger.error(f"Template error: {e}")
        
        location_clean = cfg['location'].replace(' ', '').replace('🇩🇪', 'Germany').replace('🇳🇱', 'Netherlands').replace('🇺🇸', 'USA')
        loc_for_hashtag = location_clean.replace('🇩🇪', '').replace('🇳🇱', '').replace('🇺🇸', '').replace('🇬🇧', '').replace('🇫🇷', '').strip()
        
        return f"""┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🔷 {self.config.BRAND_NAME} Config Bot      ┃
┃  ⚡️ کانال: {self.config.BRAND_CHANNEL}      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

📂 کانفیگ {cfg['type']}
📍 لوکیشن: {cfg['location']}  
📶 پینگ: {cfg['ping']} {cfg['quality']}

#{cfg['type']} #VPN #{self.config.BRAND_NAME} #{loc_for_hashtag}

🕒 {datetime.now().strftime('%Y-%m-%d %H:%M')}

<code>{cfg['link']}</code>

⚡️ بررسی: ✅ تا این لحظه فعال
🔗 بفرست برای بقیه: {self.config.BRAND_CHANNEL}"""
    
    def get_remark(self) -> str:
        return self.config.CONFIG_REMARK or f"{self.config.BRAND_NAME} | تلگرام: {self.config.BRAND_CHANNEL}"
    
    def format_admin_stats(self, stats: Dict[str, Any]) -> str:
        locations_text = '\n'.join([f"• {loc}: {count}" for loc, count in stats['locations'].items()]) if stats['locations'] else "• هیچ"
        
        return f"""📊 آمار {self.config.BRAND_NAME}

📤 امروز: {stats['today_configs']} کانفیگ
📈 کل: {stats['total_configs']} کانفیگ  
📋 در صف: {stats['queue']} کانفیگ

👥 کاربران جدید امروز: {stats.get('new_members', 0)} نفر
👤 کل اعضا: {stats.get('total_members', 0)} نفر

📊 آمار کانفیگ‌ها:
• کپی شده: {stats['today_copies']} بار (امروز) / {stats['total_copies']} بار (کل)
• گزارش خرابی: {stats['today_reports']} بار (امروز) / {stats['total_reports']} بار (کل)

🌍 لوکیشن‌های امروز:
{locations_text}"""
    
    def format_queue_status(self, queue_count: int, batch_size: int, interval: int, delay: int) -> str:
        if queue_count == 0:
            return "✅ هیچ کانفیگی در صف نیست."
        
        batches = (queue_count + batch_size - 1) // batch_size
        total_seconds = batches * (interval + delay)
        minutes = total_seconds // 60
        
        return f"📋 {queue_count} در صف | ⏱️ ~{minutes} دقیقه تا اتمام"
    
    def format_settings(self, settings: Dict[str, str]) -> str:
        return f"""⚙️ تنظیمات فعلی:

• فاصله ارسال: {settings.get('interval', '120')} ثانیه
• تعداد هر batch: {settings.get('batch_size', '5')} عدد
• تأخیر باقیمانده: {settings.get('delay', '0')} ثانیه
• ارسال کلاینت‌ها: {'✅' if settings.get('send_clients') == 'true' else '❌'}
• یادآوری renewal: {'✅' if settings.get('reminder_enabled') == 'true' else '❌'}
• محدودیت روزانه: {settings.get('daily_limit', '200')}"""
    
    def format_setting_changed(self, name: str, value: str, all_settings: Dict[str, str]) -> str:
        return f"""✅ {name} به {value} تغییر یافت.

⚙️ تنظیمات فعلی:
• فاصله: {all_settings.get('interval', '120')} ثانیه
• batch: {all_settings.get('batch_size', '5')} عدد
• تأخیر: {all_settings.get('delay', '0')} ثانیه
• محدودیت روزانه: {all_settings.get('daily_limit', '200')}"""
