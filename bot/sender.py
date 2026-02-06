"""
ارسال کانفیگ به کانال
"""

import io
import qrcode
from telegram import Bot, InputFile
from config import Config

class ConfigSender:
    """ارسال‌کننده کانفیگ"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def send_config(self, chat_id: str, config: dict, stats: dict = None):
        """ارسال یک کانفیگ"""
        
        # ساخت QR
        qr_buffer = self._create_qr(config['link'])
        
        # ساخت متن
        text = self._format_message(config, stats)
        
        # ارسال
        if qr_buffer:
            await self.bot.send_photo(
                chat_id=chat_id,
                photo=InputFile(qr_buffer, filename='qr.png'),
                caption=text,
                parse_mode='HTML'
            )
        else:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode='HTML'
            )
    
    def _create_qr(self, link: str) -> io.BytesIO:
        """ساخت QR Code"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(link)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            return buffer
        except Exception as e:
            print(f"QR Error: {e}")
            return None
    
    def _format_message(self, config: dict, stats: dict = None) -> str:
        """فرمت پیام"""
        flag = self._get_flag(config['location'])
        
        text = f"""┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🔷 {Config.BRAND_NAME} Config Bot      ┃
┃  ⚡️ کانال: {Config.BRAND_CHANNEL}      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

📂 کانفیگ {config['type']}
📍 لوکیشن: {flag} {config['location']}  
📶 پینگ: {config['ping']} {config['quality']}
#{config['type']} #VPN #{Config.BRAND_NAME} #{self._clean_hashtag(config['location'])}
🕒 {self._get_time()}

<code>{config['link']}</code>

⚡️ بررسی: ✅ تا این لحظه فعال
🔗 بفرست برای بقیه که اونا هم وصل باشن: {Config.BRAND_CHANNEL}

🔒 سطح امنیتی: عمومی
✅ مناسب: وبگردی، شبکه‌های اجتماعی، دسترسی به محتوای مسدود
❌ نامناسب: تراکنش‌های مالی، اطلاعات محرمانه، ترید"""
        
        return text
    
    def _get_flag(self, location: str) -> str:
        """پرچم کشور"""
        flags = {
            'آلمان': '🇩🇪', 'Germany': '🇩🇪', 'DE': '🇩🇪',
            'هلند': '🇳🇱', 'Netherlands': '🇳🇱', 'NL': '🇳🇱',
            'انگلیس': '🇬🇧', 'UK': '🇬🇧', 'Britain': '🇬🇧', 'GB': '🇬🇧',
            'فرانسه': '🇫🇷', 'France': '🇫🇷', 'FR': '🇫🇷',
            'آمریکا': '🇺🇸', 'USA': '🇺🇸', 'America': '🇺🇸', 'US': '🇺🇸',
            'کانادا': '🇨🇦', 'Canada': '🇨🇦', 'CA': '🇨🇦',
            'سنگاپور': '🇸🇬', 'Singapore': '🇸🇬', 'SG': '🇸🇬',
            'ژاپن': '🇯🇵', 'Japan': '🇯🇵', 'JP': '🇯🇵',
            'کلودفلر': '☁️', 'Cloudflare': '☁️'
        }
        for key, flag in flags.items():
            if key.lower() in location.lower():
                return flag
        return '🏳️'
    
    def _clean_hashtag(self, text: str) -> str:
        """تمیز کردن برای هشتگ"""
        return text.replace(' ', '_').replace('-', '_')[:20]
    
    def _get_time(self) -> str:
        """زمان فعلی"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M - %Y/%m/%d")
    
    async def send_daily_stats(self, chat_id: str, stats: dict, locations: dict):
        """ارسال آمار روزانه"""
        loc_text = ""
        for loc, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5]:
            flag = self._get_flag(loc)
            loc_text += f"{flag}{loc}({count}) "
        
        hashtags = " ".join([f"#{self._clean_hashtag(loc)}" for loc in list(locations.keys())[:6]])
        
        text = f"""📊 آمار {Config.BRAND_NAME} - {self._get_time()}

📤 امروز: {stats['today']} کانفیگ
📈 کل: {stats['total']} کانفیگ
🌍 لوکیشن‌ها: {loc_text}

🔍 جستجو بر اساس لوکیشن:
{hashtags}

⚡️ کانال: {Config.BRAND_CHANNEL}

🔒 سطح امنیتی: عمومی
✅ مناسب: وبگردی، شبکه‌های اجتماعی، دسترسی به محتوای مسدود
❌ نامناسب: تراکنش‌های مالی، اطلاعات محرمانه، ترید"""
        
        await self.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
    
    async def send_clients(self, chat_id: str):
        """ارسال لیست کلاینت‌ها"""
        text = f"""📱 کلاینت‌های پیشنهادی:

🤖 اندروید:
• V2RayNG - github.com/2dust/v2rayNG
• SagerNet - github.com/SagerNet/SagerNet

🍎 iOS:
• Streisand - App Store
• Shadowrocket - App Store

💻 ویندوز:
• v2rayN - github.com/2dust/v2rayN
• Nekoray - github.com/MatsuriDayo/nekoray

🐧 لینوکس/macOS:
• Nekoray - github.com/MatsuriDayo/nekoray

🔒 فیلترشکن‌های ضدسانسور:
• Psiphon - psiphon.ca
• Tor Browser - torproject.org
• Tails - tails.boum.org
• Lantern - getlantern.org
• Outline - getoutline.org

⚡️ کانال: {Config.BRAND_CHANNEL}"""
        
        await self.bot.send_message(chat_id=chat_id, text=text)
