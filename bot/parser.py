"""
پارس HTML و استخراج کانفیگ‌ها
"""

import re
import base64
import json
from bs4 import BeautifulSoup
from typing import List, Dict

class ConfigParser:
    """پارس کانفیگ از HTML"""
    
    # پترن‌های کانفیگ
    PATTERNS = {
        'vless': r'vless://[a-zA-Z0-9\-]+@[^:\s]+:\d+[^#\s]*(?:#[^\s]*)?',
        'vmess': r'vmess://[A-Za-z0-9+/=]+',
        'trojan': r'trojan://[a-zA-Z0-9\-]+@[^:\s]+:\d+[^#\s]*(?:#[^\s]*)?',
        'ss': r'ss://[A-Za-z0-9+/=]+@[^:\s]+:\d+(?:#[^\s]*)?',
        'mtproto': r'mtproto://[A-Za-z0-9+/=]+'
    }
    
    @staticmethod
    def parse_html(html_content: str) -> List[Dict]:
        """پارس HTML و استخراج کانفیگ‌ها"""
        soup = BeautifulSoup(html_content, 'html.parser')
        configs = []
        
        # پیدا کردن همه پیام‌ها
        messages = soup.find_all('div', class_='message')
        
        for msg in messages:
            text_div = msg.find('div', class_='text')
            if not text_div:
                continue
            
            text = text_div.get_text('\n', strip=True)
            
            # استخراج اطلاعات
            config_data = {
                'raw_text': text,
                'ping': ConfigParser.extract_ping(text),
                'location': ConfigParser.extract_location(text),
                'configs': []
            }
            
            # استخراج کانفیگ‌ها
            for proto, pattern in ConfigParser.PATTERNS.items():
                matches = re.findall(pattern, text)
                for match in matches:
                    config_info = {
                        'type': proto.upper(),
                        'link': match,
                        'remark': ConfigParser.extract_remark(match, proto)
                    }
                    config_data['configs'].append(config_info)
            
            if config_data['configs']:
                configs.append(config_data)
        
        return configs
    
    @staticmethod
    def extract_ping(text: str) -> str:
        """استخراج پینگ از متن"""
        patterns = [
            r'📶\s*پینگ[:\s]*(\d+)\s*ms',
            r'پینگ[:\s]*(\d+)\s*ms',
            r'ping[:\s]*(\d+)\s*ms'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"{match.group(1)}ms"
        return "---"
    
    @staticmethod
    def extract_location(text: str) -> str:
        """استخراج لوکیشن از متن"""
        patterns = [
            r'📍\s*لوکیشن[:\s]*([^\n]+)',
            r'لوکیشن[:\s]*([^\n]+)',
            r'🌍\s*([^\n]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return "Unknown"
    
    @staticmethod
    def extract_remark(link: str, proto: str) -> str:
        """استخراج نام کانفیگ"""
        if '#' in link:
            return link.split('#')[-1]
        
        # برای vmess
        if proto == 'vmess':
            try:
                b64 = link.replace('vmess://', '')
                # پدینگ
                padding = 4 - len(b64) % 4
                if padding != 4:
                    b64 += '=' * padding
                json_str = base64.b64decode(b64).decode('utf-8')
                data = json.loads(json_str)
                return data.get('ps', 'Unknown')
            except:
                pass
        
        return "Unknown"
