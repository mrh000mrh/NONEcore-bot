"""
دیتابیس SQLite کامل
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class Database:
    """دیتابیس ربات"""
    
    def __init__(self, db_path: str = "nonecore.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """ساخت جداول"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # جدول کانفیگ‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE,
                type TEXT,
                link TEXT,
                server TEXT,
                port INTEGER,
                location TEXT,
                ping TEXT,
                quality TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول تنظیمات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # جدول آمار روزانه
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                count INTEGER DEFAULT 0,
                locations TEXT
            )
        ''')
        
        # جدول کانال‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE,
                channel_name TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # تنظیمات پیش‌فرض
        defaults = [
            ('send_clients', 'true'),
            ('approval_mode', 'false'),
            ('batch_size', '10'),
            ('batch_interval', '120'),
            ('reminder_enabled', 'true'),
            ('total_configs', '0'),
            ('last_renewal', '')
        ]
        
        for key, value in defaults:
            cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))
        
        conn.commit()
        conn.close()
    
    def add_config(self, config_data: dict) -> bool:
        """اضافه کردن کانفیگ"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            uuid = self._extract_uuid(config_data['link'])
            
            cursor.execute('''
                INSERT OR IGNORE INTO configs 
                (uuid, type, link, server, port, location, ping, quality, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                uuid,
                config_data.get('type', ''),
                config_data['link'],
                config_data.get('server', ''),
                config_data.get('port', 0),
                config_data.get('location', ''),
                config_data.get('ping', ''),
                config_data.get('quality', ''),
                config_data.get('source', '')
            ))
            
            if cursor.rowcount > 0:
                self._increment_total(cursor)
                conn.commit()
                conn.close()
                return True
            
            conn.close()
            return False
            
        except Exception as e:
            print(f"Error adding config: {e}")
            return False
    
    def _extract_uuid(self, link: str) -> str:
        """استخراج UUID"""
        try:
            if '://' in link:
                parts = link.split('://')[1].split('@')
                if len(parts) > 0:
                    return parts[0][:50]
            return link[:50]
        except:
            return link[:50]
    
    def _increment_total(self, cursor):
        """افزایش آمار کل"""
        cursor.execute('UPDATE settings SET value = CAST(value AS INTEGER) + 1 WHERE key = ?', ('total_configs',))
    
    def is_duplicate(self, link: str) -> bool:
        """چک تکراری"""
        uuid = self._extract_uuid(link)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM configs WHERE uuid = ?', (uuid,))
        result = cursor.fetchone() is not None
        conn.close()
        return result
    
    def get_setting(self, key: str, default: str = '') -> str:
        """گرفتن تنظیم"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default
    
    def set_setting(self, key: str, value: str):
        """تنظیم مقدار"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        conn.commit()
        conn.close()
    
    def get_stats(self) -> dict:
        """آمار"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM settings WHERE key = ?', ('total_configs',))
        total = int(cursor.fetchone()[0]) if cursor.fetchone() else 0
        
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT count, locations FROM daily_stats WHERE date = ?', (today,))
        result = cursor.fetchone()
        
        today_count = result[0] if result else 0
        locations = json.loads(result[1]) if result and result[1] else {}
        
        conn.close()
        
        return {'total': total, 'today': today_count, 'locations': locations}
    
    def increment_daily(self, location: str):
        """افزایش آمار روزانه"""
        today = datetime.now().strftime('%Y-%m-%d')
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT count, locations FROM daily_stats WHERE date = ?', (today,))
        result = cursor.fetchone()
        
        if result:
            count, locs_json = result
            locations = json.loads(locs_json) if locs_json else {}
            locations[location] = locations.get(location, 0) + 1
            
            cursor.execute('UPDATE daily_stats SET count = ?, locations = ? WHERE date = ?',
                         (count + 1, json.dumps(locations), today))
        else:
            cursor.execute('INSERT INTO daily_stats (date, count, locations) VALUES (?, ?, ?)',
                         (today, 1, json.dumps({location: 1})))
        
        conn.commit()
        conn.close()
    
    def add_channel(self, channel_id: str, channel_name: str = '') -> bool:
        """اضافه کردن کانال"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO channels (channel_id, channel_name) VALUES (?, ?)',
                         (channel_id, channel_name))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def remove_channel(self, channel_id: str) -> bool:
        """حذف کانال"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM channels WHERE channel_id = ?', (channel_id,))
        conn.commit()
        conn.close()
        return True
    
    def get_channels(self) -> List[str]:
        """گرفتن لیست کانال‌ها"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT channel_id FROM channels')
        result = [row[0] for row in cursor.fetchall()]
        conn.close()
        return result if result else ['@nonecorebot']
    
    def toggle_setting(self, key: str) -> bool:
        """تغییر وضعیت true/false"""
        current = self.get_setting(key, 'false')
        new_value = 'true' if current == 'false' else 'false'
        self.set_setting(key, new_value)
        return new_value == 'true'
