import aiosqlite
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = 'nonecore.db'):
        self.db_path = db_path
    
    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
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
                    channel_id TEXT,
                    message_id INTEGER,
                    bad_reports INTEGER DEFAULT 0,
                    copy_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    count INTEGER DEFAULT 0,
                    locations TEXT,
                    new_members INTEGER DEFAULT 0,
                    copy_count INTEGER DEFAULT 0,
                    bad_reports INTEGER DEFAULT 0
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT UNIQUE,
                    channel_name TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_uuid TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.commit()
        
        await self._init_default_settings()
    
    async def _init_default_settings(self):
        defaults = {
            'send_clients': 'true',
            'batch_size': '5',
            'interval': '120',
            'delay': '0',
            'reminder_enabled': 'true',
            'daily_limit': '200',
            'stop_sending': 'false',
            'total_configs': '0',
            'last_renewal': ''
        }
        
        async with aiosqlite.connect(self.db_path) as db:
            for key, value in defaults.items():
                await db.execute('''
                    INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
                ''', (key, value))
            await db.commit()
    
    async def sync_channels_from_env(self, channels: List[str]):
        async with aiosqlite.connect(self.db_path) as db:
            for ch in channels:
                await db.execute('''
                    INSERT OR IGNORE INTO channels (channel_id, channel_name)
                    VALUES (?, ?)
                ''', (ch, ch))
            await db.commit()
    
    async def add_config(self, cfg: Dict[str, Any]) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO configs 
                (uuid, type, link, server, port, location, ping, quality, source,
                 channel_id, message_id, bad_reports, copy_count, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(uuid) DO UPDATE SET
                    type=excluded.type,
                    link=excluded.link,
                    server=excluded.server,
                    port=excluded.port,
                    location=excluded.location,
                    ping=excluded.ping,
                    quality=excluded.quality,
                    source=excluded.source,
                    channel_id=excluded.channel_id,
                    message_id=excluded.message_id,
                    sent_at=excluded.sent_at
            ''', (
                cfg.get('uuid'), cfg.get('type'), cfg.get('link'),
                cfg.get('server'), cfg.get('port'), cfg.get('location'),
                cfg.get('ping'), cfg.get('quality'), cfg.get('source'),
                cfg.get('channel_id'), cfg.get('message_id'),
                cfg.get('bad_reports', 0), cfg.get('copy_count', 0),
                cfg.get('sent_at')
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def get_config_by_uuid(self, uuid: str) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM configs WHERE uuid = ?', (uuid,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def delete_config(self, uuid: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM configs WHERE uuid = ?', (uuid,))
            await db.commit()
    
    async def get_channels(self) -> List[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT channel_id FROM channels') as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
    
    async def get_setting(self, key: str, default: str = '') -> str:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT value FROM settings WHERE key = ?', (key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else default
    
    async def set_setting(self, key: str, value: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
            await db.commit()
    
    async def increment_copy_count(self, uuid: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE configs SET copy_count = copy_count + 1 WHERE uuid = ?', (uuid,))
            await db.commit()
    
    async def increment_bad_report(self, uuid: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE configs SET bad_reports = bad_reports + 1 WHERE uuid = ?', (uuid,))
            await db.commit()
            
            async with db.execute('SELECT bad_reports FROM configs WHERE uuid = ?', (uuid,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    async def should_delete_config(self, uuid: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT bad_reports FROM configs WHERE uuid = ?', (uuid,)) as cursor:
                row = await cursor.fetchone()
                return row[0] >= 5 if row else False
    
    async def get_daily_stats(self, date: str = None) -> Dict:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM daily_stats WHERE date = ?', (date,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        'date': row['date'],
                        'count': row['count'],
                        'locations': json.loads(row['locations']) if row['locations'] else {},
                        'new_members': row['new_members'],
                        'copy_count': row['copy_count'],
                        'bad_reports': row['bad_reports']
                    }
                return {'date': date, 'count': 0, 'locations': {}, 'new_members': 0, 'copy_count': 0, 'bad_reports': 0}
    
    async def update_daily_stats(self, date: str, updates: Dict):
        async with aiosqlite.connect(self.db_path) as db:
            current = await self.get_daily_stats(date)
            current.update(updates)
            
            await db.execute('''
                INSERT OR REPLACE INTO daily_stats (date, count, locations, new_members, copy_count, bad_reports)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                date,
                current['count'],
                json.dumps(current['locations']),
                current['new_members'],
                current['copy_count'],
                current['bad_reports']
            ))
            await db.commit()
    
    async def increment_daily_count(self, location: str = None):
        date = datetime.now().strftime('%Y-%m-%d')
        stats = await self.get_daily_stats(date)
        stats['count'] += 1
        
        if location:
            loc_key = location.split()[-1] if ' ' in location else location
            stats['locations'][loc_key] = stats['locations'].get(loc_key, 0) + 1
        
        await self.update_daily_stats(date, stats)
    
    async def get_admin_stats(self) -> Dict:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            async with db.execute('SELECT COUNT(*) FROM configs') as cursor:
                total_configs = (await cursor.fetchone())[0]
            
            today = datetime.now().strftime('%Y-%m-%d')
            async with db.execute('SELECT COUNT(*) FROM configs WHERE date(created_at) = ?', (today,)) as cursor:
                today_configs = (await cursor.fetchone())[0]
            
            async with db.execute('SELECT SUM(copy_count), SUM(bad_reports) FROM configs') as cursor:
                row = await cursor.fetchone()
                total_copies = row[0] or 0
                total_reports = row[1] or 0
            
            async with db.execute('SELECT COUNT(*) FROM configs WHERE message_id IS NULL') as cursor:
                queue_count = (await cursor.fetchone())[0]
            
            daily = await self.get_daily_stats(today)
            
            return {
                'today_configs': today_configs,
                'total_configs': total_configs,
                'queue': queue_count,
                'today_copies': daily['copy_count'],
                'today_reports': daily['bad_reports'],
                'total_copies': total_copies,
                'total_reports': total_reports,
                'locations': daily['locations']
            }
    
    async def get_queue_count(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT COUNT(*) FROM configs WHERE message_id IS NULL') as cursor:
                return (await cursor.fetchone())[0]
    
    async def get_pending_configs(self, limit: int = None) -> List[Dict]:
        query = 'SELECT * FROM configs WHERE message_id IS NULL ORDER BY created_at'
        if limit:
            query += f' LIMIT {limit}'
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_daily_sent_count(self) -> int:
        today = datetime.now().strftime('%Y-%m-%d')
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT COUNT(*) FROM configs WHERE date(sent_at) = ?', (today,)) as cursor:
                return (await cursor.fetchone())[0]
    
    async def add_to_queue(self, configs: List[Dict]):
        async with aiosqlite.connect(self.db_path) as db:
            for cfg in configs:
                await db.execute('INSERT OR IGNORE INTO queue (config_uuid) VALUES (?)', (cfg.get('uuid'),))
            await db.commit()
