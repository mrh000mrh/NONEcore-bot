"""
ارسال کانفیگ به کانال
"""

import io
import qrcode
from telegram import Bot, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from config import Config
from bot.keyboard import Keyboards

class ConfigSender:
    """ارسال‌کننده کانفیگ"""
    
    QR_SIZE = 5  # سایز کوچکتر QR
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def send_config(self, chat_id: str, config: dict):
        """ارسال یک کانفیگ"""
        
        qr_buffer = self._create_qr(config['link'])
        text = self._format_message(config)
        
        # دکمه‌ها
        reply_markup = Keyboards.config_buttons(config.get('id', 0))
        
        if qr_buffer:
            msg = await self.bot.send_photo(
                chat_id=chat_id,
                photo=InputFile(qr_buffer, filename='qr.png'),
                caption=text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return msg.message_id
        else:
            msg = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return msg.message_id
    
    def _create_qr(self, link: str) -> io.BytesIO:
        """ساخت QR Code کوچک"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=self.QR_SIZE,  # سایز کوچک
                border=2,
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
    
    def _format_message(self, config: dict) -> str:
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
            'انگلیس': '🇬🇧', 'UK': '🇬🇧', 'Britain': '🇬🇧',
            'فرانسه': '🇫🇷', 'France': '🇫🇷', 'FR': '🇫🇷',
            'آمریکا': '🇺🇸', 'USA': '🇺🇸', 'US': '🇺🇸',
            'کانادا': '🇨🇦', 'Canada': '🇨🇦', 'CA': '🇨🇦',
            'سنگاپور': '🇸🇬', 'Singapore': '🇸🇬',
            'ژاپن': '🇯🇵', 'Japan': '🇯🇵',
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
    
    async def send_clients(self, chat_id: str):
        """ارسال لیست کلاینت‌ها"""
        text = """📱 <b>کلاینت‌های پیشنهادی:</b>

🤖 <b>اندروید:</b>
• V2RayNG - github.com/2dust/v2rayNG
• SagerNet - github.com/SagerNet/SagerNet

🍎 <b>iOS:</b>
• Streisand - App Store
• Shadowrocket - App Store

💻 <b>ویندوز:</b>
• v2rayN - github.com/2dust/v2rayN
• Nekoray - github.com/MatsuriDayo/nekoray

🐧 <b>لینوکس/macOS:</b>
• Nekoray - github.com/MatsuriDayo/nekoray

🔒 <b>فیلترشکن‌های ضدسانسور:</b>
• Psiphon - psiphon.ca
• Tor Browser - torproject.org
• Tails - tails.boum.org
• Lantern - getlantern.org
• Outline - getoutline.org

⚡️ @nonecorebot"""
        
        # دکمه کپی گروهی
        reply_markup = Keyboards.copy_group_button()
        
        await self.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML', reply_markup=reply_markup)