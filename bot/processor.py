"""
پردازش کانفیگ‌ها
"""

import re
import base64
import json
from typing import List, Dict

class ConfigProcessor:
    """پردازشگر کانفیگ"""
    
    PATTERNS = {
        'vless': r'vless://([a-zA-Z0-9\-]+)@([^:\s]+):(\d+)(?:\?([^#]*))?(?:#([^\s]*))?',
        'vmess': r'vmess://([A-Za-z0-9+/=]+)',
        'trojan': r'trojan://([a-zA-Z0-9\-]+)@([^:\s]+):(\d+)(?:\?([^#]*))?(?:#([^\s]*))?',
        'ss': r'ss://([A-Za-z0-9+/=]+)@([^:\s]+):(\d+)(?:#([^\s]*))?',
        'mtproto': r'mtproto://([A-Za-z0-9+/=]+)'
    }
    
    @staticmethod
    def extract_from_html(html_content: str) -> List[Dict]:
        """استخراج کانفیگ از HTML"""
        configs = []
        
        for proto, pattern in ConfigProcessor.PATTERNS.items():
            matches = re.finditer(pattern, html_content, re.IGNORECASE)
            for match in matches:
                config = ConfigProcessor._parse_config(match, proto, html_content)
                if config:
                    configs.append(config)
        
        return configs
    
    @staticmethod
    def _parse_config(match, proto: str, html_content: str) -> Dict:
        """پارس یک کانفیگ"""
        try:
            full_match = match.group(0)
            
            start_pos = max(0, match.start() - 500)
            end_pos = min(len(html_content), match.end() + 500)
            context = html_content[start_pos:end_pos]
            
            ping = ConfigProcessor._extract_ping(context)
            location = ConfigProcessor._extract_location(context)
            original_remark = ConfigProcessor._extract_original_remark(full_match, proto)
            
            new_link = ConfigProcessor._add_remark(full_match, proto, original_remark)
            
            server = ''
            port = 0
            if len(match.groups()) > 1:
                server = match.group(2) or ''
            if len(match.groups()) > 2:
                try:
                    port = int(match.group(3) or 0)
                except:
                    port = 0
            
            return {
                'type': proto.upper(),
                'link': new_link,
                'original_link': full_match,
                'server': server,
                'port': port,
                'ping': ping,
                'location': location,
                'original_remark': original_remark,
                'quality': ConfigProcessor._get_quality(ping),
                'source': original_remark
            }
            
        except Exception as e:
            print(f"Error parsing config: {e}")
            return None
    
    @staticmethod
    def _extract_ping(text: str) -> str:
        """استخراج پینگ"""
        patterns = [
            r'📶\s*پینگ[:\s]*(\d+)\s*ms',
            r'پینگ[:\s]*(\d+)\s*ms',
            r'ping[:\s]*(\d+)\s*ms',
            r'(\d+)\s*ms'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"{match.group(1)}ms"
        return "---"
    
    @staticmethod
    def _extract_location(text: str) -> str:
        """استخراج لوکیشن"""
        patterns = [
            r'📍\s*لوکیشن[:\s]*([^\n<]+)',
            r'لوکیشن[:\s]*([^\n<]+)',
            r'🌍\s*([^\n<]+)',
            r'Location[:\s]*([^\n<]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return "Unknown"
    
    @staticmethod
    def _extract_original_remark(link: str, proto: str) -> str:
        """استخراج ریماک اصلی"""
        if '#' in link:
            return link.split('#')[-1]
        
        if proto == 'vmess':
            try:
                b64 = link.replace('vmess://', '')
                padding = 4 - len(b64) % 4
                if padding != 4:
                    b64 += '=' * padding
                data = json.loads(base64.b64decode(b64).decode('utf-8'))
                return data.get('ps', 'Unknown')
            except:
                pass
        
        return "Unknown"
    
    @staticmethod
    def _add_remark(link: str, proto: str, original: str) -> str:
        """اضافه کردن ریماک NONEcore"""
        new_remark = f"NONEcore | تلگرام: @nonecorebot"
        
        if '#' in link:
            base = link.split('#')[0]
            return f"{base}#{new_remark}"
        else:
            return f"{link}#{new_remark}"
    
    @staticmethod
    def _get_quality(ping: str) -> str:
        """تعیین کیفیت"""
        try:
            num = int(ping.replace('ms', '').strip())
            if num <= 50:
                return "🟢"
            elif num <= 150:
                return "🟡"
            else:
                return "🔴"
        except:
            return "⚪️"