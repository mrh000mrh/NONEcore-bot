"""
فرمت‌بندی خروجی کانفیگ‌ها
"""

import qrcode
import io
import base64
from datetime import datetime
from config import Config

class ConfigFormatter:
    """فرمت‌بندی کانفیگ برای ارسال"""
    
    @staticmethod
    def format_config(config_data: dict, source: str = "") -> dict:
        """فرمت‌بندی یک کانفیگ"""
        configs = config_data.get('configs', [])
        if not configs:
            return None
        
        # اولین کانفیگ (اگر چندتا باشد)
        main_config = configs[0]
        
        # تعیین کیفیت
        ping = config_data.get('ping', '---')
        quality = ConfigFormatter.get_quality(ping)
        
        # لوکیشن
        location = config_data.get('location', 'Unknown')
        flag = ConfigFormatter.get_flag(location)
        
        # ساخت QR
        qr_image = ConfigFormatter.create_qr(main_config['link'])
        
        # متن اصلی
        text = f"""┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🔷 {Config.BRAND_NAME} Config Bot      ┃
┃  ⚡️ کانال: {Config.BRAND_CHANNEL}      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

📂 کانفیگ {main_config['type']}
📍 لوکیشن: {flag} {location}  
📶 پینگ: {ping} {quality}
#{main_config['type']} #VPN #{Config.BRAND_NAME} #{ConfigFormatter.clean_hashtag(location)}
🕒 {ConfigFormatter.get_time()}

`{main_config['link']}`

⚡️ بررسی: ✅ تا این لحظه فعال
🔗 بفرست برای بقیه که اونا هم وصل باشن: {Config.BRAND_CHANNEL}"""
        
        return {
            'text': text,
            'qr': qr_image,
            'config': main_config
        }
    
    @staticmethod
    def get_quality(ping: str) -> str:
        """تعیین کیفیت بر اساس پینگ"""
        try:
            ping_num = int(ping.replace('ms', '').strip())
            if ping_num <= 50:
                return "🟢"
            elif ping_num <= 150:
                return "🟡"
            else:
                return "🔴"
        except:
            return "⚪️"
    
    @staticmethod
    def get_flag(location: str) -> str:
        """تبدیل نام کشور به پرچم"""
        flags = {
            'آلمان': '🇩🇪', 'Germany': '🇩🇪',
            'هلند': '🇳🇱', 'Netherlands': '🇳🇱',
            'انگلیس': '🇬🇧', 'UK': '🇬🇧', 'Britain': '🇬🇧',
            'فرانسه': '🇫🇷', 'France': '🇫🇷',
            'آمریکا': '🇺🇸', 'USA': '🇺🇸', 'America': '🇺🇸',
            'کانادا': '🇨🇦', 'Canada': '🇨🇦',
            'سنگاپور': '🇸🇬', 'Singapore': '🇸🇬',
            'ژاپن': '🇯🇵', 'Japan': '🇯🇵',
            'کلودفلر': '☁️', 'Cloudflare': '☁️'
        }
        
        for key, flag in flags.items():
            if key in location:
                return flag
        return '🏳️'
    
    @staticmethod
    def clean_hashtag(text: str) -> str:
        """تمیز کردن برای هشتگ"""
        return text.replace(' ', '_').replace('-', '_')[:20]
    
    @staticmethod
    def get_time() -> str:
        """زمان فعلی به فارسی"""
        now = datetime.now()
        # تبدیل ساده (می‌تواند با کتابخانه jdatetime بهتر شود)
        return now.strftime("%H:%M - %Y/%m/%d")
    
    @staticmethod
    def create_qr(link: str) -> bytes:
        """ساخت QR Code"""
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(link)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
        except:
            return None
    
    @staticmethod
    def format_daily_stats(today_count: int, total_count: int, locations: dict) -> str:
        """فرمت آمار روزانه"""
        loc_text = ""
        for loc, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5]:
            flag = ConfigFormatter.get_flag(loc)
            loc_text += f"{flag}{loc}({count}) "
        
        hashtags = " ".join([f"#{ConfigFormatter.clean_hashtag(loc)}" for loc in locations.keys()][:6])
        
        return f"""📊 آمار {Config.BRAND_NAME} - {ConfigFormatter.get_time()}

📤 امروز: {today_count} کانفیگ
📈 کل: {total_count} کانفیگ
🌍 لوکیشن‌ها: {loc_text}

🔍 جستجو بر اساس لوکیشن:
{hashtags}

⚡️ کانال: {Config.BRAND_CHANNEL}"""
