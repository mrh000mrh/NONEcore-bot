import re
import uuid
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ConfigProcessor:
    CONFIG_PATTERNS = {
        'VLESS': r'vless://([^@]+)@([^:]+):(\d+)[^#\s]*(?:#([^&\s]+))?',
        'VMess': r'vmess://([A-Za-z0-9+/=]+)',
        'Trojan': r'trojan://([^@]+)@([^:]+):(\d+)[^#\s]*(?:#([^&\s]+))?',
        'Shadowsocks': r'ss://([A-Za-z0-9+/=]+)@([^:]+):(\d+)'
    }
    
    LOCATION_FLAGS = {
        'Germany': '🇩🇪', 'Deutschland': '🇩🇪', 'DE': '🇩🇪',
        'Netherlands': '🇳🇱', 'Holland': '🇳🇱', 'NL': '🇳🇱',
        'USA': '🇺🇸', 'United States': '🇺🇸', 'US': '🇺🇸', 'America': '🇺🇸',
        'United Kingdom': '🇬🇧', 'UK': '🇬🇧', 'England': '🇬🇧', 'Britain': '🇬🇧',
        'France': '🇫🇷', 'FR': '🇫🇷',
        'Singapore': '🇸🇬', 'SG': '🇸🇬',
        'Japan': '🇯🇵', 'JP': '🇯🇵',
        'Iran': '🇮🇷', 'IR': '🇮🇷', 'Tehran': '🇮🇷',
        'Turkey': '🇹🇷', 'TR': '🇹🇷', 'Türkiye': '🇹🇷',
        'Russia': '🇷🇺', 'RU': '🇷🇺',
        'Canada': '🇨🇦', 'CA': '🇨🇦',
        'Australia': '🇦🇺', 'AU': '🇦🇺',
        'India': '🇮🇳', 'IN': '🇮🇳',
        'Brazil': '🇧🇷', 'BR': '🇧🇷',
        'Finland': '🇫🇮', 'FI': '🇫🇮',
        'Sweden': '🇸🇪', 'SE': '🇸🇪',
        'Switzerland': '🇨🇭', 'CH': '🇨🇭',
        'Poland': '🇵🇱', 'PL': '🇵🇱',
        'Spain': '🇪🇸', 'ES': '🇪🇸',
        'Italy': '🇮🇹', 'IT': '🇮🇹',
        'Austria': '🇦🇹', 'AT': '🇦🇹',
        'Hong Kong': '🇭🇰', 'HK': '🇭🇰',
        'South Korea': '🇰🇷', 'Korea': '🇰🇷', 'KR': '🇰🇷',
        'UAE': '🇦🇪', 'Dubai': '🇦🇪',
        'Israel': '🇮🇱', 'IL': '🇮🇱'
    }
    
    def extract_from_html(self, html_content: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html_content, 'lxml')
        text = soup.get_text()
        configs = []
        
        for config_type, pattern in self.CONFIG_PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    cfg = self._parse_match(match, config_type, soup, text)
                    if cfg:
                        configs.append(cfg)
                except Exception as e:
                    logger.error(f"Error parsing {config_type} config: {e}")
        
        unique_configs = self._remove_duplicates(configs)
        logger.info(f"Extracted {len(unique_configs)} unique configs from HTML")
        return unique_configs
    
    def _parse_match(self, match, config_type: str, soup, full_text: str) -> Dict[str, Any]:
        link = match.group(0)
        
        server = ''
        port = 443
        remark = ''
        
        if config_type in ['VLESS', 'Trojan']:
            server = match.group(2) if len(match.groups()) > 1 else ''
            port = int(match.group(3)) if len(match.groups()) > 2 and match.group(3) else 443
            remark = match.group(4) if len(match.groups()) > 3 and match.group(4) else ''
        elif config_type == 'Shadowsocks':
            server = match.group(2) if len(match.groups()) > 1 else ''
            port = int(match.group(3)) if len(match.groups()) > 2 and match.group(3) else 443
        
        context = self._extract_context(soup, link, full_text)
        
        return {
            'uuid': str(uuid.uuid4()),
            'type': config_type,
            'link': link,
            'server': server or context.get('server', 'unknown'),
            'port': port,
            'location': context.get('location', '🌍 Unknown'),
            'ping': context.get('ping', 'N/A'),
            'quality': self._calculate_quality(context.get('ping', '999')),
            'source': remark or context.get('remark', 'NONEcore'),
            'channel_id': None,
            'message_id': None,
            'bad_reports': 0,
            'copy_count': 0,
            'sent_at': None
        }
    
    def _extract_context(self, soup, link: str, full_text: str) -> Dict[str, str]:
        context = {}
        
        pos = full_text.find(link[:50])
        if pos != -1:
            surrounding = full_text[max(0, pos-200):min(len(full_text), pos+200)]
            
            ping_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:ms|ping|delay)', surrounding, re.IGNORECASE)
            if ping_match:
                context['ping'] = ping_match.group(1) + 'ms'
            
            for loc_name, flag in self.LOCATION_FLAGS.items():
                if loc_name in surrounding:
                    context['location'] = f"{flag} {loc_name}"
                    break
            
            server_match = re.search(r'(?:server|host|address)[:\s]+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', surrounding, re.IGNORECASE)
            if server_match:
                context['server'] = server_match.group(1)
        
        if 'location' not in context:
            for loc_name, flag in self.LOCATION_FLAGS.items():
                if loc_name in full_text[:1000]:
                    context['location'] = f"{flag} {loc_name}"
                    break
        
        return context
    
    def _calculate_quality(self, ping: str) -> str:
        try:
            ping_val = float(ping.replace('ms', '').strip())
            if ping_val < 100:
                return '🟢 Excellent'
            elif ping_val < 200:
                return '🟡 Good'
            elif ping_val < 300:
                return '🟠 Fair'
            else:
                return '🔴 Poor'
        except:
            return '⚪ Unknown'
    
    def _remove_duplicates(self, configs: List[Dict]) -> List[Dict]:
        seen = set()
        unique = []
        for cfg in configs:
            key = cfg['link'].split('?')[0]
            if key not in seen:
                seen.add(key)
                unique.append(cfg)
        return unique
